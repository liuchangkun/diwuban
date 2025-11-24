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
        station_id: Optional[int] = None,
        trace_id: Optional[str] = None
    ):
        """
        初始化数据过滤器

        Args:
            max_flow: 流量上限（m³/h）- 必须从params传入，不使用默认值
            max_power: 功率上限（kW）- 必须从params传入，不使用默认值
            max_freq: 频率上限（Hz）- 必须从params传入，不使用默认值
            station_id: 泵站ID - 用于出水检测时查询 k 系数参数
            trace_id: 追踪ID（用于日志关联）
        """
        self.logger = logging.getLogger(__name__)
        self.trace_id = trace_id
        self.station_id = station_id

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
                '追踪ID': self.trace_id,
                '原始行数': original_count,
                '移除停机数量': stopped_count,
                '移除NaN数量': nan_count,
                '移除负值数量': negative_count,
                '移除异常值数量': outlier_count,
                '最终行数': final_count,
                '过滤比例': f"{(original_count - final_count) / original_count * 100:.2f}%" if original_count > 0 else "0%"
            }}
        )

        # 5. 出水状态检测（使用 k 系数判断泵是否出水）
        if self.station_id is not None and not data.empty:
            data = self._detect_water_output(data)

        return data

    def _detect_water_output(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        检测泵的出水状态

        使用 WaterOutputDetector 基于 k 系数和出口压力计算 f_min，
        判断每行数据中的泵是否在出水。

        Args:
            data: 过滤后的数据

        Returns:
            添加了 f_min 和 is_outputting 列的 DataFrame
        """
        from .pump_k_coefficient import WaterOutputDetector

        try:
            detector = WaterOutputDetector(
                station_id=self.station_id,
                trace_id=self.trace_id
            )

            # 检测当前设备的出水状态
            data = detector.detect(data)

            # 统计出水情况
            if 'is_outputting' in data.columns:
                outputting_count = data['is_outputting'].sum()
                total_count = len(data)
                self.logger.info(
                    "[数据过滤] 出水检测完成",
                    extra={'extra_data': {
                        '追踪ID': self.trace_id,
                        '总行数': total_count,
                        '出水行数': int(outputting_count),
                        '非出水行数': int(total_count - outputting_count),
                        '出水比例': f"{outputting_count / total_count * 100:.2f}%" if total_count > 0 else "0%"
                    }}
                )

        except Exception as e:
            self.logger.warning(
                "[数据过滤] 出水检测失败，跳过",
                extra={'extra_data': {
                    '追踪ID': self.trace_id,
                    '错误': str(e)
                }}
            )
            # 失败时不添加 is_outputting 列，后续逻辑会默认所有泵都出水

        return data

