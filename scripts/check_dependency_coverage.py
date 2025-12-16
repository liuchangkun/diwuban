"""
检查依赖数据的覆盖率

目的：诊断为什么 pump_hydraulic_power 和 pump_shaft_power 覆盖率低
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
    print("检查依赖数据的覆盖率")
    print("="*100)
    
    # 初始化数据库
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. 检查 pump_flow_rate 和 pump_head 的同时可用性（设备1）
            print("\n1. pump_flow_rate 和 pump_head 的同时可用性（设备1）")
            print("-"*100)
            
            cur.execute("""
                WITH flow_data AS (
                    SELECT fm.ts_bucket, fm.value as flow_rate
                    FROM fact_measurements fm
                    JOIN dim_metric_config mc ON mc.id = fm.metric_id
                    WHERE fm.station_id = 1
                      AND fm.device_id = 1
                      AND mc.metric_key = 'pump_flow_rate'
                      AND fm.ts_bucket >= '2025-10-22 08:00:00+00:00'
                      AND fm.ts_bucket < '2025-10-23 07:13:29+00:00'
                ),
                head_data AS (
                    SELECT fm.ts_bucket, fm.value as head
                    FROM fact_measurements fm
                    JOIN dim_metric_config mc ON mc.id = fm.metric_id
                    WHERE fm.station_id = 1
                      AND fm.device_id = 1
                      AND mc.metric_key = 'pump_head'
                      AND fm.ts_bucket >= '2025-10-22 08:00:00+00:00'
                      AND fm.ts_bucket < '2025-10-23 07:13:29+00:00'
                ),
                running_data AS (
                    SELECT ts_bucket, running
                    FROM mv_device_running_1s
                    WHERE station_id = 1
                      AND device_id = 1
                      AND ts_bucket >= '2025-10-22 08:00:00+00:00'
                      AND ts_bucket < '2025-10-23 07:13:29+00:00'
                )
                SELECT 
                    COUNT(DISTINCT r.ts_bucket) as total_running,
                    COUNT(DISTINCT f.ts_bucket) as has_flow,
                    COUNT(DISTINCT h.ts_bucket) as has_head,
                    COUNT(DISTINCT CASE WHEN f.ts_bucket IS NOT NULL AND h.ts_bucket IS NOT NULL THEN r.ts_bucket END) as has_both,
                    COUNT(DISTINCT CASE WHEN f.ts_bucket IS NOT NULL AND h.ts_bucket IS NOT NULL AND f.flow_rate > 0 AND h.head > 0 THEN r.ts_bucket END) as has_both_positive
                FROM running_data r
                LEFT JOIN flow_data f ON f.ts_bucket = r.ts_bucket
                LEFT JOIN head_data h ON h.ts_bucket = r.ts_bucket
                WHERE r.running = 1
            """)
            
            row = cur.fetchone()
            total_running, has_flow, has_head, has_both, has_both_positive = row
            
            print(f"运行状态记录数: {total_running:,}")
            print(f"有 flow_rate 数据: {has_flow:,} ({has_flow/total_running*100:.1f}%)")
            print(f"有 head 数据: {has_head:,} ({has_head/total_running*100:.1f}%)")
            print(f"同时有 flow 和 head: {has_both:,} ({has_both/total_running*100:.1f}%)")
            print(f"同时有且都>0: {has_both_positive:,} ({has_both_positive/total_running*100:.1f}%)")
            
            # 2. 检查 pump_active_power 的可用性（设备1）
            print("\n\n2. pump_active_power 的可用性（设备1）")
            print("-"*100)
            
            cur.execute("""
                WITH active_power_data AS (
                    SELECT fm.ts_bucket, fm.value as active_power
                    FROM fact_measurements fm
                    JOIN dim_metric_config mc ON mc.id = fm.metric_id
                    WHERE fm.station_id = 1
                      AND fm.device_id = 1
                      AND mc.metric_key = 'pump_active_power'
                      AND fm.ts_bucket >= '2025-10-22 08:00:00+00:00'
                      AND fm.ts_bucket < '2025-10-23 07:13:29+00:00'
                ),
                running_data AS (
                    SELECT ts_bucket, running
                    FROM mv_device_running_1s
                    WHERE station_id = 1
                      AND device_id = 1
                      AND ts_bucket >= '2025-10-22 08:00:00+00:00'
                      AND ts_bucket < '2025-10-23 07:13:29+00:00'
                )
                SELECT 
                    COUNT(DISTINCT r.ts_bucket) as total_running,
                    COUNT(DISTINCT p.ts_bucket) as has_active_power,
                    COUNT(DISTINCT CASE WHEN p.active_power > 0 THEN r.ts_bucket END) as has_positive_power
                FROM running_data r
                LEFT JOIN active_power_data p ON p.ts_bucket = r.ts_bucket
                WHERE r.running = 1
            """)
            
            row = cur.fetchone()
            total_running, has_active, has_positive = row
            
            print(f"运行状态记录数: {total_running:,}")
            print(f"有 active_power 数据: {has_active:,} ({has_active/total_running*100:.1f}%)")
            print(f"active_power > 0: {has_positive:,} ({has_positive/total_running*100:.1f}%)")
            
            # 3. 检查所有设备的情况
            print("\n\n3. 所有设备的依赖数据可用性")
            print("-"*100)
            
            cur.execute("""
                WITH flow_data AS (
                    SELECT fm.device_id, fm.ts_bucket, fm.value as flow_rate
                    FROM fact_measurements fm
                    JOIN dim_metric_config mc ON mc.id = fm.metric_id
                    WHERE fm.station_id = 1
                      AND fm.device_id IN (1, 2, 3, 4, 5, 6)
                      AND mc.metric_key = 'pump_flow_rate'
                      AND fm.ts_bucket >= '2025-10-22 08:00:00+00:00'
                      AND fm.ts_bucket < '2025-10-23 07:13:29+00:00'
                ),
                head_data AS (
                    SELECT fm.device_id, fm.ts_bucket, fm.value as head
                    FROM fact_measurements fm
                    JOIN dim_metric_config mc ON mc.id = fm.metric_id
                    WHERE fm.station_id = 1
                      AND fm.device_id IN (1, 2, 3, 4, 5, 6)
                      AND mc.metric_key = 'pump_head'
                      AND fm.ts_bucket >= '2025-10-22 08:00:00+00:00'
                      AND fm.ts_bucket < '2025-10-23 07:13:29+00:00'
                ),
                active_power_data AS (
                    SELECT fm.device_id, fm.ts_bucket, fm.value as active_power
                    FROM fact_measurements fm
                    JOIN dim_metric_config mc ON mc.id = fm.metric_id
                    WHERE fm.station_id = 1
                      AND fm.device_id IN (1, 2, 3, 4, 5, 6)
                      AND mc.metric_key = 'pump_active_power'
                      AND fm.ts_bucket >= '2025-10-22 08:00:00+00:00'
                      AND fm.ts_bucket < '2025-10-23 07:13:29+00:00'
                ),
                running_data AS (
                    SELECT device_id, ts_bucket, running
                    FROM mv_device_running_1s
                    WHERE station_id = 1
                      AND device_id IN (1, 2, 3, 4, 5, 6)
                      AND ts_bucket >= '2025-10-22 08:00:00+00:00'
                      AND ts_bucket < '2025-10-23 07:13:29+00:00'
                      AND running = 1
                )
                SELECT 
                    r.device_id,
                    COUNT(DISTINCT r.ts_bucket) as total_running,
                    COUNT(DISTINCT CASE WHEN f.flow_rate > 0 AND h.head > 0 THEN r.ts_bucket END) as valid_for_hydro,
                    COUNT(DISTINCT CASE WHEN p.active_power > 0 THEN r.ts_bucket END) as valid_for_shaft
                FROM running_data r
                LEFT JOIN flow_data f ON f.device_id = r.device_id AND f.ts_bucket = r.ts_bucket
                LEFT JOIN head_data h ON h.device_id = r.device_id AND h.ts_bucket = r.ts_bucket
                LEFT JOIN active_power_data p ON p.device_id = r.device_id AND p.ts_bucket = r.ts_bucket
                GROUP BY r.device_id
                ORDER BY r.device_id
            """)
            
            print(f"\n{'设备':<8} {'运行记录':<12} {'可计算P_h':<12} {'覆盖率':<10} {'可计算P_s':<12} {'覆盖率':<10}")
            print("-"*100)
            
            for row in cur.fetchall():
                device_id, total, valid_hydro, valid_shaft = row
                hydro_pct = (valid_hydro / total * 100) if total > 0 else 0
                shaft_pct = (valid_shaft / total * 100) if total > 0 else 0
                print(f"{device_id:<8} {total:<12,} {valid_hydro:<12,} {hydro_pct:<9.1f}% {valid_shaft:<12,} {shaft_pct:<9.1f}%")
    
    print("\n✅ 检查完成")


if __name__ == '__main__':
    main()

