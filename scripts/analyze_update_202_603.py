#!/usr/bin/env python3
"""
update_202 和 update_603 性能瓶颈分析脚本

用途：
1. 分析 mv_presence_1s_any 视图的执行计划
2. 分析 t_miss_spans 构建的执行计划
3. 分析 BETWEEN 范围连接的执行计划
4. 统计实际数据量

使用方法：
    python scripts/analyze_update_202_603.py --start "2025-10-22 16:00:00" --end "2025-10-22 18:00:00"
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime
import re

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config.loader_new import load_settings
from app.adapters.db import init_database, get_connection


def analyze_mv_presence_view(conn_str: str, start: str, end: str):
    """分析 mv_presence_1s_any 视图的执行计划"""
    print("\n" + "="*80)
    print("1. mv_presence_1s_any 视图执行计划分析")
    print("="*80)
    
    sql = """
    EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
    SELECT pr.station_id, pr.device_id, pr.metric_id, pr.ts_bucket, pr.present
    FROM public.mv_presence_1s_any pr
    WHERE pr.ts_bucket >= %s::timestamptz 
      AND pr.ts_bucket < %s::timestamptz
    LIMIT 1000;
    """
    
    try:
        import psycopg
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (start, end))
                plan = cur.fetchall()
                
                print("\n执行计划：")
                print("-"*80)
                for row in plan:
                    print(row[0])
                
                # 分析执行计划
                plan_text = '\n'.join([row[0] for row in plan])
                
                print("\n关键信息提取：")
                print("-"*80)
                
                # 检查扫描类型
                if 'Seq Scan' in plan_text:
                    print("⚠️ 使用了顺序扫描")
                elif 'Index Scan' in plan_text or 'Index Only Scan' in plan_text:
                    print("✅ 使用了索引扫描")
                
                # 提取执行时间
                time_match = re.search(r'Execution Time: ([\d.]+) ms', plan_text)
                if time_match:
                    exec_time = float(time_match.group(1))
                    print(f"⏱️ 执行时间: {exec_time:.2f} ms ({exec_time/1000:.2f} 秒)")
                
                # 提取行数
                rows_match = re.search(r'rows=(\d+)', plan_text)
                if rows_match:
                    rows = int(rows_match.group(1))
                    print(f"📊 预估行数: {rows:,}")
                
                return True
                
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def analyze_miss_spans_construction(conn_str: str, start: str, end: str):
    """分析 t_miss_spans 构建的执行计划"""
    print("\n" + "="*80)
    print("2. t_miss_spans 构建执行计划分析")
    print("="*80)
    
    # 分步执行SQL
    setup_sqls = [
        "DROP TABLE IF EXISTS temp_fwin",
        """
        CREATE TEMP TABLE temp_fwin AS
        SELECT id, station_id, device_id, metric_id, ts_bucket, value, 0 as qs
        FROM public.fact_measurements
        WHERE ts_bucket >= %s::timestamptz 
          AND ts_bucket < %s::timestamptz
        LIMIT 10000
        """,
        "CREATE INDEX ON temp_fwin(station_id, device_id, metric_id, ts_bucket)",
        "DROP TABLE IF EXISTS temp_t_pr_miss",
        """
        CREATE TEMP TABLE temp_t_pr_miss AS
        SELECT f.station_id, f.device_id, f.metric_id, f.ts_bucket
        FROM temp_fwin f
        JOIN public.dim_metric_config mc ON mc.id=f.metric_id
        LEFT JOIN public.mv_presence_1s_any pr
          ON pr.station_id=f.station_id AND pr.device_id=f.device_id 
         AND pr.metric_id=f.metric_id AND pr.ts_bucket=f.ts_bucket
        WHERE f.qs=0
          AND mc.metric_key NOT IN ('device_running','device_phase')
          AND (pr.present IS NULL OR pr.present=0)
        """,
        "CREATE INDEX ON temp_t_pr_miss(station_id, device_id, metric_id, ts_bucket)"
    ]
    
    analyze_sql = """
    EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
    WITH x AS (
      SELECT station_id, device_id, metric_id, ts_bucket,
             ts_bucket - (row_number() OVER (PARTITION BY station_id, device_id, metric_id ORDER BY ts_bucket))*interval '1 second' AS grp
      FROM temp_t_pr_miss
    )
    SELECT station_id, device_id, metric_id,
           MIN(ts_bucket) AS gap_start_ts,
           MAX(ts_bucket) AS gap_end_ts,
           EXTRACT(EPOCH FROM (MAX(ts_bucket) - MIN(ts_bucket)))::int + 1 AS gap_len_sec
    FROM x
    GROUP BY station_id, device_id, metric_id, grp;
    """
    
    try:
        import psycopg
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                # 创建临时表
                print("\n准备临时表...")
                for i, sql in enumerate(setup_sqls):
                    if '%s' in sql:
                        cur.execute(sql, (start, end))
                    else:
                        cur.execute(sql)
                
                # 执行分析
                print("\n执行计划：")
                print("-"*80)
                cur.execute(analyze_sql)
                plan = cur.fetchall()
                
                for row in plan:
                    print(row[0])
                
                # 分析执行计划
                plan_text = '\n'.join([row[0] for row in plan])
                
                print("\n关键信息提取：")
                print("-"*80)
                
                # 检查窗口函数
                if 'WindowAgg' in plan_text:
                    print("✅ 使用了窗口函数")
                
                # 提取执行时间
                time_match = re.search(r'Execution Time: ([\d.]+) ms', plan_text)
                if time_match:
                    exec_time = float(time_match.group(1))
                    print(f"⏱️ 执行时间: {exec_time:.2f} ms ({exec_time/1000:.2f} 秒)")
                
                return True
                
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def count_actual_data(conn_str: str, start: str, end: str):
    """统计实际数据量"""
    print("\n" + "="*80)
    print("3. 实际数据量统计")
    print("="*80)
    
    sqls = {
        "fwin 总行数": """
            SELECT COUNT(*) 
            FROM public.fact_measurements
            WHERE ts_bucket >= %s::timestamptz 
              AND ts_bucket < %s::timestamptz
        """,
        "mv_presence_1s_any 行数": """
            SELECT COUNT(*) 
            FROM public.mv_presence_1s_any
            WHERE ts_bucket >= %s::timestamptz 
              AND ts_bucket < %s::timestamptz
        """,
        "缺失点数（估算）": """
            SELECT COUNT(*) 
            FROM public.fact_measurements f
            LEFT JOIN public.mv_presence_1s_any pr
              ON pr.station_id=f.station_id AND pr.device_id=f.device_id 
             AND pr.metric_id=f.metric_id AND pr.ts_bucket=f.ts_bucket
            WHERE f.ts_bucket >= %s::timestamptz 
              AND f.ts_bucket < %s::timestamptz
              AND (pr.present IS NULL OR pr.present=0)
            LIMIT 100000
        """
    }
    
    try:
        import psycopg
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                for name, sql in sqls.items():
                    cur.execute(sql, (start, end))
                    count = cur.fetchone()[0]
                    print(f"{name}: {count:,}")
                
                return True
                
    except Exception as e:
        print(f"❌ 统计失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='update_202 和 update_603 性能瓶颈分析')
    parser.add_argument('--start', required=True, help='开始时间')
    parser.add_argument('--end', required=True, help='结束时间')
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("update_202 和 update_603 性能瓶颈分析")
    print("="*80)
    print(f"时间窗口: {args.start} ~ {args.end}")
    
    # 初始化
    settings = load_settings(Path('configs'))
    init_database(settings)
    
    # 构建连接字符串
    conn_str = f"host={settings.db.host} dbname={settings.db.name} user={settings.db.user}"
    if settings.db.password:
        conn_str += f" password={settings.db.password}"
    
    # 执行分析
    result1 = analyze_mv_presence_view(conn_str, args.start, args.end)
    result2 = analyze_miss_spans_construction(conn_str, args.start, args.end)
    result3 = count_actual_data(conn_str, args.start, args.end)
    
    # 总结
    print("\n" + "="*80)
    print("分析总结")
    print("="*80)
    
    if result1:
        print("✅ mv_presence_1s_any 视图分析完成")
    else:
        print("❌ mv_presence_1s_any 视图分析失败")
    
    if result2:
        print("✅ t_miss_spans 构建分析完成")
    else:
        print("❌ t_miss_spans 构建分析失败")
    
    if result3:
        print("✅ 数据量统计完成")
    else:
        print("❌ 数据量统计失败")
    
    print("="*80)
    
    return 0 if (result1 and result2 and result3) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

