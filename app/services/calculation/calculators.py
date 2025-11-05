"""
Calculators - 计算函数模块

实现所有指标的计算函数。

支持的指标:
- pump_flow_rate: 泵流量（6种方法）
- pump_head: 泵扬程（1种方法）
- pump_outlet_pressure: 泵出口压力（4种方法）
- pump_efficiency: 泵效率（1种方法）

所有计算函数的签名:
    def calculate_xxx(data: Dict[str, np.ndarray], params: Dict[str, float]) -> np.ndarray

参数:
    data: 输入数据字典，键为metric_key，值为numpy数组
    params: 参数字典，键为参数名，值为参数值

返回:
    计算结果的numpy数组
"""

from __future__ import annotations

import logging
from typing import Dict, Tuple, Optional, Any

import numpy as np

logger = logging.getLogger(__name__)
from app.services.calculation.domain import CalculationContext, MethodDescriptor

from app.services.calculation.methods.head_coef_v1 import calculate_head_coef_v1
from app.services.calculation.methods.pin_coef_v1 import calculate_pin_coef_v1
from app.services.calculation.methods.eff_simple_v1 import calculate_eff_simple_v1
from app.services.calculation.methods.eff_curve_v1 import calculate_pump_efficiency_eff_curve_v1
from app.services.calculation.methods.pump_inlet_pressure import (
    calculate_pump_inlet_pressure_method_a,
    calculate_pump_inlet_pressure_method_b
)



# =====================================================
# pump_flow_rate - 泵流量计算函数
# =====================================================

def calculate_pump_flow_rate_method_a(
    data: Dict[str, np.ndarray],
    params: Dict[str, float]
) -> np.ndarray:
    """
    Method A: distribute the station flow to each pump according to the power-frequency weight.

    Formula:
        Q_i = Q_total * (P_i**alpha * f_i**beta) / Σ(P_j**alpha * f_j**beta)

    Args:
        data: expects main_pipeline_flow_rate, pump_active_power, pump_frequency
        params: optional tuning parameters alpha, beta, f_thr, p_thr

    Returns:
        Numpy array with the estimated flow for the current pump.
    """
    logger.info(
        "[计算-开始] [泵流量计算-方法A]",
        extra={
            "extra_data": {
                "method": "power_frequency_weight",
                "has_share": '__pump_flow_rate_share' in data,
            }
        }
    )

    Q_total = np.asarray(data['main_pipeline_flow_rate'], dtype=float)
    share = data.get('__pump_flow_rate_share')

    result = np.full_like(Q_total, np.nan, dtype=float)

    if share is not None:
        share_arr = np.asarray(share, dtype=float)
        mask = (~np.isnan(Q_total)) & (~np.isnan(share_arr))
        result[mask] = Q_total[mask] * share_arr[mask]

        logger.info(
            "[计算-完成] [泵流量计算完成]",
            extra={
                "extra_data": {
                    "method": "A",
                    "total_points": len(result),
                    "valid_points": int(np.sum(mask)),
                }
            }
        )
        return result

    logger.warning(
        "[计算-警告] [缺少分摊系数]",
        extra={"extra_data": {"missing_key": "__pump_flow_rate_share"}}
    )
    return result


def calculate_pump_head_method_main(
    data: Dict[str, np.ndarray],
    params: Dict[str, float]
) -> np.ndarray:
    """
    Method MAIN: estimate pump head from outlet/inlet pressures.

    H = (P_out - P_in) * 1e6 / (rho * g)
    """
    out_arr = np.asarray(data.get('pump_outlet_pressure'), dtype=float)
    if out_arr.size == 0:
        return np.array([], dtype=float)

    inlet = data.get('pump_inlet_pressure')
    inlet_arr = np.asarray(inlet, dtype=float) if inlet is not None else np.full_like(out_arr, np.nan)

    if np.all(np.isnan(inlet_arr)):
        alt = data.get('main_pipeline_inlet_pressure')
        if alt is not None:
            inlet_arr = np.asarray(alt, dtype=float)
    if np.all(np.isnan(inlet_arr)):
        level = data.get('pool_liquid_level')
        if level is not None:
            level_arr = np.asarray(level, dtype=float)
            mask = ~np.isnan(level_arr)
            if np.any(mask):
                # 物理常数必须从数据库读取
                try:
                    P_atm = float(params['P_atm'])
                    rho = float(params['rho'])
                    g = float(params['g'])
                except KeyError as e:
                    raise ValueError(f"pump_head_method_main 缺少必需的物理常数参数: {e}")
                inlet_arr = np.full_like(level_arr, np.nan, dtype=float)
                inlet_arr[mask] = P_atm + rho * g * level_arr[mask] / 1_000_000.0
        if inlet_arr.size == 0:
            inlet_arr = np.full_like(out_arr, np.nan, dtype=float)

    # 物理常数必须从数据库读取
    try:
        rho = float(params['rho'])
        g = float(params['g'])
    except KeyError as e:
        raise ValueError(f"pump_head_method_main 缺少必需的物理常数参数: {e}")
    result = np.full_like(out_arr, np.nan, dtype=float)
    mask = (~np.isnan(out_arr)) & (~np.isnan(inlet_arr))
    if np.any(mask):
        result[mask] = (out_arr[mask] - inlet_arr[mask]) * 1_000_000.0 / (rho * g)
    return result


