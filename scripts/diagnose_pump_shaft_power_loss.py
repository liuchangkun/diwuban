"""
诊断 pump_shaft_power 从25,632条到9,348条的数据损失原因
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone

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
    print("诊断 pump_shaft_power 数据损失原因")
    print("="*100)
    
    # 初始化数据库
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    # 时间范围
    start_time = datetime(2025, 10, 22, 8, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2025, 10, 23, 7, 13, 29, tzinfo=timezone.utc)
    
    print(f"\n时间范围: {start_time} ~ {end_time}")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 分析设备1的数据
            device_id = 1
            
            print(f"\n{'='*100}")
            print(f"设备 {device_id} 的详细分析")
            print(f"{'='*100}")
            
            # 1. 获取 pump_active_power > 0 的数据
            print("\n1. pump_active_power > 0 的数据分布：")
            print("-"*100)
            
            cur.execute("""
                SELECT 
                    COUNT(*) as total_count,
                    MIN(fm.value) as min_value,
                    MAX(fm.value) as max_value,
                    AVG(fm.value) as avg_value,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY fm.value) as median_value
                FROM mv_device_running_1s r
                JOIN fact_measurements fm ON fm.ts_bucket = r.ts_bucket 
                    AND fm.device_id = r.device_id AND fm.station_id = r.station_id
                JOIN dim_metric_config mc ON mc.id = fm.metric_id
                WHERE r.station_id = 1 AND r.device_id = %s
                  AND r.ts_bucket >= %s AND r.ts_bucket < %s
                  AND r.running = 1
                  AND mc.metric_key = 'pump_active_power'
                  AND fm.value > 0
            """, (device_id, start_time, end_time))
            
            row = cur.fetchone()
            print(f"记录数: {row[0]:,}")
            print(f"最小值: {row[1]:.2f} kW")
            print(f"最大值: {row[2]:.2f} kW")
            print(f"平均值: {row[3]:.2f} kW")
            print(f"中位数: {row[4]:.2f} kW")
            
            # 2. 获取实际写入的 pump_shaft_power 数据
            print("\n2. 实际写入的 pump_shaft_power 数据分布：")
            print("-"*100)
            
            cur.execute("""
                SELECT 
                    COUNT(*) as total_count,
                    MIN(fm.value) as min_value,
                    MAX(fm.value) as max_value,
                    AVG(fm.value) as avg_value,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY fm.value) as median_value
                FROM fact_measurements fm
                JOIN dim_metric_config mc ON mc.id = fm.metric_id
                WHERE fm.station_id = 1 AND fm.device_id = %s
                  AND mc.metric_key = 'pump_shaft_power'
                  AND fm.ts_bucket >= %s AND fm.ts_bucket < %s
            """, (device_id, start_time, end_time))
            
            row = cur.fetchone()
            print(f"记录数: {row[0]:,}")
            print(f"最小值: {row[1]:.2f} kW")
            print(f"最大值: {row[2]:.2f} kW")
            print(f"平均值: {row[3]:.2f} kW")
            print(f"中位数: {row[4]:.2f} kW")
            
            # 3. 对比 P_shaft 和 P_active 的关系
            print("\n3. P_shaft 和 P_active 的关系验证：")
            print("-"*100)
            
            cur.execute("""
                WITH active_power AS (
                    SELECT fm.ts_bucket, fm.value as p_active
                    FROM mv_device_running_1s r
                    JOIN fact_measurements fm ON fm.ts_bucket = r.ts_bucket 
                        AND fm.device_id = r.device_id AND fm.station_id = r.station_id
                    JOIN dim_metric_config mc ON mc.id = fm.metric_id
                    WHERE r.station_id = 1 AND r.device_id = %s
                      AND r.ts_bucket >= %s AND r.ts_bucket < %s
                      AND r.running = 1
                      AND mc.metric_key = 'pump_active_power'
                      AND fm.value > 0
                ),
                shaft_power AS (
                    SELECT fm.ts_bucket, fm.value as p_shaft
                    FROM fact_measurements fm
                    JOIN dim_metric_config mc ON mc.id = fm.metric_id
                    WHERE fm.station_id = 1 AND fm.device_id = %s
                      AND mc.metric_key = 'pump_shaft_power'
                      AND fm.ts_bucket >= %s AND fm.ts_bucket < %s
                )
                SELECT 
                    COUNT(*) as total_count,
                    COUNT(CASE WHEN s.p_shaft >= a.p_active THEN 1 END) as violation_count,
                    AVG(s.p_shaft / a.p_active) as avg_ratio,
                    MIN(s.p_shaft / a.p_active) as min_ratio,
                    MAX(s.p_shaft / a.p_active) as max_ratio
                FROM active_power a
                LEFT JOIN shaft_power s ON s.ts_bucket = a.ts_bucket
                WHERE s.p_shaft IS NOT NULL
            """, (device_id, start_time, end_time, device_id, start_time, end_time))
            
            row = cur.fetchone()
            print(f"有效配对记录数: {row[0]:,}")
            print(f"违反约束记录数 (P_shaft >= P_active): {row[1]:,}")
            print(f"平均比率 (P_shaft / P_active): {row[2]:.4f}")
            print(f"最小比率: {row[3]:.4f}")
            print(f"最大比率: {row[4]:.4f}")
            
            # 4. 分析缺失的记录
            print("\n4. 缺失记录分析（有 P_active 但没有 P_shaft）：")
            print("-"*100)
            
            cur.execute("""
                WITH active_power AS (
                    SELECT fm.ts_bucket, fm.value as p_active
                    FROM mv_device_running_1s r
                    JOIN fact_measurements fm ON fm.ts_bucket = r.ts_bucket 
                        AND fm.device_id = r.device_id AND fm.station_id = r.station_id
                    JOIN dim_metric_config mc ON mc.id = fm.metric_id
                    WHERE r.station_id = 1 AND r.device_id = %s
                      AND r.ts_bucket >= %s AND r.ts_bucket < %s
                      AND r.running = 1
                      AND mc.metric_key = 'pump_active_power'
                      AND fm.value > 0
                ),
                shaft_power AS (
                    SELECT fm.ts_bucket, fm.value as p_shaft
                    FROM fact_measurements fm
                    JOIN dim_metric_config mc ON mc.id = fm.metric_id
                    WHERE fm.station_id = 1 AND fm.device_id = %s
                      AND mc.metric_key = 'pump_shaft_power'
                      AND fm.ts_bucket >= %s AND fm.ts_bucket < %s
                )
                SELECT 
                    COUNT(*) as missing_count,
                    MIN(a.p_active) as min_p_active,
                    MAX(a.p_active) as max_p_active,
                    AVG(a.p_active) as avg_p_active
                FROM active_power a
                LEFT JOIN shaft_power s ON s.ts_bucket = a.ts_bucket
                WHERE s.p_shaft IS NULL
            """, (device_id, start_time, end_time, device_id, start_time, end_time))
            
            row = cur.fetchone()
            print(f"缺失记录数: {row[0]:,}")
            if row[0] > 0:
                print(f"缺失记录的 P_active 范围: {row[1]:.2f} ~ {row[2]:.2f} kW")
                print(f"缺失记录的 P_active 平均值: {row[3]:.2f} kW")
    
    print("\n✅ 诊断完成")


if __name__ == '__main__':
    main()

