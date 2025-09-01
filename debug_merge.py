#!/usr/bin/env python3
"""调试合并SQL问题"""

import psycopg
from datetime import datetime

def debug_merge():
    try:
        conn = psycopg.connect('host=localhost dbname=pump_station_optimization user=postgres')
        cur = conn.cursor()

        # 检查维表数据
        print("=== 检查维表数据 ===")
        cur.execute("SELECT id, name FROM dim_stations")
        stations = cur.fetchall()
        print(f"泵站数量: {len(stations)}")
        for station in stations[:3]:
            print(f"  - {station}")

        cur.execute("SELECT id, station_id, name FROM dim_devices LIMIT 5")
        devices = cur.fetchall()
        print(f"\n设备数量: {len(devices)}")
        for device in devices[:3]:
            print(f"  - {device}")

        cur.execute("SELECT id, metric_key FROM dim_metric_config LIMIT 5")
        metrics = cur.fetchall()
        print(f"\n指标数量: {len(metrics)}")
        for metric in metrics[:3]:
            print(f"  - {metric}")

        # 测试解析逻辑
        print("\n=== 测试时间解析 ===")
        test_sql = """
        SELECT 
            sr."DataTime",
            to_timestamp(rtrim(replace(split_part(sr."DataTime", '.', 1), 'T', ' '), 'Z'), 'YYYY-MM-DD HH24:MI:SS') as parsed_utc,
            (to_timestamp(rtrim(replace(split_part(sr."DataTime", '.', 1), 'T', ' '), 'Z'), 'YYYY-MM-DD HH24:MI:SS') AT TIME ZONE 'Asia/Shanghai') AS ts_utc
        FROM staging_raw sr 
        LIMIT 3
        """
        cur.execute(test_sql)
        time_samples = cur.fetchall()
        for sample in time_samples:
            print(f"  原始: {sample[0]} -> 解析: {sample[1]} -> UTC: {sample[2]}")

        # 测试JOIN
        print("\n=== 测试JOIN逻辑 ===")
        join_sql = """
        SELECT 
            sr.station_name,
            sr.device_name,
            sr.metric_key,
            ds.id AS station_id,
            dd.id AS device_id,
            dmc.id AS metric_id
        FROM staging_raw sr
        LEFT JOIN dim_stations ds ON ds.name = sr.station_name
        LEFT JOIN dim_devices dd ON dd.station_id = ds.id AND dd.name = sr.device_name
        LEFT JOIN dim_metric_config dmc ON dmc.metric_key = sr.metric_key
        LIMIT 5
        """
        cur.execute(join_sql)
        join_samples = cur.fetchall()
        for sample in join_samples:
            print(f"  {sample}")
            
        # 检查有多少行能成功JOIN
        count_sql = """
        SELECT 
            COUNT(*) as total,
            COUNT(ds.id) as station_matched,
            COUNT(dd.id) as device_matched,
            COUNT(dmc.id) as metric_matched
        FROM staging_raw sr
        LEFT JOIN dim_stations ds ON ds.name = sr.station_name
        LEFT JOIN dim_devices dd ON dd.station_id = ds.id AND dd.name = sr.device_name
        LEFT JOIN dim_metric_config dmc ON dmc.metric_key = sr.metric_key
        """
        cur.execute(count_sql)
        counts = cur.fetchone()
        print(f"\n=== JOIN匹配统计 ===")
        print(f"总行数: {counts[0]}")
        print(f"泵站匹配: {counts[1]}")
        print(f"设备匹配: {counts[2]}")
        print(f"指标匹配: {counts[3]}")

        conn.close()
        
    except Exception as e:
        print(f"调试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_merge()