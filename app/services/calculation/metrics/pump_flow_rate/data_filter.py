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
    - 不使用硬编码阈值（f_thr, p_thr）
    """

    def __init__(
        self,
        max_flow: float,
        max_power: float,
        max_freq: float,
        trace_id: Optional[str] = None
    ):
        """
        初始化数据过滤器

        Args:
            max_flow: 流量上限（m³/h）- 必须从params传入，不使用默认值
            max_power: 功率上限（kW）- 必须从params传入，不使用默认值
            max_freq: 频率上限（Hz）- 必须从params传入，不使用默认值
            trace_id: 追踪ID（用于日志关联）
        """
        self.logger = logging.getLogger(__name__)
        self.trace_id = trace_id

        # 验证必需参数（禁止使用默认值）
        missing_params = []
        if max_flow is None:
            missing_params.append('max_flow')
        if max_power is None:
            missing_params.append('max_power')
        if max_freq is None:
            missing_params.append('max_freq')

        if missing_params:
            self.logger.error(
                f"[数据过滤] pump_flow_rate data_filter缺少必需参数",
                extra={'extra_data': {
                    '缺失参数': missing_params,
                    '错误': '必须在calculation_parameters表中配置这些参数'
                }}
            )
            raise ValueError(
                f"pump_flow_rate data_filter缺少必需参数: {', '.join(missing_params)}. "
                f"必须在calculation_parameters表中配置: metric_key='pump_flow_rate', method_id='data_filter'"
            )

        # 异常值阈值（从配置加载）
        self.max_flow = max_flow
        self.max_power = max_power
        self.max_freq = max_freq

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
                extra={'extra_data': {'trace_id': self.trace_id}}
            )
            return data

        original_count = len(data)

        self.logger.info(
            "[数据过滤] 开始过滤数据",
            extra={'extra_data': {
                'trace_id': self.trace_id,
                'original_rows': original_count
            }}
        )

        # 1. 停机状态过滤（使用 mv_device_running_1s.running 字段）
        # 注意：不使用硬编码阈值（f_thr, p_thr）
        before_stopped = len(data)
        data = data[data['running'] == 1]  # 只保留运行状态的数据
        stopped_count = before_stopped - len(data)

        # 2. NaN/Inf 过滤
        before_nan = len(data)
        data = data.dropna(subset=['main_pipeline_flow_rate', 'pump_active_power', 'pump_frequency'])
        data = data[~data['main_pipeline_flow_rate'].isin([np.inf, -np.inf])]
        data = data[~data['pump_active_power'].isin([np.inf, -np.inf])]
        data = data[~data['pump_frequency'].isin([np.inf, -np.inf])]
        nan_count = before_nan - len(data)

        # 3. 负值过滤
        before_negative = len(data)
        data = data[data['main_pipeline_flow_rate'] >= 0]
        data = data[data['pump_active_power'] >= 0]
        data = data[data['pump_frequency'] >= 0]
        negative_count = before_negative - len(data)

        # 4. 异常值过滤
        # 注意：main_pipeline_flow_rate 是主管道流量（所有泵的总流量），不应使用 max_flow 阈值
        # max_flow 是单个泵的流量上限，用于验证计算结果，而不是过滤输入数据
        before_outlier = len(data)
        # data = data[data['main_pipeline_flow_rate'] <= self.max_flow]  # 不过滤主管道流量
        data = data[data['pump_active_power'] <= self.max_power]
        data = data[data['pump_frequency'] <= self.max_freq]
        outlier_count = before_outlier - len(data)

        final_count = len(data)

        self.logger.info(
            "[数据过滤] 过滤完成",
            extra={'extra_data': {
                'trace_id': self.trace_id,
                'original_rows': original_count,
                'removed_stopped': stopped_count,
                'removed_nan': nan_count,
                'removed_negative': negative_count,
                'removed_outlier': outlier_count,
                'final_rows': final_count,
                'filter_ratio': f"{(original_count - final_count) / original_count * 100:.2f}%" if original_count > 0 else "0%"
            }}
        )

        return data

