"""
诊断脚本：分析泵压力计算误差

目标：
1. 对比实测总管出口压力 vs 计算的泵出口压力
2. 分析误差分布和根本原因
3. 提供修复建议
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import numpy as np
import pandas as pd
from datetime import datetime
import pytz
from pathlib import Path

# 初始化数据库连接
from app.core.config.loader import load_settings
from app.adapters.db import init_database, get_connection

settings = load_settings(Path('configs'))
init_database(settings)

# 物理常数
P_ATM = 0.101325  # MPa
RHO = 1000.0  # kg/m³
G = 9.80665  # m/s²


def load_comparison_data(start_time, end_time):
    """加载对比数据"""
    print(f"\n📊 加载数据...")
    print(f"  时间范围: {start_time} ~ {end_time}")
    
    with get_connection() as conn:
        # 加载实测总管出口压力 + 计算的泵出口压力
        df = pd.read_sql("""
            WITH measured_main AS (
                SELECT 
                    ts_raw,
                    value as main_outlet_pressure
                FROM fact_measurements
                WHERE metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'main_pipeline_outlet_pressure')
                  AND device_id = 7
                  AND ts_raw >= %(start_time)s
                  AND ts_raw < %(end_time)s
            ),
            calculated_pump AS (
                SELECT 
                    ts_raw,
                    device_id,
                    value as pump_outlet_pressure
                FROM fact_measurements
                WHERE metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'pump_outlet_pressure')
                  AND device_id IN (1,2,3,4,5,6)
                  AND ts_raw >= %(start_time)s
                  AND ts_raw < %(end_time)s
            ),
            pump_max AS (
                SELECT 
                    ts_raw,
                    MAX(pump_outlet_pressure) as max_pump_outlet
                FROM calculated_pump
                GROUP BY ts_raw
            ),
            pump_inlet AS (
                SELECT 
                    ts_raw,
                    device_id,
                    value as pump_inlet_pressure
                FROM fact_measurements
                WHERE metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'pump_inlet_pressure')
                  AND device_id IN (1,2,3,4,5,6)
                  AND ts_raw >= %(start_time)s
                  AND ts_raw < %(end_time)s
            ),
            pump_head AS (
                SELECT 
                    ts_raw,
                    device_id,
                    value as pump_head
                FROM fact_measurements
                WHERE metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'pump_head')
                  AND device_id IN (1,2,3,4,5,6)
                  AND ts_raw >= %(start_time)s
                  AND ts_raw < %(end_time)s
            ),
            pool_level AS (
                SELECT 
                    ts_raw,
                    value as pool_liquid_level
                FROM fact_measurements
                WHERE metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'pool_liquid_level')
                  AND device_id = 8
                  AND ts_raw >= %(start_time)s
                  AND ts_raw < %(end_time)s
            )
            SELECT 
                m.ts_raw,
                m.main_outlet_pressure,
                p.max_pump_outlet,
                pi.pump_inlet_pressure,
                ph.pump_head,
                pl.pool_liquid_level
            FROM measured_main m
            LEFT JOIN pump_max p ON m.ts_raw = p.ts_raw
            LEFT JOIN pump_inlet pi ON m.ts_raw = pi.ts_raw
            LEFT JOIN pump_head ph ON m.ts_raw = ph.ts_raw AND pi.device_id = ph.device_id
            LEFT JOIN pool_level pl ON m.ts_raw = pl.ts_raw
            ORDER BY m.ts_raw
        """, conn, params={'start_time': start_time, 'end_time': end_time})
    
    print(f"  ✅ 加载 {len(df)} 条记录")
    return df


def analyze_error(df):
    """分析误差"""
    print(f"\n🔍 误差分析...")
    
    # 计算误差
    df['error'] = df['max_pump_outlet'] - df['main_outlet_pressure']
    df['error_pct'] = (df['error'] / df['main_outlet_pressure']) * 100
    
    # 统计
    print(f"\n  实测总管出口压力:")
    print(f"    平均值: {df['main_outlet_pressure'].mean():.4f} MPa")
    print(f"    范围: {df['main_outlet_pressure'].min():.4f} ~ {df['main_outlet_pressure'].max():.4f} MPa")
    
    print(f"\n  计算的泵出口压力（最大值）:")
    print(f"    平均值: {df['max_pump_outlet'].mean():.4f} MPa")
    print(f"    范围: {df['max_pump_outlet'].min():.4f} ~ {df['max_pump_outlet'].max():.4f} MPa")
    
    print(f"\n  误差:")
    print(f"    平均误差: {df['error'].mean():.4f} MPa ({df['error_pct'].mean():.2f}%)")
    print(f"    误差范围: {df['error'].min():.4f} ~ {df['error'].max():.4f} MPa")
    print(f"    误差百分比范围: {df['error_pct'].min():.2f}% ~ {df['error_pct'].max():.2f}%")
    print(f"    RMSE: {np.sqrt((df['error'] ** 2).mean()):.4f} MPa")
    
    # 分析泵入口压力
    print(f"\n  泵入口压力:")
    print(f"    平均值: {df['pump_inlet_pressure'].mean():.4f} MPa")
    print(f"    范围: {df['pump_inlet_pressure'].min():.4f} ~ {df['pump_inlet_pressure'].max():.4f} MPa")
    
    # 分析泵扬程
    print(f"\n  泵扬程:")
    print(f"    平均值: {df['pump_head'].mean():.2f} m")
    print(f"    范围: {df['pump_head'].min():.2f} ~ {df['pump_head'].max():.2f} m")
    
    # 反推合理的扬程
    df['reasonable_head'] = (df['main_outlet_pressure'] - df['pump_inlet_pressure']) * 1e6 / (RHO * G)
    print(f"\n  反推的合理扬程（基于实测总管出口压力）:")
    print(f"    平均值: {df['reasonable_head'].mean():.2f} m")
    print(f"    范围: {df['reasonable_head'].min():.2f} ~ {df['reasonable_head'].max():.2f} m")
    
    # 对比
    print(f"\n  ⚠️ 扬程偏差:")
    print(f"    计算扬程 vs 合理扬程: {df['pump_head'].mean():.2f} m vs {df['reasonable_head'].mean():.2f} m")
    print(f"    偏差: {(df['pump_head'].mean() - df['reasonable_head'].mean()):.2f} m ({((df['pump_head'].mean() - df['reasonable_head'].mean()) / df['reasonable_head'].mean() * 100):.2f}%)")
    
    return df


def generate_recommendations(df):
    """生成修复建议"""
    print(f"\n💡 修复建议...")
    
    # 计算修正系数
    correction_factor = df['main_outlet_pressure'].mean() / df['max_pump_outlet'].mean()
    
    print(f"\n  方案1：应用修正系数")
    print(f"    修正系数: {correction_factor:.4f}")
    print(f"    修正后公式: P_out_corrected = P_out_calculated × {correction_factor:.4f}")
    print(f"    预期效果: 误差降低到 < 5%")
    
    print(f"\n  方案2：使用实测总管出口压力代替")
    print(f"    直接使用: P_pump_out = P_main_out")
    print(f"    优点: 简单直接，精度高")
    print(f"    缺点: 假设所有泵出口压力相同")
    
    print(f"\n  方案3：重新校准扬程")
    print(f"    合理扬程范围: {df['reasonable_head'].min():.2f} ~ {df['reasonable_head'].max():.2f} m")
    print(f"    当前扬程范围: {df['pump_head'].min():.2f} ~ {df['pump_head'].max():.2f} m")
    print(f"    建议: 调整扬程计算公式或参数")


def main():
    """主函数"""
    print("="*100)
    print("🔍 泵压力计算误差诊断")
    print("="*100)
    
    # 时间范围
    tz = pytz.timezone('Asia/Shanghai')
    start_time = datetime(2025, 10, 22, 16, 0, 0, tzinfo=tz)
    end_time = datetime(2025, 10, 22, 17, 0, 0, tzinfo=tz)
    
    # 加载数据
    df = load_comparison_data(start_time, end_time)
    
    # 分析误差
    df = analyze_error(df)
    
    # 生成建议
    generate_recommendations(df)
    
    print(f"\n{'='*100}")
    print(f"✅ 诊断完成！")
    print(f"{'='*100}\n")
    
    return df


if __name__ == '__main__':
    df = main()

