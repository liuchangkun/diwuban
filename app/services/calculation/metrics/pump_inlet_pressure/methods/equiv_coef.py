"""
等效损失系数法

公式:
P_in = P_atm + ρ × g × (h_static - h_loss) / 1e6

其中:
h_static = pool_liquid_level - L_offset
h_loss = K_eq × v² / (2g)
v = Q / (3600 × π × D² / 4)

依赖: pool_liquid_level, pump_flow_rate
参数: P_atm, rho, g, K_eq, L_offset, pipe_diameter

物理意义:
- pool_liquid_level: 水池液位相对于水池底部的高度 (m)
- L_offset: 泵入口距离水池底部的垂直高度 (m)，水池在泵上方时为正值
- h_static: 泵入口的静压头 = pool_liquid_level - L_offset (m)
"""

from __future__ import annotations

from typing import Dict, Any
import pandas as pd
import numpy as np


def calculate_equiv_coef(data: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """
    等效损失系数法

    Args:
        data: 输入数据（已过滤 running=1）
        params: 参数配置

    Returns:
        计算结果（包含 pump_inlet_pressure 列）
    """
    # 获取参数
    P_atm = params.get('P_atm', 0.101325)  # 大气压 (MPa) - 物理常数，可保留默认值
    rho = params.get('rho', 1000.0)  # 水密度 (kg/m³) - 物理常数，可保留默认值
    g = params.get('g', 9.80665)  # 重力加速度 (m/s²) - 物理常数，可保留默认值
    K_eq = params.get('K_eq')  # 等效损失系数 - 必需参数，不允许默认值
    L_offset = params.get('L_offset')  # 水池底部到泵入口的垂直距离 (m)，水池在泵上方为正值
    pipe_diameter = params.get('pipe_diameter')  # 进水管道直径 (m)

    # 验证必需参数
    if K_eq is None:
        raise ValueError(
            "缺少必需参数 'K_eq' (等效损失系数). "
            "请在 calculation_parameters 表中添加该参数: "
            "metric_key='pump_inlet_pressure', method_id='equiv_coef'"
        )

    # 验证必需参数
    if L_offset is None:
        raise ValueError("缺少必需参数: L_offset")
    if pipe_diameter is None:
        raise ValueError("缺少必需参数: pipe_diameter")

    results = []

    for idx, row in data.iterrows():
        pool_level = float(row['pool_liquid_level'])  # 水池液位 (m)
        flow_rate = float(row['pump_flow_rate'])  # 水泵流量 (m³/h)

        # 计算静态水头
        # 水池在泵上方，静压头 = 水池液位（相对于水池底部）- 泵入口高度（相对于水池底部）
        h_static = pool_level - L_offset  # (m)

        # 计算流速
        # v = Q / (3600 × π × D² / 4)
        # Q: m³/h, D: m, v: m/s
        pipe_area = np.pi * (pipe_diameter ** 2) / 4  # (m²)
        velocity = flow_rate / (3600 * pipe_area)  # (m/s)

        # 计算水头损失
        # h_loss = K_eq × v² / (2g)
        h_loss = K_eq * (velocity ** 2) / (2 * g)  # (m)

        # 计算入口压力
        # P_in = P_atm + ρ × g × (h_static - h_loss) / 1e6
        # 单位: MPa
        pressure = P_atm + rho * g * (h_static - h_loss) / 1e6  # (MPa)

        results.append(pressure)

    # 创建结果 DataFrame
    df_result = data.copy()
    df_result['pump_inlet_pressure'] = results

    return df_result

