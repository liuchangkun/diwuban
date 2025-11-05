# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict
import numpy as np

def calculate_head_coef_v1(data: Dict[str, np.ndarray], params: Dict[str, float]) -> np.ndarray:
    """
    HEAD_COEF_V1方法：基于压差和系数的扬程计算

    公式：H = a0 + a1 * head_out - a2 * level - a3 * Q_i² - a4 * Q_st² - a5 * Q_i
    其中：head_out = (P_out * 1e6) / (rho * g)

    Args:
        data: 输入数据字典
            - pump_outlet_pressure (必需): 泵出口压力 [MPa]
            - pool_liquid_level (可选): 水池液位 [m]，缺失时使用0
            - pump_flow_rate (可选): 泵流量 [m³/s]，缺失时忽略相关项
            - main_pipeline_flow_rate (可选): 总管流量 [m³/s]，缺失时忽略相关项
        params: 参数字典
            - rho: 水密度 [kg/m³]，默认1000.0
            - g: 重力加速度 [m/s²]，默认9.80665
            - a0-a5: 系数参数
            - H_min, H_max: 扬程边界

    Returns:
        扬程数组 [m]
    """
    P_out = data.get('pump_outlet_pressure')  # MPa
    level = data.get('pool_liquid_level')     # m
    Q_i = data.get('pump_flow_rate')          # m3/s
    Q_st = data.get('main_pipeline_flow_rate')  # m3/s

    # 确定数组长度
    n = 0
    for arr in (P_out, level, Q_i, Q_st):
        if isinstance(arr, np.ndarray):
            n = len(arr)
            break
    if n == 0:
        return np.array([])

    # 获取参数（物理常数和系数参数必须从数据库读取）
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

    # 辅助函数：将标量或None转换为数组，缺失值使用默认值而非NaN
    def nz(x, default=0.0):
        if isinstance(x, np.ndarray):
            return x
        else:
            return np.full(n, default, dtype=float)

    # 转换输入数据
    P_out = nz(P_out, np.nan)  # pump_outlet_pressure是必需的，缺失时为NaN
    level = nz(level, 0.0)     # pool_liquid_level缺失时使用0（假设水池液位为0）
    Q_i = nz(Q_i, 0.0)         # pump_flow_rate缺失时使用0（不影响计算）
    Q_st = nz(Q_st, 0.0)       # main_pipeline_flow_rate缺失时使用0（不影响计算）

    # 计算扬程
    head_out = (P_out * 1e6) / (rho * g)
    H = a0 + a1 * head_out - a2 * level - a3 * (Q_i ** 2) - a4 * (Q_st ** 2) - a5 * Q_i
    H = np.clip(H, H_min, H_max)
    return H

