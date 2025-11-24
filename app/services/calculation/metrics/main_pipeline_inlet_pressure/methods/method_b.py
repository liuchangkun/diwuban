"""
method_b - 静压法

计算公式：
P_in = P_atm + ρ × g × h / 1e6

参数：
- P_atm: 大气压力（MPa），默认0.101325
- rho: 水的密度（kg/m³），默认1000.0
- g: 重力加速度（m/s²），默认9.81
- h: 水池液位（m），从pool_liquid_level获取
"""

from __future__ import annotations

from typing import Dict, Any
import pandas as pd
import logging


def calculate(data: pd.DataFrame, params: Dict[str, Any], trace_id: str = None) -> pd.DataFrame:
    """
    使用静压法计算总管进口压力
    
    Args:
        data: 输入数据（包含pool_liquid_level列）
        params: 参数字典
        trace_id: 追踪ID
    
    Returns:
        计算结果（添加main_pipeline_inlet_pressure列）
    """
    logger = logging.getLogger(__name__)
    
    # 获取参数
    P_atm = params.get('P_atm')
    rho = params.get('rho')
    g = params.get('g')

    # 验证必需参数
    if P_atm is None:
        logger.error(
            "[参数错误] 缺少必需参数 'P_atm'",
            extra={'extra_data': {
                '追踪ID': trace_id,
                'missing_param': 'P_atm',
                'fix': '请在 calculation_parameters 表中添加该参数'
            }}
        )
        raise ValueError("缺少必需参数 'P_atm'")
    if rho is None:
        logger.error(
            "[参数错误] 缺少必需参数 'rho'",
            extra={'extra_data': {
                '追踪ID': trace_id,
                'missing_param': 'rho',
                'fix': '请在 calculation_parameters 表中添加该参数'
            }}
        )
        raise ValueError("缺少必需参数 'rho'")
    if g is None:
        logger.error(
            "[参数错误] 缺少必需参数 'g'",
            extra={'extra_data': {
                '追踪ID': trace_id,
                'missing_param': 'g',
                'fix': '请在 calculation_parameters 表中添加该参数'
            }}
        )
        raise ValueError("缺少必需参数 'g'")

    logger.info(
        f"[method_b] 开始计算: P_atm={P_atm}, rho={rho}, g={g}",
        extra={'extra_data': {'追踪ID': trace_id}}
    )
    
    # 计算
    result = data.copy()
    # 转换pool_liquid_level为float（避免Decimal类型问题）
    h = result['pool_liquid_level'].astype(float)
    result['main_pipeline_inlet_pressure'] = P_atm + rho * g * h / 1e6
    result['method'] = 'method_b'
    
    logger.info(
        f"[method_b] 计算完成: 结果数量={len(result)}",
        extra={'extra_data': {'追踪ID': trace_id}}
    )
    
    return result

