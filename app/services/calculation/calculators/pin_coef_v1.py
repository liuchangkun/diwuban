# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict
import numpy as np

"""
PIN_COEF_V1 - 总管进口压力系数化方法（站级）

公式（逐点）:
  P_in(Pa) = b0 + b1*(rho*g*level_eff) - b2*Q_station^2 - b3*Q_station
  输出单位：MPa（统一与其他压力口径）
  clip 到 [P_in_min, P_in_max]（单位MPa）

依赖:
  - pool_liquid_level (m)
  - main_pipeline_flow_rate (m3/s)
参数(示例初值):
  - b0..b3 (float)
  - rho (kg/m3) 缺省1000
  - g (m/s2) 缺省9.81
  - P_in_min/P_in_max (MPa)
"""


def calculate_pin_coef_v1(data: Dict[str, np.ndarray], params: Dict[str, float]) -> np.ndarray:
    level = data.get('pool_liquid_level')           # m
    Q_st = data.get('main_pipeline_flow_rate')      # m3/s

    n = 0
    for arr in (level, Q_st):
        if isinstance(arr, np.ndarray):
            n = len(arr)
            break
    if n == 0:
        return np.array([])

    b0 = float(params.get('b0', 0.0))
    b1 = float(params.get('b1', 1.0))
    b2 = float(params.get('b2', 0.0))
    b3 = float(params.get('b3', 0.0))
    rho = float(params.get('rho', 1000.0))
    g = float(params.get('g', 9.81))
    Pmin = float(params.get('P_in_min', 0.0))       # MPa
    Pmax = float(params.get('P_in_max', 1.5))       # MPa

    def nz(x):
        return x if isinstance(x, np.ndarray) else np.full(n, np.nan)

    level = nz(level)
    Q_st = nz(Q_st)

    P_pa = b0 + b1 * (rho * g * level) - b2 * (Q_st ** 2) - b3 * Q_st
    P_mpa = P_pa / 1e6

    P_mpa = np.clip(P_mpa, Pmin, Pmax)
    return P_mpa

