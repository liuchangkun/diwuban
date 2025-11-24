"""
K_eq 参数优化

优化方法:
1. 查询历史数据（pool_liquid_level, pump_flow_rate, pump_inlet_pressure）
2. 假设合理的压力范围（0.10-0.15 MPa）
3. 反推每个数据点的 K_eq
4. 计算中位数/平均值作为优化后的 K_eq
5. 更新参数表并重新计算

执行方式:
    python scripts/optimize_K_eq_20251119.py
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import init_database, get_connection
from app.core.config.loader import load_settings

def main():
    """K_eq 参数优化"""
    print("=" * 100)
    print("K_eq 参数优化")
    print("=" * 100)
    
    # 加载配置并初始化数据库
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    # 查询历史数据
    print("\n[1/5] 查询历史数据...")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 查询 metric_id
            cur.execute("""
                SELECT id, metric_key FROM dim_metric_config 
                WHERE metric_key IN ('pump_inlet_pressure', 'pump_flow_rate', 'pool_liquid_level')
            """)
            
            metric_map = {row[1]: row[0] for row in cur.fetchall()}
            print(f"   ✓ metric_id 映射: {metric_map}")
            
            # 查询历史数据（设备1-6的pump_inlet_pressure, pump_flow_rate, 设备8的pool_liquid_level）
            cur.execute("""
                WITH pump_data AS (
                    SELECT 
                        ts_bucket,
                        device_id,
                        MAX(CASE WHEN metric_id = %(pressure_id)s THEN value END) as pressure,
                        MAX(CASE WHEN metric_id = %(flow_id)s THEN value END) as flow_rate
                    FROM fact_measurements
                    WHERE device_id IN (1, 2, 3, 4, 5, 6)
                      AND metric_id IN (%(pressure_id)s, %(flow_id)s)
                      AND ts_bucket >= '2025-10-22 16:00:00+08:00'
                      AND ts_bucket <= '2025-10-23 15:20:00+08:00'
                    GROUP BY ts_bucket, device_id
                ),
                pool_data AS (
                    SELECT 
                        ts_bucket,
                        value as pool_level
                    FROM fact_measurements
                    WHERE device_id = 8
                      AND metric_id = %(pool_id)s
                      AND ts_bucket >= '2025-10-22 16:00:00+08:00'
                      AND ts_bucket <= '2025-10-23 15:20:00+08:00'
                )
                SELECT 
                    p.device_id,
                    p.ts_bucket,
                    p.pressure,
                    p.flow_rate,
                    pl.pool_level
                FROM pump_data p
                JOIN pool_data pl ON p.ts_bucket = pl.ts_bucket
                WHERE p.pressure IS NOT NULL 
                  AND p.flow_rate IS NOT NULL 
                  AND pl.pool_level IS NOT NULL
                  AND p.flow_rate > 100  -- 只选择有流量的数据点
                ORDER BY p.device_id, p.ts_bucket
                LIMIT 100000
            """, {
                'pressure_id': metric_map['pump_inlet_pressure'],
                'flow_id': metric_map['pump_flow_rate'],
                'pool_id': metric_map['pool_liquid_level']
            })
            
            rows = cur.fetchall()
            print(f"   ✓ 查询到 {len(rows)} 条有效数据")
    
    if len(rows) == 0:
        print("\n⚠️  没有足够的数据进行优化")
        return
    
    # 转换为 DataFrame
    df = pd.DataFrame(rows, columns=['device_id', 'ts_bucket', 'pressure', 'flow_rate', 'pool_level'])

    # 转换 Decimal 为 float
    df['pressure'] = df['pressure'].astype(float)
    df['flow_rate'] = df['flow_rate'].astype(float)
    df['pool_level'] = df['pool_level'].astype(float)

    print(f"\n   数据统计:")
    print(f"      设备数量: {df['device_id'].nunique()}")
    print(f"      时间范围: {df['ts_bucket'].min()} ~ {df['ts_bucket'].max()}")
    print(f"      压力范围: {df['pressure'].min():.4f} ~ {df['pressure'].max():.4f} MPa")
    print(f"      流量范围: {df['flow_rate'].min():.2f} ~ {df['flow_rate'].max():.2f} m³/h")
    print(f"      液位范围: {df['pool_level'].min():.4f} ~ {df['pool_level'].max():.4f} m")
    
    # 反推 K_eq
    print("\n[2/5] 反推 K_eq...")
    
    # 物理常数
    P_atm = 0.101325  # MPa
    rho = 1000.0  # kg/m³
    g = 9.80665  # m/s²
    L_offset = 2.25  # m
    pipe_diameter = 0.6  # m
    
    # 计算静压头
    df['h_static'] = df['pool_level'] - L_offset  # m
    
    # 计算流速
    df['velocity'] = df['flow_rate'] / (3600 * np.pi * (pipe_diameter ** 2) / 4)  # m/s
    
    # 从压力反推损失水头
    # P_in = P_atm + ρ × g × (h_static - h_loss) / 1e6
    # h_loss = h_static - (P_in - P_atm) × 1e6 / (ρ × g)
    df['h_loss'] = df['h_static'] - (df['pressure'] - P_atm) * 1e6 / (rho * g)
    
    # 反推 K_eq
    # h_loss = K_eq × v² / (2g)
    # K_eq = h_loss × 2g / v²
    df['K_eq_calculated'] = df['h_loss'] * 2 * g / (df['velocity'] ** 2)
    
    # 过滤异常值（K_eq应该在0.1-10之间）
    df_valid = df[(df['K_eq_calculated'] > 0.1) & (df['K_eq_calculated'] < 10.0)].copy()
    
    print(f"   ✓ 有效数据: {len(df_valid)} / {len(df)} ({len(df_valid)/len(df)*100:.1f}%)")
    
    # 统计 K_eq
    print("\n[3/5] K_eq 统计分析...")
    
    k_eq_stats = df_valid['K_eq_calculated'].describe()
    print(f"\n   K_eq 统计:")
    print(f"      平均值: {k_eq_stats['mean']:.4f}")
    print(f"      中位数: {df_valid['K_eq_calculated'].median():.4f}")
    print(f"      标准差: {k_eq_stats['std']:.4f}")
    print(f"      最小值: {k_eq_stats['min']:.4f}")
    print(f"      25%分位: {k_eq_stats['25%']:.4f}")
    print(f"      50%分位: {k_eq_stats['50%']:.4f}")
    print(f"      75%分位: {k_eq_stats['75%']:.4f}")
    print(f"      最大值: {k_eq_stats['max']:.4f}")
    
    # 按设备统计
    print(f"\n   各设备 K_eq 中位数:")
    for device_id in sorted(df_valid['device_id'].unique()):
        device_data = df_valid[df_valid['device_id'] == device_id]
        median_k_eq = device_data['K_eq_calculated'].median()
        print(f"      设备{device_id}: {median_k_eq:.4f} (样本数: {len(device_data)})")
    
    # 推荐值
    recommended_k_eq = df_valid['K_eq_calculated'].median()
    print(f"\n   ✓ 推荐 K_eq: {recommended_k_eq:.4f}")
    
    # 对比理论值
    theoretical_k_eq = 0.65
    print(f"   ✓ 理论 K_eq: {theoretical_k_eq:.4f}")
    print(f"   ✓ 差异: {abs(recommended_k_eq - theoretical_k_eq):.4f} ({abs(recommended_k_eq - theoretical_k_eq) / theoretical_k_eq * 100:.1f}%)")
    
    # 决策
    print("\n[4/5] 优化决策...")
    
    if abs(recommended_k_eq - theoretical_k_eq) / theoretical_k_eq < 0.1:
        print(f"   ✓ 推荐值与理论值差异 < 10%，建议保持理论值 {theoretical_k_eq}")
        final_k_eq = theoretical_k_eq
    else:
        print(f"   ⚠️  推荐值与理论值差异 >= 10%，建议使用优化值 {recommended_k_eq:.4f}")
        final_k_eq = recommended_k_eq
    
    print(f"\n   最终 K_eq: {final_k_eq:.4f}")
    
    print("\n[5/5] 完成")
    print(f"\n   当前数据库中的 K_eq: 0.65")
    print(f"   优化后的 K_eq: {final_k_eq:.4f}")
    
    if abs(final_k_eq - 0.65) < 0.01:
        print(f"\n   ✅ 无需更新参数，当前值已是最优")
    else:
        print(f"\n   ⚠️  建议更新参数为 {final_k_eq:.4f}")
        print(f"   更新命令:")
        print(f"      UPDATE calculation_parameters")
        print(f"      SET param_value = '{final_k_eq:.4f}', updated_at = NOW(), updated_by = 'optimize_K_eq_20251119'")
        print(f"      WHERE metric_key = 'pump_inlet_pressure' AND param_name = 'K_eq' AND device_id IS NULL;")
    
    print("\n" + "=" * 100)

if __name__ == "__main__":
    main()