# calculate_main_pipeline_inlet_pressure_method_b 已移至第866行（完整版本）
# 此处删除重复定义（manual_fix_2.4）

def calculate_pump_flow_rate_method_b(
    data: Dict[str, np.ndarray],
    params: Dict[str, float]
) -> np.ndarray:
    """
    方案B：累计量求导

    公式:
        Q(t) = dV/dt = (V(t) - V(t-1)) / Δt

    其中:
        - V(t): t时刻的累计流量
        - Δt: 时间间隔（默认1秒）

    Args:
        data: 包含 pump_cumulative_flow
        params: 空（此方法不需要参数）

    Returns:
        计算得到的泵流量数组
    """
    V = data['pump_cumulative_flow']

    # 计算差分（求导）
    Q = np.diff(V, prepend=V[0])

    # 处理负值（累计流量不应该减少）
    Q[Q < 0] = 0

    return Q


def calculate_pump_flow_rate_method_c(
    data: Dict[str, np.ndarray],
    params: Dict[str, float]
) -> np.ndarray:
    """
    方案C：单泵运行直接取总管流量

    公式:
        Q_pump = Q_total

    条件:
        - 只有该泵运行（running_count = 1）

    Args:
        data: 包含 main_pipeline_flow_rate
        params: 空（此方法不需要参数）

    Returns:
        计算得到的泵流量数组
    """
    Q_total = data['main_pipeline_flow_rate']
    return Q_total.copy()


def calculate_pump_flow_rate_method_d(
    data: Dict[str, np.ndarray],
    params: Dict[str, float]
) -> np.ndarray:
    """
    方案D：仅功率分摊

    公式:
        Q_i = Q_total × P_i / Σ(P_j)

    Args:
        data: 包含 main_pipeline_flow_rate, pump_active_power
        params: 包含 p_thr

    Returns:
        计算得到的泵流量数组
    """
    Q_total = data['main_pipeline_flow_rate']
    P_i = data['pump_active_power']

    p_thr = params.get('p_thr', 0.5)

    # 过滤掉功率过低的数据点
    mask = P_i >= p_thr

    Q_i = np.zeros_like(Q_total)
    Q_i[mask] = Q_total[mask] * P_i[mask]

    return Q_i


def calculate_pump_flow_rate_method_e(
    data: Dict[str, np.ndarray],
    params: Dict[str, float]
) -> np.ndarray:
    """
    方案E：仅频率分摊

    公式:
        Q_i = Q_total × f_i / Σ(f_j)

    Args:
        data: 包含 main_pipeline_flow_rate, pump_frequency
        params: 包含 f_thr

    Returns:
        计算得到的泵流量数组
    """
    Q_total = data['main_pipeline_flow_rate']
    f_i = data['pump_frequency']

    f_thr = params.get('f_thr', 3.0)

    # 过滤掉频率过低的数据点
    mask = f_i >= f_thr

    Q_i = np.zeros_like(Q_total)
    Q_i[mask] = Q_total[mask] * f_i[mask]

    return Q_i


def calculate_pump_flow_rate_method_f(
    data: Dict[str, np.ndarray],
    params: Dict[str, float]
) -> np.ndarray:
    """
    方案F：数据驱动回归融合

    公式:
        Q = a0 + a1×P + a2×f + a3×P_in + a4×P² + a5×f² + ...

    注意：此方法需要预先训练，获取回归系数

    Args:
        data: 包含 pump_active_power, pump_frequency, pump_inlet_pressure
        params: 包含回归系数 a0, a1, a2, ...

    Returns:
        计算得到的泵流量数组
    """
    P = data['pump_active_power']
    f = data['pump_frequency']
    P_in = data['pump_inlet_pressure']

    # 简单的线性回归模型（实际应该使用训练好的模型）
    a0 = params.get('a0', 0.0)
    a1 = params.get('a1', 1.0)
    a2 = params.get('a2', 1.0)
    a3 = params.get('a3', 0.0)

    Q = a0 + a1 * P + a2 * f + a3 * P_in

    # 确保流量非负
    Q[Q < 0] = 0

    return Q


# =====================================================
# pump_head - 泵扬程计算函数
# =====================================================

# =====================================================
# pump_outlet_pressure - 泵出口压力计算函数
# =====================================================

def calculate_pump_outlet_pressure_method_a(
    data: Dict[str, np.ndarray],
    params: Dict[str, float]
) -> np.ndarray:
    """
    方案A：直接读取

    如果data字典中已有pump_outlet_pressure数据，直接返回；
    否则返回空数组（表示需要从数据库读取）

    Args:
        data: 可能包含pump_outlet_pressure的数据字典
        params: 空（不需要参数）

    Returns:
        pump_outlet_pressure数组，如果data中没有则返回空数组
    """
    if 'pump_outlet_pressure' in data:
        P_out = data['pump_outlet_pressure']
        if P_out is not None and len(P_out) > 0:
            return P_out.copy()
    return np.array([], dtype=float)


