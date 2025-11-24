"""
数据过滤器（DataFilter）

职责：
- 过滤数据质量（NaN、Inf、异常值）
- 返回过滤后的数据
- 注意：不过滤运行状态，停机时转速为0仍可计算
"""

from __future__ import annotations

from typing import Dict, Any
import pandas as pd
import numpy as np
import logging


class DataFilter:
    """
    数据过滤器

    职责：
    - 过滤数据质量（去除 NaN、Inf、异常值）
    - 不过滤运行状态（停机时转速为0仍可计算）
    - 禁止硬编码阈值（所有阈值从参数传入）
    """

    def __init__(self, params: Dict[str, Any] = None, trace_id: str = None):
        """
        初始化数据过滤器

        Args:
            params: 过滤参数（包含阈值）
            trace_id: 追踪ID（用于日志关联）
        """
        self.logger = logging.getLogger(__name__)
        self.trace_id = trace_id
        self.params = params or {}

    def filter_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        过滤数据

        Args:
            data: 原始数据

        Returns:
            过滤后的数据
        """
        if data.empty:
            self.logger.info(
                "[数据过滤] 输入数据为空，跳过过滤",
                extra={'extra_data': {'trace_id': self.trace_id}}
            )
            return data

        original_count = len(data)

        # 1. 过滤NaN值
        if len(data) > 0:
            before_nan_filter = len(data)
            data = data.dropna(subset=['pump_frequency']).copy()
            nan_filtered = before_nan_filter - len(data)

            if nan_filtered > 0:
                self.logger.info(
                    "[数据过滤] NaN值过滤",
                    extra={'extra_data': {
                        'trace_id': self.trace_id,
                        'filtered_count': nan_filtered,
                        'remaining_count': len(data)
                    }}
                )

        # 2. 过滤Inf值
        if len(data) > 0:
            before_inf_filter = len(data)
            data = data[~data['pump_frequency'].isin([np.inf, -np.inf])].copy()
            inf_filtered = before_inf_filter - len(data)

            if inf_filtered > 0:
                self.logger.info(
                    "[数据过滤] Inf值过滤",
                    extra={'extra_data': {
                        'trace_id': self.trace_id,
                        'filtered_count': inf_filtered,
                        'remaining_count': len(data)
                    }}
                )

        # 3. 过滤pump_frequency异常值
        if 'pump_frequency' in data.columns and len(data) > 0:
            # 获取阈值参数
            min_freq = self.params.get('min_freq', 0.0)
            max_freq = self.params.get('max_freq', 60.0)

            # 过滤频率范围
            before_freq_filter = len(data)
            data = data[
                (data['pump_frequency'] >= min_freq) &
                (data['pump_frequency'] <= max_freq)
            ].copy()
            freq_filtered = before_freq_filter - len(data)

            if freq_filtered > 0:
                self.logger.info(
                    "[数据过滤] 频率范围过滤",
                    extra={'extra_data': {
                        'trace_id': self.trace_id,
                        'min_freq': min_freq,
                        'max_freq': max_freq,
                        'filtered_count': freq_filtered,
                        'remaining_count': len(data)
                    }}
                )

        # 最终统计
        final_count = len(data)
        total_filtered = original_count - final_count
        filter_ratio = (total_filtered / original_count * 100) if original_count > 0 else 0

        self.logger.info(
            "[数据过滤] 过滤完成",
            extra={'extra_data': {
                'trace_id': self.trace_id,
                'original_count': original_count,
                'final_count': final_count,
                'total_filtered': total_filtered,
                'filter_ratio': f"{filter_ratio:.1f}%"
            }}
        )

        return data

