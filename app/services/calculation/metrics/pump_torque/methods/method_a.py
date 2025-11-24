"""
Method A: 功率-转速法

公式：T = 9549.3 × P / n

参数：
- P: 泵有功功率（kW）
- n: 泵转速（rpm）
- T: 泵扭矩（N·m）

物理原理：
扭矩等于功率除以角速度
T = P / ω
ω = 2π × n / 60
T = P / (2π × n / 60) = P × 60 / (2π × n) = 9549.3 × P / n
"""

from __future__ import annotations

from typing import Dict, Any
import pandas as pd


def calculate(data: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """
    功率-转速法计算泵扭矩

    Args:
        data: 包含 pump_active_power (kW), pump_speed (rpm) 的 DataFrame
        params: 参数字典（本方法不需要额外参数）

    Returns:
        包含 pump_torque (N·m) 的 DataFrame
    """
    result = data.copy()

    # T = 9549.3 × P / n
    # P: kW, n: rpm, T: N·m
    result['pump_torque'] = 9549.3 * result['pump_active_power'] / result['pump_speed']

    return result