def calculate_pump_outlet_pressure_method_b(
    data: Dict[str, np.ndarray],
    params: Dict[str, float]
) -> np.ndarray:
    """
    方案B：以总管出口压力代替

    公式:
        P_pump_out = P_main_out

    Args:
        data: 包含 main_pipeline_outlet_pressure
        params: 空（不需要参数）

    Returns:
        计算得到的泵出口压力数组
    """
    P_main_out = data['main_pipeline_outlet_pressure']
    return P_main_out.copy()


def calculate_pump_outlet_pressure_method_c(
    data: Dict[str, np.ndarray],
    params: Dict[str, float]
) -> np.ndarray:
    """
    方案C：由进口压力与扬程回推

    公式:
        P_out = P_in + ρ × g × H / 10^6

    其中:
        - P_out: 出口压力（MPa）
        - P_in: 进口压力（MPa）
        - H: 扬程（m）
        - ρ: 水密度（kg/m³，默认1000）
        - g: 重力加速度（m/s²，默认9.80665）

    Args:
        data: 包含 pump_head, pump_inlet_pressure
        params: 包含 rho, g

    Returns:
        计算得到的泵出口压力数组
    """
    H = data['pump_head']                 # m
    P_in = data['pump_inlet_pressure']    # MPa

    # 物理常数必须从数据库读取
    try:
        rho = float(params['rho'])
        g = float(params['g'])
    except KeyError as e:
        raise ValueError(f"pump_outlet_pressure_method_a 缺少必需的物理常数参数: {e}")

    # 创建有效数据掩码
    valid_mask = ~np.isnan(H) & ~np.isnan(P_in)

    # 计算出口压力（初始化为NaN）
    # 注意：结果单位是MPa
    P_out = np.full_like(H, np.nan)
    P_out[valid_mask] = P_in[valid_mask] + rho * g * H[valid_mask] / 1e6

    return P_out


def calculate_pump_outlet_pressure_method_d(
    data: Dict[str, np.ndarray],
    params: Dict[str, float]
) -> np.ndarray:
    """
    方案D：泵组层面近似

    公式:
        P_pump_out = P_group_out

    Args:
        data: 包含 pump_group_outlet_pressure
        params: 空（不需要参数）

    Returns:
        计算得到的泵出口压力数组
    """
    P_group_out = data['pump_group_outlet_pressure']
    return P_group_out.copy()


# =====================================================
# pump_efficiency - 泵效率计算函数
# =====================================================

def calculate_pump_efficiency_method_main(
    data: Dict[str, np.ndarray],
    params: Dict[str, float]
) -> np.ndarray:
    """Deprecated: replaced by EFF_SIMPLE_V1. Stub retained for backward import safety."""
    raise NotImplementedError("pump_efficiency_method_main has been replaced by EFF_SIMPLE_V1")


# =====================================================
# pump_speed - 泵转速计算函数
# =====================================================

def calculate_pump_speed_method_a(
    data: Dict[str, np.ndarray],
    params: Dict[str, float]
) -> np.ndarray:
    """
    方法A：频率比例法（基于额定转速）

    公式:
        n = (pump_frequency / f_ref) × n_ref

    其中:
        - n: 实际转速（rpm）
        - pump_frequency: 泵变频频率（Hz）
        - f_ref: 参考频率（Hz，默认50）
        - n_ref: 额定转速（rpm，默认1500，对应50Hz时的转速）

    Args:
        data: 包含 pump_frequency
        params: 包含 f_ref, n_ref

    Returns:
        计算得到的实际转速数组（rpm）
    """
    f = data['pump_frequency']  # Hz
    f_ref = params.get('f_ref', 50.0)  # Hz
    n_ref = params.get('n_ref', 1500.0)  # rpm

    # 创建有效数据掩码
    valid_mask = ~np.isnan(f) & (f > 0)

    # 计算实际转速（初始化为NaN）
    n = np.full_like(f, np.nan)
    n[valid_mask] = (f[valid_mask] / f_ref) * n_ref

    return n


def calculate_pump_speed_method_b(
    data: Dict[str, np.ndarray],
    params: Dict[str, float]
) -> np.ndarray:
    """
    方法B：绝对转速法（基于电机学原理）

    公式:
        n_sync = 120 × f / P  # 同步转速（rpm）
        n = n_sync × (1 - s)  # 实际转速（rpm）

    其中:
        - n: 实际转速（rpm）
        - f: 频率（Hz）
        - P: 极对数（默认2，即4极电机）
        - s: 滑差（默认0.02，即2%）

    Args:
        data: 包含 pump_frequency
        params: 包含 poles_pair (或 pole_pairs), slip

    Returns:
        计算得到的转速数组（rpm）
    """
    f = data['pump_frequency']  # Hz
    # 支持两种参数名：poles_pair（数据库标准）和 pole_pairs（向后兼容）
    pole_pairs = params.get('poles_pair', params.get('pole_pairs', 2))  # 极对数
    slip = params.get('slip', 0.02)  # 滑差

    # 创建有效数据掩码
    valid_mask = ~np.isnan(f) & (f > 0)

    # 计算转速（初始化为NaN）
    n = np.full_like(f, np.nan)
    n_sync = 120.0 * f[valid_mask] / pole_pairs  # 同步转速
    n[valid_mask] = n_sync * (1.0 - slip)  # 实际转速

    return n


