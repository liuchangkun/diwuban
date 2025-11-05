#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析测试环境数据情况
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader import load_settings


def analyze_test_data():
    """分析测试环境数据"""
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            print("=" * 80)
            print("📊 测试环境数据分析")
            print("=" * 80)
            
            # 1. 查询数据时间范围
            print("\n【1. 数据时间范围】")
            cur.execute("""
                SELECT 
                    MIN(ts_bucket) as min_time,
                    MAX(ts_bucket) as max_time,
                    COUNT(DISTINCT ts_bucket) as time_points,
                    COUNT(DISTINCT device_id) as device_count
                FROM fact_measurements
            """)
            row = cur.fetchone()
            if row and row[0]:
                print(f"  最早时间: {row[0]}")
                print(f"  最晚时间: {row[1]}")
                print(f"  时间点数: {row[2]:,}")
                print(f"  设备数量: {row[3]}")
                
                # 计算建议的测试窗口
                min_time = row[0]
                max_time = row[1]
                
                # 建议使用最近的2小时数据
                test_end = max_time
                test_start = max_time - timedelta(hours=2)
                
                print(f"\n  建议测试窗口:")
                print(f"  开始时间: {test_start}")
                print(f"  结束时间: {test_end}")
            else:
                print("  ⚠️  未找到数据")
                return None, None
            
            # 2. 查询泵站和设备信息
            print("\n【2. 泵站和设备信息】")
            cur.execute("""
                SELECT
                    ds.id as station_id,
                    ds.name as station_name,
                    COUNT(DISTINCT dd.id) as device_count,
                    STRING_AGG(DISTINCT dd.type, ', ') as device_types
                FROM dim_stations ds
                LEFT JOIN dim_devices dd ON dd.station_id = ds.id
                GROUP BY ds.id, ds.name
                ORDER BY ds.id
            """)
            rows = cur.fetchall()
            for row in rows:
                print(f"  泵站 {row[0]}: {row[1]} | {row[2]} 个设备 | 类型: {row[3]}")
            
            # 3. 查询指标覆盖情况
            print("\n【3. 指标覆盖情况】")
            cur.execute("""
                SELECT
                    dmc.metric_key,
                    COUNT(DISTINCT fm.device_id) as device_count,
                    COUNT(*) as data_points,
                    COUNT(CASE WHEN fm.source_hint LIKE 'calculation:%%' THEN 1 END) as calculated_points,
                    COUNT(CASE WHEN fm.source_hint NOT LIKE 'calculation:%%' THEN 1 END) as imported_points
                FROM fact_measurements fm
                JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
                WHERE fm.ts_bucket >= %s AND fm.ts_bucket < %s
                GROUP BY dmc.metric_key
                ORDER BY dmc.metric_key
            """, (test_start, test_end))
            rows = cur.fetchall()
            
            print(f"\n  时间窗口: {test_start} ~ {test_end}")
            print(f"  {'指标名称':40s} | {'设备数':>6s} | {'总数据点':>10s} | {'计算点':>10s} | {'导入点':>10s}")
            print("  " + "-" * 90)
            
            total_points = 0
            total_calculated = 0
            total_imported = 0
            
            for row in rows:
                metric_key, device_count, data_points, calculated, imported = row
                total_points += data_points
                total_calculated += calculated
                total_imported += imported
                print(f"  {metric_key:40s} | {device_count:6d} | {data_points:10,d} | {calculated:10,d} | {imported:10,d}")
            
            print("  " + "-" * 90)
            print(f"  {'总计':40s} | {'':6s} | {total_points:10,d} | {total_calculated:10,d} | {total_imported:10,d}")
            
            # 4. 查询历史计算失败记录
            print("\n【4. 历史计算失败记录】")
            cur.execute("""
                SELECT 
                    metric_key,
                    error_type,
                    COUNT(*) as failure_count
                FROM calculation_failures_log
                WHERE created_at >= NOW() - INTERVAL '7 days'
                GROUP BY metric_key, error_type
                ORDER BY failure_count DESC
                LIMIT 10
            """)
            rows = cur.fetchall()
            
            if rows:
                print(f"  {'指标名称':40s} | {'错误类型':20s} | {'失败次数':>10s}")
                print("  " + "-" * 80)
                for row in rows:
                    print(f"  {row[0]:40s} | {row[1]:20s} | {row[2]:10,d}")
            else:
                print("  ℹ️  无历史失败记录")
            
            # 5. 查询运行状态数据
            print("\n【5. 运行状态数据】")
            cur.execute("""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(CASE WHEN running = 1 THEN 1 END) as running_records,
                    COUNT(DISTINCT device_id) as device_count
                FROM mv_device_running_1s
                WHERE ts_bucket >= %s AND ts_bucket < %s
            """, (test_start, test_end))
            row = cur.fetchone()
            if row:
                total, running, devices = row
                running_pct = (running / total * 100) if total > 0 else 0
                print(f"  总记录数: {total:,}")
                print(f"  运行记录: {running:,} ({running_pct:.1f}%)")
                print(f"  设备数量: {devices}")
            
            return test_start, test_end


if __name__ == "__main__":
    try:
        # 初始化数据库连接
        settings = load_settings(Path("configs"))
        init_database(settings)
        
        test_start, test_end = analyze_test_data()
        
        if test_start and test_end:
            print("\n" + "=" * 80)
            print("✅ 数据分析完成")
            print("=" * 80)
            print(f"\n建议的测试命令:")
            print(f"python -m app.cli.main missing-metrics:compute \\")
            print(f"  --start '{test_start.strftime('%Y-%m-%d %H:%M:%S')}+08' \\")
            print(f"  --end '{test_end.strftime('%Y-%m-%d %H:%M:%S')}+08' \\")
            print(f"  --window-hours 1 \\")
            print(f"  --filter-running \\")
            print(f"  --filter-quality \\")
            print(f"  --dry-run")
            
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

