"""
PIN_COEF_V1 - 等效系数法

计算公式：
P_in = b0 + b1×h + b2×h² + b3×h³

参数：
- b0, b1, b2, b3: 拟合系数，需要现场校准
- h: 水池液位（m），从pool_liquid_level获取
"""

from __future__ import annotations

from typing import Dict, Any
import pandas as pd
import logging


def calculate(data: pd.DataFrame, params: Dict[str, Any], trace_id: str = None) -> pd.DataFrame:
    """
    使用等效系数法计算总管进口压力
    
    Args:
        data: 输入数据（包含pool_liquid_level列）
        params: 参数字典
        trace_id: 追踪ID
    
    Returns:
        计算结果（添加main_pipeline_inlet_pressure列）
    """
    logger = logging.getLogger(__name__)
    
    # 获取参数
    b0 = params.get('b0', 0.101325)  # MPa
    b1 = params.get('b1', 0.00981)  # MPa/m
    b2 = params.get('b2', 0.0)  # MPa/m²
    b3 = params.get('b3', 0.0)  # MPa/m³
    
    logger.info(
        f"[PIN_COEF_V1] 开始计算: b0={b0}, b1={b1}, b2={b2}, b3={b3}",
        extra={'extra_data': {'trace_id': trace_id}}
    )
    
    # 计算
    result = data.copy()
    # 转换pool_liquid_level为float（避免Decimal类型问题）
    h = result['pool_liquid_level'].astype(float)
    result['main_pipeline_inlet_pressure'] = b0 + b1*h + b2*h**2 + b3*h**3
    result['method'] = 'PIN_COEF_V1'
    
    logger.info(
        f"[PIN_COEF_V1] 计算完成: 结果数量={len(result)}",
        extra={'extra_data': {'trace_id': trace_id}}
    )
    
    return result

