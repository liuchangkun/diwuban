"""
诊断功率关系问题

问题：物理约束验证显示只有9.4%的数据满足 P_h < P_s < P_a
需要诊断：
1. 各个功率指标的数据分布
2. 不满足约束的具体原因
3. 是否是计算公式错误
"""

import sys
import os
from pathlib import Path

# 设置控制台编码为UTF-8（Windows兼容）
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings


def main():
    """主函数"""
    print("="*100)
    print("诊断功率关系问题")
    print("="*100)
    
    # 初始化数据库
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. 检查各功率指标的数据分布
            print("\n1. 各功率指标的数据分布（设备1样本）")
            print("-"*100)
            
            cur.execute("""
                SELECT 
                    mc.metric_key,
                    COUNT(*) as count,
                    MIN(fm.value) as min_val,
                    MAX(fm.value) as max_val,
                    AVG(fm.value) as avg_val,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY fm.value) as median_val
                FROM fact_measurements fm
                JOIN dim_metric_config mc ON mc.id = fm.metric_id
                WHERE fm.station_id = 1
                  AND fm.device_id = 1
                  AND mc.metric_key IN ('pump_active_power', 'pump_shaft_power', 'pump_hydraulic_power')
                  AND fm.ts_bucket >= '2025-10-22 08:00:00+00:00'
                  AND fm.ts_bucket < '2025-10-23 07:13:29+00:00'
                GROUP BY mc.metric_key
                ORDER BY mc.metric_key
            """)
            
            for row in cur.fetchall():
                metric_key, count, min_val, max_val, avg_val, median_val = row
                print(f"\n{metric_key}:")
                print(f"  记录数: {count:,}")
                print(f"  最小值: {min_val:.2f} kW")
                print(f"  最大值: {max_val:.2f} kW")
                print(f"  平均值: {avg_val:.2f} kW")
                print(f"  中位数: {median_val:.2f} kW")
            
            # 2. 检查同一时刻的功率值对比（设备1样本）
            print("\n\n2. 同一时刻的功率值对比（设备1，前10条记录）")
            print("-"*100)
            
            cur.execute("""
                WITH power_data AS (
                    SELECT 
                        fm.ts_bucket,
                        mc.metric_key,
                        fm.value
                    FROM fact_measurements fm
                    JOIN dim_metric_config mc ON mc.id = fm.metric_id
                    WHERE fm.station_id = 1
                      AND fm.device_id = 1
                      AND mc.metric_key IN ('pump_active_power', 'pump_shaft_power', 'pump_hydraulic_power')
                      AND fm.ts_bucket >= '2025-10-22 08:00:00+00:00'
                      AND fm.ts_bucket < '2025-10-23 07:13:29+00:00'
                )
                SELECT 
                    p_active.ts_bucket,
                    p_active.value as p_active,
                    p_shaft.value as p_shaft,
                    p_hydro.value as p_hydro,
                    CASE 
                        WHEN p_hydro.value IS NULL THEN 'P_hydro缺失'
                        WHEN p_shaft.value IS NULL THEN 'P_shaft缺失'
                        WHEN p_hydro.value >= p_shaft.value THEN 'P_h >= P_s'
                        WHEN p_shaft.value >= p_active.value THEN 'P_s >= P_a'
                        ELSE '正常'
                    END as status
                FROM power_data p_active
                LEFT JOIN power_data p_shaft 
                    ON p_shaft.ts_bucket = p_active.ts_bucket 
                    AND p_shaft.metric_key = 'pump_shaft_power'
                LEFT JOIN power_data p_hydro 
                    ON p_hydro.ts_bucket = p_active.ts_bucket 
                    AND p_hydro.metric_key = 'pump_hydraulic_power'
                WHERE p_active.metric_key = 'pump_active_power'
                ORDER BY p_active.ts_bucket
                LIMIT 10
            """)
            
            print(f"\n{'时间':<25} {'P_active':<12} {'P_shaft':<12} {'P_hydro':<12} {'状态':<15}")
            print("-"*100)
            
            for row in cur.fetchall():
                ts, p_a, p_s, p_h, status = row
                p_a_str = f"{p_a:.2f}" if p_a else "N/A"
                p_s_str = f"{p_s:.2f}" if p_s else "N/A"
                p_h_str = f"{p_h:.2f}" if p_h else "N/A"
                print(f"{str(ts):<25} {p_a_str:<12} {p_s_str:<12} {p_h_str:<12} {status:<15}")
            
            # 3. 统计各种异常情况的数量
            print("\n\n3. 异常情况统计（所有设备）")
            print("-"*100)
            
            cur.execute("""
                WITH power_data AS (
                    SELECT 
                        fm.ts_bucket,
                        fm.device_id,
                        mc.metric_key,
                        fm.value
                    FROM fact_measurements fm
                    JOIN dim_metric_config mc ON mc.id = fm.metric_id
                    WHERE fm.station_id = 1
                      AND fm.device_id IN (1, 2, 3, 4, 5, 6)
                      AND mc.metric_key IN ('pump_active_power', 'pump_shaft_power', 'pump_hydraulic_power')
                      AND fm.ts_bucket >= '2025-10-22 08:00:00+00:00'
                      AND fm.ts_bucket < '2025-10-23 07:13:29+00:00'
                ),
                combined AS (
                    SELECT 
                        p_active.device_id,
                        p_active.ts_bucket,
                        p_active.value as p_active,
                        p_shaft.value as p_shaft,
                        p_hydro.value as p_hydro
                    FROM power_data p_active
                    LEFT JOIN power_data p_shaft 
                        ON p_shaft.ts_bucket = p_active.ts_bucket 
                        AND p_shaft.device_id = p_active.device_id
                        AND p_shaft.metric_key = 'pump_shaft_power'
                    LEFT JOIN power_data p_hydro 
                        ON p_hydro.ts_bucket = p_active.ts_bucket 
                        AND p_hydro.device_id = p_active.device_id
                        AND p_hydro.metric_key = 'pump_hydraulic_power'
                    WHERE p_active.metric_key = 'pump_active_power'
                )
                SELECT 
                    device_id,
                    COUNT(*) as total,
                    SUM(CASE WHEN p_shaft IS NULL THEN 1 ELSE 0 END) as shaft_missing,
                    SUM(CASE WHEN p_hydro IS NULL THEN 1 ELSE 0 END) as hydro_missing,
                    SUM(CASE WHEN p_shaft IS NOT NULL AND p_hydro IS NOT NULL AND p_hydro >= p_shaft THEN 1 ELSE 0 END) as h_ge_s,
                    SUM(CASE WHEN p_shaft IS NOT NULL AND p_shaft >= p_active THEN 1 ELSE 0 END) as s_ge_a,
                    SUM(CASE WHEN p_shaft IS NOT NULL AND p_hydro IS NOT NULL AND p_hydro < p_shaft AND p_shaft < p_active THEN 1 ELSE 0 END) as valid
                FROM combined
                GROUP BY device_id
                ORDER BY device_id
            """)
            
            print(f"\n{'设备':<8} {'总记录':<10} {'P_s缺失':<10} {'P_h缺失':<10} {'P_h>=P_s':<10} {'P_s>=P_a':<10} {'正常':<10}")
            print("-"*100)
            
            for row in cur.fetchall():
                device_id, total, shaft_miss, hydro_miss, h_ge_s, s_ge_a, valid = row
                print(f"{device_id:<8} {total:<10} {shaft_miss:<10} {hydro_miss:<10} {h_ge_s:<10} {s_ge_a:<10} {valid:<10}")
    
    print("\n✅ 诊断完成")


if __name__ == '__main__':
    main()

