#!/usr/bin/env python3
"""手动执行合并SQL测试"""

import psycopg
from datetime import datetime, timezone

def manual_merge():
    try:
        conn = psycopg.connect('host=localhost dbname=pump_station_optimization user=postgres')
        
        # 时间窗口
        start_utc = datetime(2025, 2, 28, 2, 0, 0, tzinfo=timezone.utc)
        end_utc = datetime(2025, 2, 28, 4, 0, 0, tzinfo=timezone.utc)
        
        print(f"时间窗口: {start_utc} 到 {end_utc}")
        
        # 测试parsed CTE
        parsed_sql = """
        WITH parsed AS (
          SELECT
            ds.id AS station_id,
            dd.id AS device_id,
            dmc.id AS metric_id,
            -- 站点 tz 优先，缺失用默认 tz
            (to_timestamp(rtrim(replace(split_part(sr."DataTime", '.', 1), 'T', ' '), 'Z'), 'YYYY-MM-DD HH24:MI:SS') AT TIME ZONE COALESCE(ds.extra->>'tz', %s)) AS ts_utc,
            sr."DataValue"::numeric AS val,
            sr.source_hint
          FROM public.staging_raw sr
          JOIN public.dim_stations ds ON ds.name = sr.station_name
          JOIN public.dim_devices dd ON dd.station_id = ds.id AND dd.name = sr.device_name
          JOIN public.dim_metric_config dmc ON dmc.metric_key = sr.metric_key
        )
        SELECT COUNT(*), MIN(ts_utc), MAX(ts_utc) FROM parsed
        """
        
        cur = conn.cursor()
        cur.execute(parsed_sql, ('Asia/Shanghai',))
        parsed_result = cur.fetchone()
        print(f"解析结果: {parsed_result[0]} 行, 时间范围: {parsed_result[1]} 到 {parsed_result[2]}")
        
        # 测试dedup CTE
        dedup_sql = """
        WITH parsed AS (
          SELECT
            ds.id AS station_id,
            dd.id AS device_id,
            dmc.id AS metric_id,
            (to_timestamp(rtrim(replace(split_part(sr."DataTime", '.', 1), 'T', ' '), 'Z'), 'YYYY-MM-DD HH24:MI:SS') AT TIME ZONE COALESCE(ds.extra->>'tz', %s)) AS ts_utc,
            sr."DataValue"::numeric AS val,
            sr.source_hint
          FROM public.staging_raw sr
          JOIN public.dim_stations ds ON ds.name = sr.station_name
          JOIN public.dim_devices dd ON dd.station_id = ds.id AND dd.name = sr.device_name
          JOIN public.dim_metric_config dmc ON dmc.metric_key = sr.metric_key
        ), dedup AS (
          SELECT *,
                 date_trunc('second', ts_utc) AS ts_bucket,
                 row_number() OVER (
                   PARTITION BY station_id, device_id, metric_id, date_trunc('second', ts_utc)
                   ORDER BY ts_utc DESC
                 ) AS rn
          FROM parsed
        )
        SELECT 
            COUNT(*) as total_rows,
            COUNT(*) FILTER (WHERE rn = 1) as unique_rows,
            COUNT(*) FILTER (WHERE ts_bucket >= %s AND ts_bucket < %s) as in_window,
            COUNT(*) FILTER (WHERE rn = 1 AND ts_bucket >= %s AND ts_bucket < %s) as unique_in_window
        FROM dedup
        """
        
        cur.execute(dedup_sql, ('Asia/Shanghai', start_utc, end_utc, start_utc, end_utc))
        dedup_result = cur.fetchone()
        print(f"去重结果: 总行数={dedup_result[0]}, 唯一行数={dedup_result[1]}, 窗口内={dedup_result[2]}, 窗口内唯一={dedup_result[3]}")
        
        # 如果有数据在窗口内，尝试实际插入
        if dedup_result[3] > 0:
            print("\n有数据在窗口内，尝试实际插入...")
            
            # 实际的合并SQL
            merge_sql = """
            WITH parsed AS (
              SELECT
                ds.id AS station_id,
                dd.id AS device_id,
                dmc.id AS metric_id,
                (to_timestamp(rtrim(replace(split_part(sr."DataTime", '.', 1), 'T', ' '), 'Z'), 'YYYY-MM-DD HH24:MI:SS') AT TIME ZONE COALESCE(ds.extra->>'tz', %s)) AS ts_utc,
                sr."DataValue"::numeric AS val,
                sr.source_hint
              FROM public.staging_raw sr
              JOIN public.dim_stations ds ON ds.name = sr.station_name
              JOIN public.dim_devices dd ON dd.station_id = ds.id AND dd.name = sr.device_name
              JOIN public.dim_metric_config dmc ON dmc.metric_key = sr.metric_key
            ), dedup AS (
              SELECT *,
                     date_trunc('second', ts_utc) AS ts_bucket,
                     row_number() OVER (
                       PARTITION BY station_id, device_id, metric_id, date_trunc('second', ts_utc)
                       ORDER BY ts_utc DESC
                     ) AS rn
              FROM parsed
            )
            INSERT INTO public.fact_measurements(station_id, device_id, metric_id, ts_raw, ts_bucket, value, source_hint)
            SELECT station_id, device_id, metric_id, ts_utc, ts_bucket, val, source_hint
            FROM dedup
            WHERE rn = 1 AND ts_bucket >= %s AND ts_bucket < %s
            ON CONFLICT (station_id, device_id, metric_id, ts_bucket)
            DO UPDATE SET value = EXCLUDED.value, source_hint = EXCLUDED.source_hint, ts_raw = EXCLUDED.ts_raw
            """
            
            cur.execute(merge_sql, ('Asia/Shanghai', start_utc, end_utc))
            affected = cur.rowcount
            conn.commit()
            print(f"插入/更新了 {affected} 行")
            
            # 验证插入结果
            cur.execute("SELECT COUNT(*) FROM fact_measurements")
            fact_count = cur.fetchone()[0]
            print(f"fact_measurements 表现在有 {fact_count} 行")
            
        else:
            print("没有数据在指定的时间窗口内")

        conn.close()
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    manual_merge()