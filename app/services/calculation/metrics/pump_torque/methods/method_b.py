"""
Method B: 水力功率法

公式：T = ρ × g × Q × H / (2π × n / 60)

参数：
- ρ: 液体密度（kg/m³），默认1000（水）
- g: 重力加速度（m/s²），默认9.81
- Q: 泵流量（m³/h），需转换为m³/s
- H: 泵扬程（m）
- n: 泵转速（rpm），需转换为rad/s
- T: 泵扭矩（N·m）

物理原理：
扭矩等于水力功率除以角速度
P_h = ρ × g × Q × H
T = P_h / ω
ω = 2π × n / 60
T = ρ × g × Q × H / (2π × n / 60)
"""

from __future__ import annotations

from typing import Dict, Any
import pandas as pd
import math


def calculate(data: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """
    水力功率法计算泵扭矩

    Args:
        data: 包含 pump_flow_rate (m³/h), pump_head (m), pump_speed (rpm) 的 DataFrame
        params: 参数字典（rho, g）

    Returns:
        包含 pump_torque (N·m) 的 DataFrame
    """
    result = data.copy()

    # 获取参数
    rho = params.get('rho')
    g = params.get('g')

    # 验证必需参数
    if rho is None:
        raise ValueError(
            "缺少必需参数 'rho'. "
            "请在 calculation_parameters 表中添加该参数"
        )
    if g is None:
        raise ValueError(
            "缺少必需参数 'g'. "
            "请在 calculation_parameters 表中添加该参数"
        )

    # 单位转换
    Q_s = result['pump_flow_rate'] / 3600.0  # m³/h → m³/s
    n_rad_s = result['pump_speed'] * 2 * math.pi / 60  # rpm → rad/s

    # T = ρ × g × Q × H / ω
    result['pump_torque'] = rho * g * Q_s * result['pump_head'] / n_rad_s

    return result