def calculate_pump_speed_method_c(
    data: Dict[str, np.ndarray],
    params: Dict[str, float]
) -> np.ndarray:
    """
    方法C：标定关系法

    公式:
        n = a × f + b

    其中:
        - n: 转速（rpm）
        - f: 频率（Hz）
        - a: 斜率（默认30，对应4极电机）
        - b: 截距（默认0）

    Args:
        data: 包含 pump_frequency
        params: 包含 calibration_a, calibration_b

    Returns:
        计算得到的转速数组（rpm）
    """
    f = data['pump_frequency']  # Hz
    a = params.get('calibration_a', 30.0)  # 斜率
    b = params.get('calibration_b', 0.0)  # 截距

    # 创建有效数据掩码
    valid_mask = ~np.isnan(f) & (f > 0)

    # 计算转速（初始化为NaN）
    n = np.full_like(f, np.nan)
    n[valid_mask] = a * f[valid_mask] + b

    return n


# =====================================================
# pump_torque - 泵扭矩计算函数
# =====================================================

def calculate_pump_torque_method_a(
    data: Dict[str, np.ndarray],
    params: Dict[str, float]
) -> np.ndarray:
    """
    方法A：水力功率与转速法（推荐）

    公式:
        P_shaft = ρ × g × (Q / 3600) × H / 1000  # 水力功率（kW）
        ω = 2π × n / 60  # 角速度（rad/s）
        T = P_shaft × 1000 / ω  # 扭矩（N·m）

    其中:
        - T: 扭矩（N·m）
        - P_shaft: 水力功率（kW）
        - ω: 角速度（rad/s）
        - Q: 流量（m³/h）
        - H: 扬程（m）
        - n: 转速（rpm）
        - ρ: 水密度（kg/m³，默认1000）
        - g: 重力加速度（m/s²，默认9.80665）

    Args:
        data: 包含 pump_flow_rate, pump_head, pump_speed
        params: 包含 rho, g

    Returns:
        计算得到的扭矩数组（N·m）
    """
    Q_m3h = data['pump_flow_rate']  # m³/h
    H = data['pump_head']  # m
    n = data['pump_speed']  # rpm

    # 物理常数必须从数据库读取
    try:
        rho = float(params['rho'])
        g = float(params['g'])
    except KeyError as e:
        raise ValueError(f"pump_torque_method_a 缺少必需的物理常数参数: {e}")

    # 检查数组长度一致性
    arrays = [Q_m3h, H, n]
    lengths = [len(arr) for arr in arrays if isinstance(arr, np.ndarray)]
    if len(set(lengths)) > 1:
        # 数组长度不一致，对齐到最短长度
        min_len = min(lengths)
        Q_m3h = Q_m3h[:min_len] if len(Q_m3h) > min_len else Q_m3h
        H = H[:min_len] if len(H) > min_len else H
        n = n[:min_len] if len(n) > min_len else n

    # 创建有效数据掩码
    valid_mask = ~np.isnan(Q_m3h) & ~np.isnan(H) & ~np.isnan(n) & (n > 0)

    # 计算扭矩（初始化为NaN）
    T = np.full_like(Q_m3h, np.nan)

    # 单位转换
    Q_m3s = Q_m3h[valid_mask] / 3600.0  # m³/h → m³/s
    omega = 2.0 * np.pi * n[valid_mask] / 60.0  # rpm → rad/s

    # 计算水力功率（kW）
    P_shaft = rho * g * Q_m3s * H[valid_mask] / 1000.0

    # 计算扭矩（N·m）
    T[valid_mask] = P_shaft * 1000.0 / omega

    return T


