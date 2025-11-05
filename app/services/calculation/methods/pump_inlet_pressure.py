# -*- coding: utf-8 -*-
"""
pump_inlet_pressure 计算方法

提供两种计算泵进口压力的方法：
- method_a: 使用总管进口压力代替（并联系统假设）
- method_b: 从水池液位推算（基于静压原理）
"""
from typing import Dict
import numpy as np


def calculate_pump_inlet_pressure_method_a(
    data: Dict[str, np.ndarray],
    params: Dict[str, float]
) -> np.ndarray:
    """
    方法A：使用总管进口压力代替泵进口压力
    
    假设：并联系统中，泵进口与总管进口压力相近
    
    公式:
        P_pump_in = P_main_in
    
    Args:
        data: 包含 main_pipeline_inlet_pressure
        params: 空（不需要参数）
    
    Returns:
        计算得到的泵进口压力数组（MPa）
    """
    if 'main_pipeline_inlet_pressure' not in data:
        return np.array([], dtype=float)
    
    P_main_in = data['main_pipeline_inlet_pressure']
    if P_main_in is None or len(P_main_in) == 0:
        return np.array([], dtype=float)
    
    return P_main_in.copy()


def calculate_pump_inlet_pressure_method_b(
    data: Dict[str, np.ndarray],
    params: Dict[str, float]
) -> np.ndarray:
    """
    方法B：从水池液位推算泵进口压力
    
    公式:
        P_in = P_atm + ρ × g × L / 1e6
    
    其中:
        - P_in: 泵进口压力（MPa）
        - P_atm: 大气压（MPa，默认0.101325）
        - L: 水池液位（m）
        - ρ: 水密度（kg/m³，默认1000）
        - g: 重力加速度（m/s²，默认9.80665）
    
    Args:
        data: 包含 pool_liquid_level
        params: 包含 P_atm, rho, g（从数据库读取）
    
    Returns:
        计算得到的泵进口压力数组（MPa）
    """
    if 'pool_liquid_level' not in data:
        return np.array([], dtype=float)
    
    L = data['pool_liquid_level']  # m
    if L is None or len(L) == 0:
        return np.array([], dtype=float)

    # 物理常数必须从数据库读取
    try:
        P_atm = float(params['P_atm'])
        rho = float(params['rho'])
        g = float(params['g'])
    except KeyError as e:
        raise ValueError(f"pump_inlet_pressure_method_b 缺少必需的物理常数参数: {e}")

    result = np.full_like(L, np.nan, dtype=float)
    mask = ~np.isnan(L)
    result[mask] = P_atm + rho * g * L[mask] / 1e6
    
    return result

