"""
静压法（备用方法）

公式:
P_in = P_atm + ρ × g × (pool_liquid_level - L_offset) / 1e6

依赖: pool_liquid_level
参数: P_atm, rho, g, L_offset

物理意义:
- pool_liquid_level: 水池液位相对于水池底部的高度 (m)
- L_offset: 泵入口距离水池底部的垂直高度 (m)，水池在泵上方时为正值
"""

from __future__ import annotations

from typing import Dict, Any
import pandas as pd


def calculate_static_pressure(data: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """
    静压法（备用方法）

    Args:
        data: 输入数据（已过滤 running=1）
        params: 参数配置

    Returns:
        计算结果（包含 pump_inlet_pressure 列）
    """
    # 获取参数（带默认值）
    P_atm = params.get('P_atm', 0.101325)  # 大气压 (MPa)
    rho = params.get('rho', 1000.0)  # 水密度 (kg/m³)
    g = params.get('g', 9.80665)  # 重力加速度 (m/s²)
    L_offset = params.get('L_offset')  # 水池底部到泵入口的垂直距离 (m)，水池在泵上方为正值

    # 验证必需参数
    if L_offset is None:
        raise ValueError("缺少必需参数: L_offset")

    results = []

    for idx, row in data.iterrows():
        pool_level = float(row['pool_liquid_level'])  # 水池液位 (m)

        # 计算入口压力（只考虑静压，不考虑流速损失）
        # 水池在泵上方，静压头 = 水池液位（相对于水池底部）- 泵入口高度（相对于水池底部）
        # P_in = P_atm + ρ × g × (pool_liquid_level - L_offset) / 1e6
        # 单位: MPa
        pressure = P_atm + rho * g * (pool_level - L_offset) / 1e6  # (MPa)

        results.append(pressure)

    # 创建结果 DataFrame
    df_result = data.copy()
    df_result['pump_inlet_pressure'] = results

    return df_result

