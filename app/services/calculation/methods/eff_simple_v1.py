# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict
import numpy as np

def calculate_eff_simple_v1(data: Dict[str, np.ndarray], params: Dict[str, float]) -> np.ndarray:
    Q = data.get('pump_flow_rate')        # m3/s
    H = data.get('pump_head')             # m
    P_e = data.get('pump_active_power')   # kW

    n = 0
    for arr in (Q, H, P_e):
        if isinstance(arr, np.ndarray):
            n = len(arr)
            break
    if n == 0:
        return np.array([])

    # 物理常数必须从数据库读取
    try:
        rho = float(params['rho'])
        g = float(params['g'])
    except KeyError as e:
        raise ValueError(f"pump_efficiency_method_eff_simple_v1 缺少必需的物理常数参数: {e}")

    # 可优化参数允许默认值
    eta_motor = float(params.get('eta_motor', 0.92))
    eta_max = float(params.get('eta_max', 0.85))

    def nz(x):
        """对齐数组长度到 n，处理不同长度的输入数组"""
        if not isinstance(x, np.ndarray):
            return np.full(n, np.nan)
        if len(x) != n:
            # 数组长度不一致时，对齐到 n
            aligned = np.full(n, np.nan)
            copy_len = min(len(x), n)
            aligned[:copy_len] = x[:copy_len]
            return aligned
        return x

    Q = nz(Q)
    H = nz(H)
    P_e = nz(P_e)

    denom = P_e * eta_motor
    mask_valid = (~np.isnan(Q)) & (~np.isnan(H)) & (~np.isnan(P_e)) & (denom > 1e-6)
    eta = np.full(n, np.nan)
    eta[mask_valid] = (rho * g * Q[mask_valid] * H[mask_valid]) / (denom[mask_valid] * 1000.0)

    eta = np.clip(eta, 0.0, eta_max)
    return eta