def calculate_pump_torque_method_b(
    data: Dict[str, np.ndarray],
    params: Dict[str, float]
) -> np.ndarray:
    """
    方法B：电功率与频率法

    公式:
        n = 120 × f / P × (1 - s)  # 转速（rpm）
        ω = 2π × n / 60  # 角速度（rad/s）
        T = P_in × 1000 / ω  # 扭矩（N·m）

    其中:
        - T: 扭矩（N·m）
        - P_in: 电功率（kW）
        - ω: 角速度（rad/s）
        - f: 频率（Hz）
        - P: 极对数（默认2）
        - s: 滑差（默认0.02）

    Args:
        data: 包含 pump_active_power, pump_frequency
        params: 包含 poles_pair (或 pole_pairs), slip

    Returns:
        计算得到的扭矩数组（N·m）
    """
    P_in = data['pump_active_power']  # kW
    f = data['pump_frequency']  # Hz

    # 支持两种参数名：poles_pair（数据库标准）和 pole_pairs（向后兼容）
    pole_pairs = params.get('poles_pair', params.get('pole_pairs', 2))  # 极对数
    slip = params.get('slip', 0.02)  # 滑差

    # 检查数组长度一致性
    arrays = [P_in, f]
    lengths = [len(arr) for arr in arrays if isinstance(arr, np.ndarray)]
    if len(set(lengths)) > 1:
        # 数组长度不一致，对齐到最短长度
        min_len = min(lengths)
        P_in = P_in[:min_len] if len(P_in) > min_len else P_in
        f = f[:min_len] if len(f) > min_len else f

    # 创建有效数据掩码
    valid_mask = ~np.isnan(P_in) & ~np.isnan(f) & (f > 0) & (P_in > 0)

    # 计算扭矩（初始化为NaN）
    T = np.full_like(P_in, np.nan)

    # 计算转速（rpm）
    n_sync = 120.0 * f[valid_mask] / pole_pairs
    n = n_sync * (1.0 - slip)

    # 计算角速度（rad/s）
    omega = 2.0 * np.pi * n / 60.0

    # 计算扭矩（N·m）
    T[valid_mask] = P_in[valid_mask] * 1000.0 / omega

    return T


# =====================================================
# main_pipeline_outlet_pressure - 总管出口压力计算函数
# =====================================================

def calculate_main_pipeline_outlet_pressure_method_a(
    data: Dict[str, np.ndarray],
    params: Dict[str, float]
) -> np.ndarray:
    """
    方法A：从单泵出口压力推算（设备级方法）

    公式:
        P_main_out = pump_outlet_pressure

    说明:
        适用于单泵系统，总管出口压力等于泵出口压力
        注意：这是设备级方法，不适用于多泵并联系统
        对于多泵系统，应使用方法C（泵站级聚合）

    Args:
        data: 包含 pump_outlet_pressure
        params: 空（不需要参数）

    Returns:
        计算得到的总管出口压力数组（MPa）
    """
    P_pump_out = data['pump_outlet_pressure']  # MPa
    return P_pump_out.copy()


def calculate_main_pipeline_outlet_pressure_method_b(
    data: Dict[str, np.ndarray],
    params: Dict[str, float]
) -> np.ndarray:
    """
    方法B：从泵进口压力和扬程推算（设备级方法）

    公式:
        P_main_out = P_in + ρ × g × H / 1e6

    其中:
        - P_main_out: 总管出口压力（MPa）
        - P_in: 泵进口压力（MPa）
        - H: 泵扬程（m）
        - ρ: 水密度（kg/m³，默认1000）
        - g: 重力加速度（m/s²，默认9.80665）

    说明:
        适用于单泵系统
        注意：这是设备级方法，不适用于多泵并联系统
        对于多泵系统，应使用方法C（泵站级聚合）

    Args:
        data: 包含 pump_inlet_pressure, pump_head
        params: 包含 rho, g

    Returns:
        计算得到的总管出口压力数组（MPa）
    """
    P_in = data['pump_inlet_pressure']  # MPa
    H = data['pump_head']  # m

    # 物理常数必须从数据库读取
    try:
        rho = float(params['rho'])
        g = float(params['g'])
    except KeyError as e:
        raise ValueError(f"pump_outlet_pressure_method_c 缺少必需的物理常数参数: {e}")

    # 创建有效数据掩码
    valid_mask = ~np.isnan(P_in) & ~np.isnan(H)

    # 计算总管出口压力（初始化为NaN）
    P_main_out = np.full_like(P_in, np.nan)
    P_main_out[valid_mask] = P_in[valid_mask] + rho * g * H[valid_mask] / 1e6

    return P_main_out


