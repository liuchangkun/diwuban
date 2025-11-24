"""
计算执行器（Calculator）

职责：
- 调用具体的计算方法
- 添加 method_id 列
"""

from __future__ import annotations

from typing import Dict, Any, Optional
import pandas as pd
import logging


class Calculator:
    """
    计算执行器
    
    职责：
    - 根据 method_id 调用对应的计算方法
    - 添加 method_id 列到结果中
    """
    
    def __init__(self, params: Dict[str, Any], trace_id: Optional[str] = None):
        """
        初始化计算执行器
        
        Args:
            params: 参数字典
            trace_id: 追踪ID（用于日志关联）
        """
        self.params = params
        self.trace_id = trace_id
        self.logger = logging.getLogger(__name__)
    
    def calculate(self, data: pd.DataFrame, method_id: str) -> pd.DataFrame:
        """
        执行计算
        
        Args:
            data: 过滤后的数据
            method_id: 方法ID
        
        Returns:
            计算结果（包含 pump_shaft_power 和 method_id 列）
        
        Raises:
            ValueError: 如果方法ID无效
        """
        self.logger.info(
            "[计算执行] 开始计算",
            extra={'extra_data': {
                '追踪ID': self.trace_id,
                '方法ID': method_id,
                'row_count': len(data)
            }}
        )
        
        # 调用对应的计算方法
        if method_id == 'method_a':
            from .methods import method_a
            result = method_a.calculate(data, self.params)
        else:
            raise ValueError(f"无效的方法ID: {method_id}")
        
        # 添加 method_id 列
        result['method_id'] = method_id
        
        # 统计信息
        if 'pump_shaft_power' in result.columns:
            stats = {
                'count': len(result),
                'mean': float(result['pump_shaft_power'].mean()),
                'min': float(result['pump_shaft_power'].min()),
                'max': float(result['pump_shaft_power'].max())
            }
        else:
            stats = {'count': len(result)}
        
        self.logger.info(
            "[计算执行] 计算完成",
            extra={'extra_data': {
                '追踪ID': self.trace_id,
                '方法ID': method_id,
                'stats': stats
            }}
        )
        
        return result

