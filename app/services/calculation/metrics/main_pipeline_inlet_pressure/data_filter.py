"""
数据过滤器（DataFilter）

职责：
- 过滤运行状态（running=1）
- 过滤数据质量
- 返回过滤后的数据
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
    - 过滤运行状态（使用 mv_device_running_1s.running 字段）
    - 过滤数据质量（去除异常值）
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
                extra={'extra_data': {'追踪ID': self.trace_id}}
            )
            return data
        
        original_count = len(data)

        # 1. 过滤运行状态（running=1）
        # 注意：总管设备(device_id=7)没有running状态，NULL值应视为运行状态
        if 'running' in data.columns:
            # 保留 running=1 或 running=NULL 的数据
            data = data[(data['running'] == 1) | (data['running'].isna())].copy()
            running_filtered = original_count - len(data)

            self.logger.info(
                "[数据过滤] 运行状态过滤",
                extra={'extra_data': {
                    '追踪ID': self.trace_id,
                    '原始数量': original_count,
                    'filtered_count': running_filtered,
                    '剩余数量': len(data)
                }}
            )
        
        # 2. 过滤pool_liquid_level异常值
        if 'pool_liquid_level' in data.columns and len(data) > 0:
            # 获取阈值参数（不允许硬编码默认值）
            min_level = self.params.get('min_level')
            max_level = self.params.get('max_level')

            # 验证必需参数
            if min_level is None or max_level is None:
                missing_params = []
                if min_level is None:
                    missing_params.append('min_level')
                if max_level is None:
                    missing_params.append('max_level')

                self.logger.error(
                    "[数据过滤] main_pipeline_inlet_pressure data_filter缺少必需参数",
                    extra={'extra_data': {
                        '追踪ID': self.trace_id,
                        '缺失参数': missing_params,
                        '当前参数': self.params,
                        '错误': '必须在calculation_parameters表中配置这些参数'
                    }}
                )
                raise ValueError(
                    f"main_pipeline_inlet_pressure data_filter缺少必需参数: {', '.join(missing_params)}. "
                    f"必须在calculation_parameters表中配置: metric_key='main_pipeline_inlet_pressure', method_id='data_filter'"
                )
            
            # 过滤液位范围
            before_level_filter = len(data)
            data = data[
                (data['pool_liquid_level'] >= min_level) &
                (data['pool_liquid_level'] <= max_level)
            ].copy()
            level_filtered = before_level_filter - len(data)
            
            if level_filtered > 0:
                self.logger.info(
                    "[数据过滤] 液位范围过滤",
                    extra={'extra_data': {
                        '追踪ID': self.trace_id,
                        'min_level': min_level,
                        'max_level': max_level,
                        'filtered_count': level_filtered,
                        '剩余数量': len(data)
                    }}
                )
        
        # 3. 过滤NaN值
        if len(data) > 0:
            before_nan_filter = len(data)
            data = data.dropna(subset=['pool_liquid_level']).copy()
            nan_filtered = before_nan_filter - len(data)

            if nan_filtered > 0:
                self.logger.info(
                    "[数据过滤] NaN值过滤",
                    extra={'extra_data': {
                        '追踪ID': self.trace_id,
                        'filtered_count': nan_filtered,
                        '剩余数量': len(data)
                    }}
                )

        # 4. 过滤Inf值
        if len(data) > 0:
            before_inf_filter = len(data)
            data = data[~data['pool_liquid_level'].isin([np.inf, -np.inf])].copy()
            inf_filtered = before_inf_filter - len(data)

            if inf_filtered > 0:
                self.logger.info(
                    "[数据过滤] Inf值过滤",
                    extra={'extra_data': {
                        '追踪ID': self.trace_id,
                        'filtered_count': inf_filtered,
                        '剩余数量': len(data)
                    }}
                )

        # 最终统计
        final_count = len(data)
        total_filtered = original_count - final_count
        filter_ratio = (total_filtered / original_count * 100) if original_count > 0 else 0
        
        self.logger.info(
            "[数据过滤] 过滤完成",
            extra={'extra_data': {
                '追踪ID': self.trace_id,
                '原始数量': original_count,
                '最终数量': final_count,
                'total_filtered': total_filtered,
                '过滤比例': f"{filter_ratio:.1f}%"
            }}
        )
        
        return data