def calculate_main_pipeline_outlet_pressure_method_c(
    data: Dict[str, np.ndarray],
    params: Dict[str, float]
) -> np.ndarray:
    """
    方法C：从多泵出口压力聚合（泵站级方法）

    公式:
        P_main_out(t) = max(P_pump1_out(t), P_pump2_out(t), ..., P_pumpN_out(t))

    说明:
        这是泵站级计算方法，适用于多泵并联系统
        物理意义：并联泵组的总管出口压力由压力最高的泵决定

        数据格式：
        - data应包含泵站所有设备的pump_outlet_pressure数据
        - 格式：{'device_1': array, 'device_2': array, ...}
        - 或者：{'pump_outlet_pressure': 2D array (n_devices × n_timepoints)}

    Args:
        data: 包含多个设备的 pump_outlet_pressure 数据
        params: 包含 aggregation_method（默认'max'）

    Returns:
        计算得到的总管出口压力数组（MPa）
    """
    aggregation_method = params.get('aggregation_method', 'max')

    # 检查数据格式
    if 'pump_outlet_pressure' in data:
        # 格式1：单个键，值为2D数组或多个1D数组的列表
        pressure_data = data['pump_outlet_pressure']

        if isinstance(pressure_data, np.ndarray):
            if pressure_data.ndim == 1:
                # 单设备数据，直接返回
                return pressure_data.copy()
            elif pressure_data.ndim == 2:
                # 多设备数据 (n_devices × n_timepoints)
                if aggregation_method == 'max':
                    # 沿设备维度取最大值，忽略NaN
                    return np.nanmax(pressure_data, axis=0)
                elif aggregation_method == 'mean':
                    return np.nanmean(pressure_data, axis=0)
                else:
                    raise ValueError(f"不支持的聚合方法: {aggregation_method}")
        elif isinstance(pressure_data, list):
            # 列表形式的多设备数据
            pressure_arrays = [np.asarray(p) for p in pressure_data]
            stacked = np.stack(pressure_arrays, axis=0)
            if aggregation_method == 'max':
                return np.nanmax(stacked, axis=0)
            elif aggregation_method == 'mean':
                return np.nanmean(stacked, axis=0)
            else:
                raise ValueError(f"不支持的聚合方法: {aggregation_method}")
    else:
        # 格式2：多个键，每个键对应一个设备
        # 例如：{'device_1_pump_outlet_pressure': array, 'device_2_pump_outlet_pressure': array}
        pressure_keys = [k for k in data.keys() if 'pump_outlet_pressure' in k]

        if not pressure_keys:
            raise ValueError("数据中未找到pump_outlet_pressure相关字段")

        if len(pressure_keys) == 1:
            # 单设备
            return data[pressure_keys[0]].copy()

        # 多设备聚合
        pressure_arrays = [data[k] for k in pressure_keys]
        stacked = np.stack(pressure_arrays, axis=0)

        if aggregation_method == 'max':
            return np.nanmax(stacked, axis=0)
        elif aggregation_method == 'mean':
            return np.nanmean(stacked, axis=0)
        else:
            raise ValueError(f"不支持的聚合方法: {aggregation_method}")

    raise ValueError("无法解析数据格式")


# =====================================================
# main_pipeline_inlet_pressure - 总管进口压力计算函数
# =====================================================

def calculate_main_pipeline_inlet_pressure_method_a(
    data: Dict[str, np.ndarray],
    params: Dict[str, float]
) -> np.ndarray:
    """
    方法A：从单泵进口压力推算（设备级方法）

    公式:
        P_main_in = pump_inlet_pressure

    说明:
        适用于单泵系统，总管进口压力等于泵进口压力
        注意：这是设备级方法，不适用于多泵并联系统
        对于多泵系统，应使用方法C（泵站级聚合）

    Args:
        data: 包含 pump_inlet_pressure
        params: 空（不需要参数）

    Returns:
        计算得到的总管进口压力数组（MPa）
    """
    P_pump_in = data['pump_inlet_pressure']  # MPa
    return P_pump_in.copy()


def calculate_main_pipeline_inlet_pressure_method_b(
    data: Dict[str, np.ndarray],
    params: Dict[str, float]
) -> np.ndarray:
    """
    方法B：从水池液位推算（泵站级方法）

    公式:
        P_main_in = P_atm + ρ × g × L / 1e6

    其中:
        - P_main_in: 总管进口压力（MPa）
        - P_atm: 大气压（MPa，默认0.101325）
        - L: 水池液位（m）
        - ρ: 水密度（kg/m³，默认1000）
        - g: 重力加速度（m/s²，默认9.80665）

    说明:
        这是泵站级方法，从水池液位计算总管进口压力
        适用于所有泵共用一个进水池的情况

    Args:
        data: 包含 pool_liquid_level
        params: 包含 P_atm, rho, g

    Returns:
        计算得到的总管进口压力数组（MPa）
    """
    L = data['pool_liquid_level']  # m

    # 物理常数必须从数据库读取
    try:
        P_atm = float(params['P_atm'])
        rho = float(params['rho'])
        g = float(params['g'])
    except KeyError as e:
        raise ValueError(f"main_pipeline_inlet_pressure_method_b 缺少必需的物理常数参数: {e}")

    # 创建有效数据掩码
    valid_mask = ~np.isnan(L) & (L >= 0)

    # 计算总管进口压力（初始化为NaN）
    P_main_in = np.full_like(L, np.nan)
    P_main_in[valid_mask] = P_atm + rho * g * L[valid_mask] / 1e6

    return P_main_in


