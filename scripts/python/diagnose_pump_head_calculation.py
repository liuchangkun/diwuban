"""
诊断 pump_head 计算误差问题

分析当前计算逻辑和参数，找出为什么计算值比实测值高120-180%
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import pandas as pd
import numpy as np
from pathlib import Path
from app.core.config.loader import load_settings
from app.adapters.db import init_database, get_connection

# 初始化数据库
settings = load_settings(Path('configs'))
init_database(settings)

print("="*100)
print("🔍 pump_head 计算误差诊断")
print("="*100)

# 时间范围
start_time = '2025-10-22 16:00:00+08:00'
end_time = '2025-10-22 17:00:00+08:00'

print(f"\n📊 分析时间范围: {start_time} ~ {end_time}")

with get_connection() as conn:
    # 1. 加载实测总管出口压力
    print("\n" + "="*100)
    print("1️⃣ 实测总管出口压力（device_id=7）")
    print("="*100)
    
    df_main = pd.read_sql("""
        SELECT 
            ts_raw,
            value as main_pipeline_outlet_pressure
        FROM fact_measurements
        WHERE metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'main_pipeline_outlet_pressure')
          AND device_id = 7
          AND ts_raw >= %s
          AND ts_raw < %s
        ORDER BY ts_raw
    """, conn, params=(start_time, end_time))
    
    print(f"  记录数: {len(df_main)}")
    print(f"  平均值: {df_main['main_pipeline_outlet_pressure'].mean():.4f} MPa")
    print(f"  范围: {df_main['main_pipeline_outlet_pressure'].min():.4f} ~ {df_main['main_pipeline_outlet_pressure'].max():.4f} MPa")
    
    # 2. 加载计算的泵出口压力和扬程
    print("\n" + "="*100)
    print("2️⃣ 计算的泵出口压力和扬程（device_id=1-6）")
    print("="*100)
    
    df_calc = pd.read_sql("""
        SELECT 
            fm.device_id,
            fm.ts_raw,
            mc.metric_key,
            fm.value
        FROM fact_measurements fm
        JOIN dim_metric_config mc ON mc.id = fm.metric_id
        WHERE mc.metric_key IN ('pump_outlet_pressure', 'pump_head', 'pump_inlet_pressure')
          AND fm.device_id IN (1, 2, 3, 4, 5, 6)
          AND fm.ts_raw >= %s
          AND fm.ts_raw < %s
        ORDER BY fm.device_id, fm.ts_raw, mc.metric_key
    """, conn, params=(start_time, end_time))
    
    # 透视数据
    df_pivot = df_calc.pivot_table(
        index=['device_id', 'ts_raw'],
        columns='metric_key',
        values='value',
        aggfunc='first'
    ).reset_index()
    
    print(f"  记录数: {len(df_pivot)}")
    print(f"\n  各设备统计:")
    for device_id in sorted(df_pivot['device_id'].unique()):
        df_dev = df_pivot[df_pivot['device_id'] == device_id]
        print(f"\n    设备 {device_id}:")
        print(f"      pump_outlet_pressure: {df_dev['pump_outlet_pressure'].mean():.4f} MPa (范围: {df_dev['pump_outlet_pressure'].min():.4f} ~ {df_dev['pump_outlet_pressure'].max():.4f})")
        print(f"      pump_head: {df_dev['pump_head'].mean():.2f} m (范围: {df_dev['pump_head'].min():.2f} ~ {df_dev['pump_head'].max():.2f})")
        print(f"      pump_inlet_pressure: {df_dev['pump_inlet_pressure'].mean():.4f} MPa (范围: {df_dev['pump_inlet_pressure'].min():.4f} ~ {df_dev['pump_inlet_pressure'].max():.4f})")
    
    # 3. 分析计算公式
    print("\n" + "="*100)
    print("3️⃣ 分析当前计算公式")
    print("="*100)
    
    # 加载参数
    df_params = pd.read_sql("""
        SELECT 
            device_id,
            param_name,
            param_value
        FROM calculation_parameters
        WHERE metric_key = 'pump_head'
          AND method_id = 'pipe_loss_multi_pump'
          AND (device_id IN (1, 2, 3, 4, 5, 6) OR (device_id IS NULL AND station_id = 1))
        ORDER BY device_id NULLS FIRST, param_name
    """, conn)
    
    print("\n  当前参数:")
    for _, row in df_params.iterrows():
        device_str = f"设备{row['device_id']}" if pd.notna(row['device_id']) else "泵站级"
        print(f"    {device_str} - {row['param_name']}: {row['param_value']}")
    
    # 4. 反推合理参数
    print("\n" + "="*100)
    print("4️⃣ 反推合理参数")
    print("="*100)
    
    # 合并数据
    df_pivot['ts_bucket'] = df_pivot['ts_raw'].dt.floor('1s')
    df_main['ts_bucket'] = df_main['ts_raw'].dt.floor('1s')
    
    df_merged = df_pivot.merge(
        df_main[['ts_bucket', 'main_pipeline_outlet_pressure']],
        on='ts_bucket',
        how='inner',
        suffixes=('_calc', '_measured')
    )
    
    print(f"  合并后记录数: {len(df_merged)}")
    
    # 计算合理的泵出口压力（应该接近实测总管出口压力）
    df_merged['reasonable_pump_outlet_pressure'] = df_merged['main_pipeline_outlet_pressure']
    
    # 计算合理的扬程
    df_merged['reasonable_pump_head'] = (
        (df_merged['reasonable_pump_outlet_pressure'] - df_merged['pump_inlet_pressure']) * 1e6 / (1000.0 * 9.81)
    )
    
    print(f"\n  合理值统计:")
    print(f"    合理泵出口压力: {df_merged['reasonable_pump_outlet_pressure'].mean():.4f} MPa")
    print(f"    合理扬程: {df_merged['reasonable_pump_head'].mean():.2f} m")
    
    print(f"\n  当前计算值 vs 合理值:")
    print(f"    泵出口压力误差: {((df_merged['pump_outlet_pressure'].mean() / df_merged['reasonable_pump_outlet_pressure'].mean()) - 1) * 100:.1f}%")
    print(f"    扬程误差: {((df_merged['pump_head'].mean() / df_merged['reasonable_pump_head'].mean()) - 1) * 100:.1f}%")
    
    # 5. 分析问题根源
    print("\n" + "="*100)
    print("5️⃣ 问题根源分析")
    print("="*100)
    
    print("\n  当前计算公式:")
    print("    P_pump_out = P_main_out × correction_factor + delta_P_pipe")
    print("    其中:")
    print("      correction_factor = 1 + alpha_multi_pump × N_running / N_total")
    print("      delta_P_pipe = K_pipe_loss × Q²")
    
    print("\n  问题分析:")
    print("    ❌ correction_factor 会放大 P_main_out，导致 P_pump_out 偏高")
    print("    ❌ delta_P_pipe 是正值，进一步增加 P_pump_out")
    print("    ✅ 正确的逻辑应该是：P_pump_out ≈ P_main_out（并联系统）")
    
    # 6. 计算修正系数
    print("\n" + "="*100)
    print("6️⃣ 计算修正系数")
    print("="*100)
    
    # 反推 correction_factor 和 delta_P_pipe
    # 假设当前公式：P_pump_out_calc = P_main_out × correction_factor + delta_P_pipe
    # 合理公式：P_pump_out_reasonable = P_main_out
    
    # 简化分析：假设 correction_factor 是主要问题
    avg_correction_factor = df_merged['pump_outlet_pressure'].mean() / df_merged['main_pipeline_outlet_pressure'].mean()
    
    print(f"\n  当前平均 correction_factor（反推）: {avg_correction_factor:.4f}")
    print(f"  合理 correction_factor: 1.0000")
    print(f"  建议修正: 将 alpha_multi_pump 设置为 0（禁用多泵修正）")
    print(f"  建议修正: 将 K_pipe_loss 设置为 0（禁用管道损失修正）")

print("\n" + "="*100)
print("✅ 诊断完成！")
print("="*100)

