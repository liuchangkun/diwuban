"""
数据过滤器（DataFilter）

职责：
- 过滤停机状态数据（使用 running 字段）
- 过滤无效数据（NaN, Inf, 负值, 异常值）
- 禁止硬编码阈值，所有阈值从params获取
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
    - 使用 running 字段过滤停机数据（running == 1）
    - 过滤 NaN/Inf 值
    - 过滤负值
    - 过滤异常值（基于参数阈值）
    - 禁止硬编码阈值
    """
    
    def __init__(self, max_power: float, trace_id: Optional[str] = None):
        """
        初始化数据过滤器
        
        Args:
            max_power: 功率上限（kW），用于过滤异常值
            trace_id: 追踪ID（用于日志关联）
        
        Raises:
            ValueError: 如果必需参数缺失
        """
        # 验证必需参数
        if max_power is None:
            raise ValueError(
                "缺少必需参数: max_power。"
                "必须在calculation_parameters表中配置该参数。"
            )
        
        self.max_power = max_power
        self.trace_id = trace_id
        self.logger = logging.getLogger(__name__)
    
    def filter_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        过滤数据
        
        Args:
            data: 原始数据
        
        Returns:
            过滤后的数据
        """
        if data.empty:
            return data
        
        original_count = len(data)
        
        self.logger.info(
            "[数据过滤] 开始过滤",
            extra={'extra_data': {
                'trace_id': self.trace_id,
                'original_count': original_count
            }}
        )
        
        # 1. 使用 running 字段过滤停机数据
        data = data[data['running'] == 1].copy()
        running_filtered_count = len(data)
        
        self.logger.info(
            "[数据过滤] running字段过滤完成",
            extra={'extra_data': {
                'trace_id': self.trace_id,
                'filtered_count': original_count - running_filtered_count,
                'remaining_count': running_filtered_count
            }}
        )
        
        if data.empty:
            return data
        
        # 2. 过滤 NaN/Inf 值
        data = data.dropna(subset=['pump_active_power'])
        data = data[~data['pump_active_power'].isin([np.inf, -np.inf])]
        
        # 3. 过滤负值
        data = data[data['pump_active_power'] >= 0]
        
        # 4. 过滤异常值（使用参数阈值）
        data = data[data['pump_active_power'] <= self.max_power]
        
        final_count = len(data)
        filtered_count = original_count - final_count
        filter_ratio = (filtered_count / original_count * 100) if original_count > 0 else 0
        
        self.logger.info(
            "[数据过滤] 过滤完成",
            extra={'extra_data': {
                'trace_id': self.trace_id,
                'original_count': original_count,
                'filtered_count': filtered_count,
                'final_count': final_count,
                'filter_ratio': f"{filter_ratio:.2f}%"
            }}
        )
        
        return data