def calculate_main_pipeline_inlet_pressure_method_c(
    data: Dict[str, np.ndarray],
    params: Dict[str, float]
) -> np.ndarray:
    """
    方法C：从多泵进口压力聚合（泵站级方法）

    公式:
        P_main_in(t) = mean(P_pump1_in(t), P_pump2_in(t), ..., P_pumpN_in(t))

    说明:
        这是泵站级计算方法，适用于多泵并联系统
        物理意义：并联泵组的总管进口压力取各泵进口压力的平均值
        （因为进口压力相对稳定，各泵进口压力应该接近）

        数据格式：
        - data应包含泵站所有设备的pump_inlet_pressure数据
        - 格式：{'device_1': array, 'device_2': array, ...}
        - 或者：{'pump_inlet_pressure': 2D array (n_devices × n_timepoints)}

    Args:
        data: 包含多个设备的 pump_inlet_pressure 数据
        params: 包含 aggregation_method（默认'mean'）

    Returns:
        计算得到的总管进口压力数组（MPa）
    """
    aggregation_method = params.get('aggregation_method', 'mean')

    # 检查数据格式
    if 'pump_inlet_pressure' in data:
        # 格式1：单个键，值为2D数组或多个1D数组的列表
        pressure_data = data['pump_inlet_pressure']

        if isinstance(pressure_data, np.ndarray):
            if pressure_data.ndim == 1:
                # 单设备数据，直接返回
                return pressure_data.copy()
            elif pressure_data.ndim == 2:
                # 多设备数据 (n_devices × n_timepoints)
                if aggregation_method == 'mean':
                    # 沿设备维度取平均值，忽略NaN
                    return np.nanmean(pressure_data, axis=0)
                elif aggregation_method == 'max':
                    return np.nanmax(pressure_data, axis=0)
                else:
                    raise ValueError(f"不支持的聚合方法: {aggregation_method}")
        elif isinstance(pressure_data, list):
            # 列表形式的多设备数据
            pressure_arrays = [np.asarray(p) for p in pressure_data]
            stacked = np.stack(pressure_arrays, axis=0)
            if aggregation_method == 'mean':
                return np.nanmean(stacked, axis=0)
            elif aggregation_method == 'max':
                return np.nanmax(stacked, axis=0)
            else:
                raise ValueError(f"不支持的聚合方法: {aggregation_method}")
    else:
        # 格式2：多个键，每个键对应一个设备
        # 例如：{'device_1_pump_inlet_pressure': array, 'device_2_pump_inlet_pressure': array}
        pressure_keys = [k for k in data.keys() if 'pump_inlet_pressure' in k]

        if not pressure_keys:
            raise ValueError("数据中未找到pump_inlet_pressure相关字段")

        if len(pressure_keys) == 1:
            # 单设备
            return data[pressure_keys[0]].copy()

        # 多设备聚合
        pressure_arrays = [data[k] for k in pressure_keys]
        stacked = np.stack(pressure_arrays, axis=0)

        if aggregation_method == 'mean':
            return np.nanmean(stacked, axis=0)
        elif aggregation_method == 'max':
            return np.nanmax(stacked, axis=0)
        else:
            raise ValueError(f"不支持的聚合方法: {aggregation_method}")

    raise ValueError("无法解析数据格式")


# =====================================================
# pump_cumulative_flow - 泵累计流量计算函数
# =====================================================

def calculate_pump_cumulative_flow_method_a(
    data: Dict[str, np.ndarray],
    params: Dict[str, float]
) -> np.ndarray:
    """
    方法A：从瞬时流量积分（向量化实现）

    公式:
        V(t) = V(t-1) + Q(t) × Δt / 3600

    其中:
        - V(t): t时刻的累计流量（m³）
        - Q(t): t时刻的瞬时流量（m³/h）
        - Δt: 时间间隔（秒）

    说明:
        这是一个累积计算，需要知道初始累计值和时间间隔
        使用NumPy向量化操作（np.cumsum）替代for循环，性能提升10-100倍

    Args:
        data: 包含 pump_flow_rate
        params: 包含 initial_value, time_interval

    Returns:
        计算得到的累计流量数组（m³）
    """
    Q = data['pump_flow_rate']  # m³/h

    initial_value = params.get('initial_value', 0.0)  # m³
    time_interval = params.get('time_interval', 1.0)  # 秒

    # 创建有效数据掩码
    valid_mask = ~np.isnan(Q) & (Q >= 0)

    # 将无效值填充为0（用于累加计算）
    Q_filled = np.where(valid_mask, Q, 0.0)

    # 计算每个时间点的增量（m³）
    delta_V = Q_filled * time_interval / 3600.0  # m³/h × s / 3600 = m³

    # 使用np.cumsum进行向量化累积计算
    V = initial_value + np.cumsum(delta_V)

    # 将原本无效的位置恢复为NaN
    V[~valid_mask] = np.nan

    return V


def calculate_pump_cumulative_flow_method_b(
    data: Dict[str, np.ndarray],
    params: Dict[str, float]
) -> np.ndarray:
    """
    方法B：从总管累计流量按比例分摊

    公式:
        V_pump = V_main × (Q_pump / Q_main)

    其中:
        - V_pump: 泵累计流量（m³）
        - V_main: 总管累计流量（m³）
        - Q_pump: 泵瞬时流量（m³/h）
        - Q_main: 总管瞬时流量（m³/h）

    Args:
        data: 包含 main_pipeline_cumulative_flow, pump_flow_rate, main_pipeline_flow_rate
        params: 空（不需要参数）

    Returns:
        计算得到的累计流量数组（m³）
    """
    V_main = data['main_pipeline_cumulative_flow']  # m³
    Q_pump = data['pump_flow_rate']  # m³/h
    Q_main = data['main_pipeline_flow_rate']  # m³/h

    # 创建有效数据掩码
    valid_mask = ~np.isnan(V_main) & ~np.isnan(Q_pump) & ~np.isnan(Q_main) & (Q_main > 0)

    # 计算泵累计流量（初始化为NaN）
    V_pump = np.full_like(V_main, np.nan)
    V_pump[valid_mask] = V_main[valid_mask] * (Q_pump[valid_mask] / Q_main[valid_mask])

    return V_pump


