# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict
import numpy as np

"""
HEAD_COEF_V1 - 泵扬程系数化方法（设备级）

公式（逐点）:
  H = a0 + a1*(P_out/(rho*g)) - a2*level_eff - a3*Q_i^2 - a4*Q_station^2 - a5*Q_i
  clip 到 [H_min, H_max]

依赖:
  - pump_outlet_pressure (MPa)
  - pool_liquid_level (m)
  - pump_flow_rate (m3/s)
  - main_pipeline_flow_rate (m3/s)
参数(示例初值):
  - a0..a5 (float)
  - rho (kg/m3) 缺省1000
  - g (m/s2) 缺省9.81
  - H_min/H_max (边界)
"""


def calculate_head_coef_v1(data: Dict[str, np.ndarray], params: Dict[str, float]) -> np.ndarray:
    P_out = data.get('pump_outlet_pressure')  # MPa
    level = data.get('pool_liquid_level')     # m
    Q_i = data.get('pump_flow_rate')          # m3/s
    Q_st = data.get('main_pipeline_flow_rate')  # m3/s

    n = 0
    for arr in (P_out, level, Q_i, Q_st):
        if isinstance(arr, np.ndarray):
            n = len(arr)
            break
    if n == 0:
        return np.array([])

    # 物理常数和系数参数必须从数据库读取
    try:
        rho = float(params['rho'])
        g = float(params['g'])
        a0 = float(params['a0'])
        a1 = float(params['a1'])
        a2 = float(params['a2'])
        a3 = float(params['a3'])
        a4 = float(params['a4'])
        a5 = float(params['a5'])
        H_min = float(params['H_min'])
        H_max = float(params['H_max'])
    except KeyError as e:
        raise ValueError(f"HEAD_COEF_V1 缺少必需的参数: {e}")

    # 安全取值
    def nz(x):
        return x if isinstance(x, np.ndarray) else np.full(n, np.nan)

    P_out = nz(P_out)
    level = nz(level)
    Q_i = nz(Q_i)
    Q_st = nz(Q_st)

    # MPa -> Pa for P_out/(rho*g): multiply 1e6 then divide by (rho*g)
    head_out = (P_out * 1e6) / (rho * g)

    H = a0 + a1 * head_out - a2 * level - a3 * (Q_i ** 2) - a4 * (Q_st ** 2) - a5 * Q_i

    # 裁剪到边界
    H = np.clip(H, H_min, H_max)
    return H

