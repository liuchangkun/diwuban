# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict
import numpy as np

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

    # 物理常数和系数参数必须从数据库读取
    try:
        rho = float(params['rho'])
        g = float(params['g'])
        b0 = float(params['b0'])
        b1 = float(params['b1'])
        b2 = float(params['b2'])
        b3 = float(params['b3'])
        Pmin = float(params['P_in_min'])
        Pmax = float(params['P_in_max'])
    except KeyError as e:
        raise ValueError(f"PIN_COEF_V1 缺少必需的参数: {e}")

    def nz(x):
        return x if isinstance(x, np.ndarray) else np.full(n, np.nan)

    level = nz(level)
    Q_st = nz(Q_st)

    P_pa = b0 + b1 * (rho * g * level) - b2 * (Q_st ** 2) - b3 * Q_st
    P_mpa = P_pa / 1e6

    P_mpa = np.clip(P_mpa, Pmin, Pmax)
    return P_mpa

