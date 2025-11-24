#!/usr/bin/env python3
"""
执行计划分析脚本：验证 P0 优化是否生效

用途：
1. 分析 mv_device_running_1s 注入的执行计划
2. 分析规则503快速通道的执行计划
3. 验证是否使用了 Hash Join 或 Merge Join
4. 识别性能瓶颈

使用方法：
    python scripts/analyze_execution_plan.py --start "2025-10-22 16:00:00" --end "2025-10-22 18:00:00"
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


def analyze_mv_device_running_injection(conn_str: str, start: str, end: str):
    """分析 mv_device_running_1s 注入的执行计划"""
    print("\n" + "="*80)
    print("1. mv_device_running_1s 注入执行计划分析（P0优化点1）")
    print("="*80)

    # 模拟存储过程中的SQL（简化版，使用临时表模拟fwin）
    # 注意：mv_device_running_1s 的主键是 (station_id, device_id, ts_bucket)，没有 id 字段
    sql = """
    EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
    SELECT r.station_id, r.device_id, r.ts_bucket, r.running::int
    FROM public.mv_device_running_1s r
    LEFT JOIN public.mv_device_running_1s x ON (
        x.station_id = r.station_id
        AND x.device_id = r.device_id
        AND x.ts_bucket = r.ts_bucket
    )
    WHERE r.ts_bucket >= %s::timestamptz
      AND r.ts_bucket < %s::timestamptz
      AND x.station_id IS NULL
    LIMIT 100;
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
                
                # 检查 Join 类型
                if 'Hash Join' in plan_text:
                    print("✅ 使用了 Hash Join")
                elif 'Merge Join' in plan_text:
                    print("✅ 使用了 Merge Join")
                elif 'Nested Loop' in plan_text:
                    print("⚠️ 使用了 Nested Loop（性能较差）")
                else:
                    print("❓ 未检测到明确的 Join 类型")
                
                # 检查索引使用
                if 'Index Scan' in plan_text or 'Index Only Scan' in plan_text:
                    print("✅ 使用了索引扫描")
                elif 'Seq Scan' in plan_text:
                    print("⚠️ 使用了顺序扫描")
                
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


def analyze_rule_503_fast_path(conn_str: str, start: str, end: str):
    """分析规则503快速通道的执行计划"""
    print("\n" + "="*80)
    print("2. 规则503快速通道执行计划分析（P0优化点2）")
    print("="*80)

    # 创建临时表的SQL语句（分开执行）
    setup_sqls = [
        "DROP TABLE IF EXISTS temp_t503_keys_with_total",
        """
        CREATE TEMP TABLE temp_t503_keys_with_total AS
        SELECT DISTINCT
            station_id,
            device_id,
            metric_id,
            7200 as total_secs
        FROM public.fact_measurements
        WHERE ts_bucket >= %s::timestamptz
          AND ts_bucket < %s::timestamptz
        LIMIT 100
        """,
        "CREATE INDEX ON temp_t503_keys_with_total(station_id, device_id, metric_id)",
        "DROP TABLE IF EXISTS temp_t503_pr_agg",
        """
        CREATE TEMP TABLE temp_t503_pr_agg AS
        SELECT
            station_id,
            device_id,
            metric_id,
            COUNT(*) AS present_total
        FROM public.mv_presence_1s_any
        WHERE ts_bucket >= %s::timestamptz
          AND ts_bucket < %s::timestamptz
          AND present = 1
        GROUP BY 1, 2, 3
        LIMIT 100
        """,
        "CREATE INDEX ON temp_t503_pr_agg(station_id, device_id, metric_id)"
    ]
    
    # 分析SQL
    analyze_sql = """
    EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
    SELECT COUNT(*)
    FROM temp_t503_keys_with_total ts
    LEFT JOIN temp_t503_pr_agg pr USING (station_id, device_id, metric_id)
    WHERE COALESCE(pr.present_total, 0) < ts.total_secs;
    """
    
    try:
        import psycopg
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                # 创建临时表（分开执行）
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
                
                # 检查 Join 类型
                if 'Hash Join' in plan_text or 'Hash Left Join' in plan_text:
                    print("✅ 使用了 Hash Join")
                elif 'Merge Join' in plan_text or 'Merge Left Join' in plan_text:
                    print("✅ 使用了 Merge Join")
                elif 'Nested Loop' in plan_text:
                    print("⚠️ 使用了 Nested Loop（性能较差）")
                else:
                    print("❓ 未检测到明确的 Join 类型")
                
                # 检查索引使用
                if 'Index Scan' in plan_text or 'Index Only Scan' in plan_text:
                    print("✅ 使用了索引扫描")
                elif 'Seq Scan' in plan_text:
                    print("⚠️ 使用了顺序扫描")
                
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


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='执行计划分析')
    parser.add_argument('--start', required=True, help='开始时间')
    parser.add_argument('--end', required=True, help='结束时间')
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("执行计划分析 - P0 优化验证")
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
    result1 = analyze_mv_device_running_injection(conn_str, args.start, args.end)
    result2 = analyze_rule_503_fast_path(conn_str, args.start, args.end)
    
    # 总结
    print("\n" + "="*80)
    print("分析总结")
    print("="*80)
    
    if result1:
        print("✅ mv_device_running_1s 注入分析完成")
    else:
        print("❌ mv_device_running_1s 注入分析失败")
    
    if result2:
        print("✅ 规则503快速通道分析完成")
    else:
        print("❌ 规则503快速通道分析失败")
    
    print("="*80)
    
    return 0 if (result1 and result2) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

