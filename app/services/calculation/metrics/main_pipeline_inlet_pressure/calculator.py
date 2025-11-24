"""
计算执行器（Calculator）

职责：
- 根据选定的方法执行计算
- 调用具体的计算方法模块
- 返回计算结果
"""

from __future__ import annotations

from typing import Dict, Any
import pandas as pd
import logging


class Calculator:
    """
    计算执行器
    
    职责：
    - 根据method_id分发到具体的计算方法
    - 执行计算并返回结果
    """
    
    def __init__(self, params: Dict[str, Any] = None, trace_id: str = None):
        """
        初始化计算执行器
        
        Args:
            params: 参数字典（包含计算参数）
            trace_id: 追踪ID（用于日志关联）
        """
        self.logger = logging.getLogger(__name__)
        self.trace_id = trace_id
        self.params = params or {}
    
    def calculate(self, data: pd.DataFrame, method_id: str) -> pd.DataFrame:
        """
        执行计算
        
        Args:
            data: 输入数据
            method_id: 方法ID
        
        Returns:
            计算结果（添加main_pipeline_inlet_pressure列）
        """
        if data.empty:
            self.logger.warning(
                "[计算执行] 输入数据为空，跳过计算",
                extra={'extra_data': {'trace_id': self.trace_id}}
            )
            return data
        
        self.logger.info(
            f"[计算执行] 开始计算: method={method_id}, 数据量={len(data)}",
            extra={'extra_data': {'trace_id': self.trace_id}}
        )
        
        # 根据method_id分发到具体方法
        if method_id == 'method_b':
            from .methods.method_b import calculate
            result = calculate(data, self.params, self.trace_id)
        elif method_id == 'PIN_COEF_V1':
            from .methods.pin_coef_v1 import calculate
            result = calculate(data, self.params, self.trace_id)
        else:
            raise ValueError(f"未知方法: {method_id}")
        
        self.logger.info(
            f"[计算执行] 计算完成: 结果数量={len(result)}",
            extra={'extra_data': {'trace_id': self.trace_id}}
        )
        
        return result

