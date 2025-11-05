# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict
import numpy as np

"""
EFF_SIMPLE_V1 - 泵效率简化方法（设备级）

公式（逐点）:
  eta = (rho * g * Q * H) / (P_electric * eta_motor_assumed)
  eta ∈ [0, eta_max]
  可选平滑：由 orchestrator/validator 外层控制（本实现不引入状态）

依赖:
  - pump_flow_rate (m3/s)
  - pump_head (m)
  - pump_active_power (kW)
参数(示例初值):
  - eta_motor_assumed (默认0.92)
  - eta_max (默认0.85)
  - rho (1000), g (9.81)
"""


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
        return x if isinstance(x, np.ndarray) else np.full(n, np.nan)

    Q = nz(Q)
    H = nz(H)
    P_e = nz(P_e)

    denom = P_e * eta_motor
    # 避免除零
    mask_valid = (~np.isnan(Q)) & (~np.isnan(H)) & (~np.isnan(P_e)) & (denom > 1e-6)
    eta = np.full(n, np.nan)
    eta[mask_valid] = (rho * g * Q[mask_valid] * H[mask_valid]) / (denom[mask_valid] * 1000.0)

    eta = np.clip(eta, 0.0, eta_max)
    return eta