# =====================================================
# 计算函数注册表
# =====================================================

CALCULATOR_REGISTRY = {
    'pump_flow_rate_method_a': calculate_pump_flow_rate_method_a,
    'pump_flow_rate_method_b': calculate_pump_flow_rate_method_b,
    'pump_flow_rate_method_c': calculate_pump_flow_rate_method_c,
    'pump_flow_rate_method_d': calculate_pump_flow_rate_method_d,
    'pump_flow_rate_method_e': calculate_pump_flow_rate_method_e,
    'pump_flow_rate_method_f': calculate_pump_flow_rate_method_f,
    'pump_head_method_main': calculate_pump_head_method_main,
    # replaced: 'pump_head_method_main' → new HEAD_COEF_V1
    'HEAD_COEF_V1': calculate_head_coef_v1,
    # pump_inlet_pressure (2个) - 新增 (manual_fix_1.1)
    'pump_inlet_pressure_method_a': calculate_pump_inlet_pressure_method_a,
    'pump_inlet_pressure_method_b': calculate_pump_inlet_pressure_method_b,
    'pump_outlet_pressure_method_a': calculate_pump_outlet_pressure_method_a,
    'pump_outlet_pressure_method_b': calculate_pump_outlet_pressure_method_b,
    'pump_outlet_pressure_method_c': calculate_pump_outlet_pressure_method_c,
    'pump_outlet_pressure_method_d': calculate_pump_outlet_pressure_method_d,
    # replaced: 'pump_efficiency_method_main' → new EFF_SIMPLE_V1
    'EFF_SIMPLE_V1': calculate_eff_simple_v1,
    # pump_efficiency (2个) - 新增 EFF_CURVE_V1 (manual_fix_3.3)
    'EFF_CURVE_V1': calculate_pump_efficiency_eff_curve_v1,
    'pump_speed_method_a': calculate_pump_speed_method_a,
    'pump_speed_method_b': calculate_pump_speed_method_b,
    'pump_speed_method_c': calculate_pump_speed_method_c,
    'pump_torque_method_a': calculate_pump_torque_method_a,
    'pump_torque_method_b': calculate_pump_torque_method_b,
    # main_pipeline_inlet_pressure (4个) - 新增 method_a 和 method_c (manual_fix_2.3)
    'main_pipeline_inlet_pressure_method_a': calculate_main_pipeline_inlet_pressure_method_a,
    'main_pipeline_inlet_pressure_method_b': calculate_main_pipeline_inlet_pressure_method_b,
    'main_pipeline_inlet_pressure_method_c': calculate_main_pipeline_inlet_pressure_method_c,
    'main_pipeline_outlet_pressure_method_a': calculate_main_pipeline_outlet_pressure_method_a,
    'main_pipeline_outlet_pressure_method_b': calculate_main_pipeline_outlet_pressure_method_b,
    'main_pipeline_outlet_pressure_method_c': calculate_main_pipeline_outlet_pressure_method_c,
    # replaced: inlet_pressure methods → new PIN_COEF_V1
    'PIN_COEF_V1': calculate_pin_coef_v1,
    'pump_cumulative_flow_method_a': calculate_pump_cumulative_flow_method_a,
    'pump_cumulative_flow_method_b': calculate_pump_cumulative_flow_method_b,
}


def get_calculator(method_id: str):
    """
    获取计算函数

    Args:
        method_id: 方法ID（如 'pump_flow_rate_method_a'）

    Returns:
        计算函数

    Raises:
        KeyError: 如果方法ID不存在
    """
    if method_id not in CALCULATOR_REGISTRY:
        raise KeyError(f"未找到计算函数: {method_id}")

    return CALCULATOR_REGISTRY[method_id]


def get_calculator_unified(method_id: str):
    """
    获取统一签名的计算器包装函数。

    新签名：fn(ctx: CalculationContext, method: MethodDescriptor, data: Dict[str, np.ndarray]) -> Tuple[np.ndarray, Dict]
    旧实现保持不变，通过包装层适配参数与返回值。
    """
    base_fn = get_calculator(method_id)

    def _wrapped(ctx: CalculationContext, method: MethodDescriptor, data: Dict[str, np.ndarray]) -> Tuple[np.ndarray, Dict[str, Any]]:
        # 参数来源优先 method.params，其次为空字典（后续由参数管理装配）
        params = getattr(method, "params", {}) or {}
        values = base_fn(data, params)
        meta: Dict[str, Any] = {"method_id": method.method_id, "method_code": method.method_code}
        return values, meta

    return _wrapped


