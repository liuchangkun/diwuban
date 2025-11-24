"""
参数优化脚本：基于实测总管出口压力校准泵计算参数

核心思路：
1. 实测数据：总管出口压力（main_pipeline_outlet_pressure）
2. 物理约束：总管出口压力 ≈ MAX(各泵出口压力)（并联系统）
3. 优化目标：调整参数使计算的泵出口压力与实测总管出口压力匹配

优化参数：
- K_eq: 等效损失系数（影响 pump_inlet_pressure）
- L_offset: 水池底部到泵入口的垂直距离（影响 pump_inlet_pressure）
- pipe_diameter: 入口管道直径（影响 pump_inlet_pressure）

优化方法：
- 使用最小二乘法拟合参数
- 使用物理约束限制参数范围
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import numpy as np
import pandas as pd
from scipy.optimize import minimize, differential_evolution
from datetime import datetime
import pytz
from app.core.database import get_connection

# 物理常数
P_ATM = 0.101325  # MPa
RHO = 1000.0  # kg/m³
G = 9.80665  # m/s²


def load_data(start_time, end_time, device_ids):
    """加载实测和计算数据"""
    print(f"\n📊 加载数据...")
    print(f"  时间范围: {start_time} ~ {end_time}")
    print(f"  设备: {device_ids}")
    
    with get_connection() as conn:
        # 加载实测总管出口压力
        df_main = pd.read_sql("""
            SELECT 
                ts_raw,
                value as main_outlet_pressure
            FROM fact_measurements
            WHERE metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'main_pipeline_outlet_pressure')
              AND device_id = 7
              AND ts_raw >= %(start_time)s
              AND ts_raw < %(end_time)s
            ORDER BY ts_raw
        """, conn, params={'start_time': start_time, 'end_time': end_time})
        
        # 加载原始数据（用于重新计算）
        df_raw = pd.read_sql("""
            SELECT 
                fm.ts_raw,
                fm.device_id,
                mc.metric_key,
                fm.value
            FROM fact_measurements fm
            JOIN dim_metric_config mc ON fm.metric_id = mc.id
            WHERE mc.metric_key IN ('pool_liquid_level', 'pump_flow_rate', 'running')
              AND fm.device_id IN %(device_ids)s
              AND fm.ts_raw >= %(start_time)s
              AND fm.ts_raw < %(end_time)s
        """, conn, params={'device_ids': tuple(device_ids), 'start_time': start_time, 'end_time': end_time})
    
    print(f"  ✅ 实测总管出口压力: {len(df_main)} 条")
    print(f"  ✅ 原始数据: {len(df_raw)} 条")
    
    return df_main, df_raw


def calculate_pump_pressures(df_raw, device_id, K_eq, L_offset, pipe_diameter):
    """
    根据参数计算泵的入口压力和出口压力
    
    公式：
    1. 入口压力：P_in = P_atm + ρ×g×(h_static - h_loss) / 1e6
       - h_static = pool_liquid_level + L_offset
       - h_loss = K_eq × v² / (2g)
       - v = Q / (3600 × π × D² / 4)
    
    2. 出口压力：P_out = P_in + ρ×g×H / 1e6
       - H 是扬程，需要从特性曲线或经验公式获得
       - 这里我们假设 H 与流量有关：H = a - b×Q²（简化模型）
    """
    df_device = df_raw[df_raw['device_id'] == device_id].copy()
    
    # 数据透视
    df_pivot = df_device.pivot_table(
        index='ts_raw',
        columns='metric_key',
        values='value',
        aggfunc='first'
    ).reset_index()
    
    # 计算入口压力
    pool_level = df_pivot['pool_liquid_level'].values
    flow_rate = df_pivot['pump_flow_rate'].values
    
    # 静压头
    h_static = pool_level + L_offset
    
    # 流速
    v = flow_rate / (3600 * np.pi * (pipe_diameter ** 2) / 4)
    
    # 摩擦损失
    h_loss = K_eq * (v ** 2) / (2 * G)
    
    # 入口压力
    P_in = P_ATM + RHO * G * (h_static - h_loss) / 1e6
    
    df_pivot['pump_inlet_pressure'] = P_in
    
    return df_pivot


def objective_function(params, df_main, df_raw, device_ids):
    """
    目标函数：最小化计算的泵出口压力与实测总管出口压力的误差
    
    Args:
        params: [K_eq, L_offset, pipe_diameter, H_a, H_b]
            - K_eq: 等效损失系数
            - L_offset: 垂直距离 (m)
            - pipe_diameter: 管道直径 (m)
            - H_a, H_b: 扬程曲线参数 H = H_a - H_b×Q²
    """
    K_eq, L_offset, pipe_diameter, H_a, H_b = params
    
    # 计算每台泵的出口压力
    pump_pressures = []
    
    for device_id in device_ids:
        df_device = calculate_pump_pressures(df_raw, device_id, K_eq, L_offset, pipe_diameter)
        
        # 计算扬程（简化模型）
        Q = df_device['pump_flow_rate'].values
        H = H_a - H_b * (Q ** 2)
        H = np.maximum(H, 0)  # 扬程不能为负
        
        # 计算出口压力
        P_in = df_device['pump_inlet_pressure'].values
        P_out = P_in + RHO * G * H / 1e6
        
        df_device['pump_outlet_pressure'] = P_out
        pump_pressures.append(df_device[['ts_raw', 'pump_outlet_pressure']])
    
    # 合并所有泵的数据，取最大值（并联系统）
    df_all = pd.concat(pump_pressures)
    df_max = df_all.groupby('ts_raw')['pump_outlet_pressure'].max().reset_index()
    
    # 与实测数据对齐
    df_merged = pd.merge(df_main, df_max, on='ts_raw', how='inner')
    
    # 计算误差（均方根误差）
    error = np.sqrt(np.mean((df_merged['main_outlet_pressure'] - df_merged['pump_outlet_pressure']) ** 2))
    
    return error


def main():
    """主函数"""
    print("="*100)
    print("🎯 参数优化：基于实测总管出口压力校准泵计算参数")
    print("="*100)
    
    # 时间范围（使用1小时数据进行优化，避免计算量过大）
    tz = pytz.timezone('Asia/Shanghai')
    start_time = datetime(2025, 10, 22, 16, 0, 0, tzinfo=tz)
    end_time = datetime(2025, 10, 22, 17, 0, 0, tzinfo=tz)
    
    # 设备列表
    device_ids = [1, 2, 3, 4, 5, 6]
    
    # 加载数据
    df_main, df_raw = load_data(start_time, end_time, device_ids)
    
    print(f"\n🔧 开始参数优化...")
    print(f"  优化参数: K_eq, L_offset, pipe_diameter, H_a, H_b")
    print(f"  优化方法: 差分进化算法（全局优化）")
    
    # 参数边界
    bounds = [
        (0.5, 10.0),    # K_eq: 等效损失系数
        (1.0, 5.0),     # L_offset: 垂直距离 (m)
        (0.2, 0.5),     # pipe_diameter: 管道直径 (m)
        (50.0, 150.0),  # H_a: 扬程曲线参数
        (0.0, 0.01)     # H_b: 扬程曲线参数
    ]
    
    # 使用差分进化算法进行全局优化
    result = differential_evolution(
        objective_function,
        bounds,
        args=(df_main, df_raw, device_ids),
        maxiter=100,
        popsize=15,
        tol=0.001,
        seed=42,
        disp=True
    )
    
    print(f"\n✅ 优化完成！")
    print(f"  最优参数:")
    print(f"    K_eq = {result.x[0]:.4f}")
    print(f"    L_offset = {result.x[1]:.4f} m")
    print(f"    pipe_diameter = {result.x[2]:.4f} m")
    print(f"    H_a = {result.x[3]:.4f}")
    print(f"    H_b = {result.x[4]:.6f}")
    print(f"  最小误差 (RMSE): {result.fun:.6f} MPa")
    
    return result


if __name__ == '__main__':
    result = main()

