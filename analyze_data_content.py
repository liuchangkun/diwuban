#!/usr/bin/env python3
"""
查看数据库的具体数据内容
"""

import psycopg
from datetime import datetime

def analyze_data_content():
    conn_params = {
        "host": "localhost",
        "dbname": "pump_station_optimization", 
        "user": "postgres",
    }
    
    with psycopg.connect(**conn_params) as conn:
        with conn.cursor() as cur:
            print("=== 具体数据内容分析 ===\n")
            
            # 查看泵站信息
            print("=== 泵站信息 ===")
            cur.execute("SELECT id, name, extra FROM dim_stations ORDER BY id")
            stations = cur.fetchall()
            for station in stations:
                sid, name, extra = station
                print(f"ID: {sid}, 名称: {name}")
                if extra:
                    print(f"  额外信息: {extra}")
                print()
            
            # 查看设备信息
            print("=== 设备信息 ===")
            cur.execute("""
                SELECT d.id, s.name as station_name, d.name, d.type, d.pump_type, d.extra 
                FROM dim_devices d 
                JOIN dim_stations s ON d.station_id = s.id 
                ORDER BY s.id, d.id
            """)
            devices = cur.fetchall()
            
            current_station = None
            for device in devices:
                did, station_name, device_name, device_type, pump_type, extra = device
                if station_name != current_station:
                    print(f"\n【{station_name}】")
                    current_station = station_name
                
                print(f"  设备ID: {did}")
                print(f"  设备名: {device_name}")
                print(f"  类型: {device_type}")
                if pump_type:
                    print(f"  泵类型: {pump_type}")
                if extra:
                    print(f"  额外信息: {extra}")
                print()
            
            # 查看指标配置
            print("=== 指标配置 ===")
            cur.execute("""
                SELECT metric_key, unit, unit_display, value_type, valid_min, valid_max 
                FROM dim_metric_config 
                ORDER BY id
            """)
            metrics = cur.fetchall()
            
            for metric in metrics:
                key, unit, unit_display, value_type, vmin, vmax = metric
                print(f"指标: {key}")
                print(f"  单位: {unit} ({unit_display if unit_display else '无显示名'})")
                if value_type:
                    print(f"  类型: {value_type}")
                if vmin is not None or vmax is not None:
                    print(f"  范围: {vmin} ~ {vmax}")
                print()
            
            # 查看最近的数据采样
            print("=== 最近数据采样（最新10条记录） ===")
            cur.execute("""
                SELECT 
                    s.name as station_name,
                    d.name as device_name, 
                    m.metric_key,
                    f.ts_bucket,
                    f.value,
                    f.source_hint,
                    f.inserted_at
                FROM fact_measurements f
                JOIN dim_stations s ON f.station_id = s.id
                JOIN dim_devices d ON f.device_id = d.id  
                JOIN dim_metric_config m ON f.metric_id = m.id
                ORDER BY f.inserted_at DESC 
                LIMIT 10
            """)
            
            recent_data = cur.fetchall()
            for row in recent_data:
                station, device, metric, ts_bucket, value, source, inserted = row
                print(f"{station} > {device} > {metric}")
                print(f"  时间: {ts_bucket}")
                print(f"  数值: {value}")
                print(f"  来源: {source}")
                print(f"  插入时间: {inserted}")
                print()
            
            # 数据统计分析
            print("=== 数据统计分析 ===")
            
            # 按站点统计
            cur.execute("""
                SELECT 
                    s.name,
                    COUNT(*) as record_count,
                    MIN(f.ts_bucket) as earliest_time,
                    MAX(f.ts_bucket) as latest_time
                FROM fact_measurements f
                JOIN dim_stations s ON f.station_id = s.id
                GROUP BY s.id, s.name
                ORDER BY s.id
            """)
            
            station_stats = cur.fetchall()
            print("按泵站统计:")
            for stat in station_stats:
                name, count, earliest, latest = stat
                print(f"  {name}: {count:,} 条记录")
                print(f"    时间范围: {earliest} ~ {latest}")
                print()
            
            # 按指标统计
            cur.execute("""
                SELECT 
                    m.metric_key,
                    COUNT(*) as record_count,
                    AVG(f.value::float) as avg_value,
                    MIN(f.value) as min_value,
                    MAX(f.value) as max_value
                FROM fact_measurements f
                JOIN dim_metric_config m ON f.metric_id = m.id
                GROUP BY m.id, m.metric_key
                ORDER BY record_count DESC
            """)
            
            metric_stats = cur.fetchall()
            print("按指标统计（记录数排序）:")
            for stat in metric_stats:
                metric, count, avg_val, min_val, max_val = stat
                print(f"  {metric}: {count:,} 条记录")
                if avg_val is not None:
                    print(f"    平均值: {avg_val:.2f}, 范围: {min_val} ~ {max_val}")
                print()
            
            # 检查数据质量
            print("=== 数据质量检查 ===")
            
            # 时间对齐检查
            cur.execute("""
                SELECT COUNT(*) as misaligned_count
                FROM fact_measurements 
                WHERE date_trunc('second', ts_bucket) != ts_bucket
            """)
            misaligned = cur.fetchone()[0]
            print(f"时间未对齐记录数: {misaligned}")
            
            # 重复数据检查  
            cur.execute("""
                SELECT COUNT(*) as duplicate_count
                FROM (
                    SELECT station_id, device_id, metric_id, ts_bucket, COUNT(*)
                    FROM fact_measurements 
                    GROUP BY station_id, device_id, metric_id, ts_bucket
                    HAVING COUNT(*) > 1
                ) duplicates
            """)
            duplicates = cur.fetchone()[0]
            print(f"重复记录组数: {duplicates}")
            
            # 空值检查
            cur.execute("""
                SELECT 
                    COUNT(CASE WHEN value IS NULL THEN 1 END) as null_values,
                    COUNT(CASE WHEN source_hint IS NULL THEN 1 END) as null_source_hints
                FROM fact_measurements
            """)
            null_stats = cur.fetchone()
            null_values, null_hints = null_stats
            print(f"空值记录: value={null_values}, source_hint={null_hints}")

if __name__ == "__main__":
    analyze_data_content()