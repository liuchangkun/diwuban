"""
数据过滤器（DataFilter）

职责：
- 过滤无效数据，确保计算输入的质量
- 使用 mv_device_running_1s.running 字段过滤停机数据（不使用硬编码阈值）
- 过滤 NaN、Inf、负值、异常值
"""

from __future__ import annotations

from typing import Optional
import pandas as pd
import numpy as np
import logging


class DataFilter:
    """
    数据过滤器

    职责：
    - 过滤无效数据，确保计算输入的质量
    - 使用 mv_device_running_1s.running 字段过滤停机数据
    - 不使用硬编码阈值
    """

    def __init__(
        self,
        max_power: float,
        max_speed: float,
        max_flow: Optional[float] = None,
        max_head: Optional[float] = None,
        trace_id: Optional[str] = None
    ):
        """
        初始化数据过滤器

        Args:
            max_power: 功率上限（kW）- 必须从params传入
            max_speed: 转速上限（rpm）- 必须从params传入
            max_flow: 流量上限（m³/h）- 可选，用于method_b
            max_head: 扬程上限（m）- 可选，用于method_b
            trace_id: 追踪ID（用于日志关联）
        """
        self.logger = logging.getLogger(__name__)
        self.trace_id = trace_id

        # 验证必需参数（禁止使用默认值）
        missing_params = []
        if max_power is None:
            missing_params.append('max_power')
        if max_speed is None:
            missing_params.append('max_speed')

        if missing_params:
            self.logger.error(
                f"[数据过滤] pump_torque data_filter缺少必需参数",
                extra={'extra_data': {
                    '缺失参数': missing_params,
                    '错误': '必须在calculation_parameters表中配置这些参数'
                }}
            )
            raise ValueError(
                f"pump_torque data_filter缺少必需参数: {', '.join(missing_params)}. "
                f"必须在calculation_parameters表中配置: metric_key='pump_torque', method_id='data_filter'"
            )

        # 异常值阈值（从配置加载）
        self.max_power = max_power
        self.max_speed = max_speed
        self.max_flow = max_flow
        self.max_head = max_head

    def filter_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        过滤无效数据

        Args:
            data: 原始数据（包含 running 字段）

        Returns:
            过滤后的数据
        """
        if data.empty:
            self.logger.warning(
                "[数据过滤] 输入数据为空",
                extra={'extra_data': {'追踪ID': self.trace_id}}
            )
            return data

        original_count = len(data)

        self.logger.info(
            "[数据过滤] 开始过滤数据",
            extra={'extra_data': {
                '追踪ID': self.trace_id,
                '原始行数': original_count
            }}
        )

        # 1. 停机状态过滤（使用 mv_device_running_1s.running 字段）
        before_stopped = len(data)
        data = data[data['running'] == 1]  # 只保留运行状态的数据
        stopped_count = before_stopped - len(data)

        # 2. NaN/Inf 过滤（必需字段）
        before_nan = len(data)
        data = data.dropna(subset=['pump_active_power', 'pump_speed'])
        data = data[~data['pump_active_power'].isin([np.inf, -np.inf])]
        data = data[~data['pump_speed'].isin([np.inf, -np.inf])]
        nan_count = before_nan - len(data)

        # 3. 可选字段的 NaN/Inf 过滤
        if 'pump_flow_rate' in data.columns:
            before_flow_nan = len(data)
            data = data.dropna(subset=['pump_flow_rate'])
            data = data[~data['pump_flow_rate'].isin([np.inf, -np.inf])]
            flow_nan_count = before_flow_nan - len(data)
        else:
            flow_nan_count = 0

        if 'pump_head' in data.columns:
            before_head_nan = len(data)
            data = data.dropna(subset=['pump_head'])
            data = data[~data['pump_head'].isin([np.inf, -np.inf])]
            head_nan_count = before_head_nan - len(data)
        else:
            head_nan_count = 0

        # 4. 负值和零值过滤
        before_negative = len(data)
        data = data[data['pump_active_power'] >= 0]
        data = data[data['pump_speed'] > 0]  # 转速必须 > 0，避免除零错误
        if 'pump_flow_rate' in data.columns:
            data = data[data['pump_flow_rate'] >= 0]
        if 'pump_head' in data.columns:
            data = data[data['pump_head'] >= 0]
        negative_count = before_negative - len(data)

        # 5. 异常值过滤
        before_outlier = len(data)
        data = data[data['pump_active_power'] <= self.max_power]
        data = data[data['pump_speed'] <= self.max_speed]
        if 'pump_flow_rate' in data.columns and self.max_flow is not None:
            data = data[data['pump_flow_rate'] <= self.max_flow]
        if 'pump_head' in data.columns and self.max_head is not None:
            data = data[data['pump_head'] <= self.max_head]
        outlier_count = before_outlier - len(data)

        final_count = len(data)

        self.logger.info(
            "[数据过滤] 过滤完成",
            extra={'extra_data': {
                '追踪ID': self.trace_id,
                '原始行数': original_count,
                '移除停机数量': stopped_count,
                '移除NaN数量': nan_count,
                'removed_flow_nan': flow_nan_count,
                'removed_head_nan': head_nan_count,
                '移除负值数量': negative_count,
                '移除异常值数量': outlier_count,
                '最终行数': final_count,
                '过滤比例': f"{(original_count - final_count) / original_count * 100:.2f}%" if original_count > 0 else "0%"
            }}
        )

        return data

