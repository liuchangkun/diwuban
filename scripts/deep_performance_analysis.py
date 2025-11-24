"""
深度性能分析脚本

目的：分析为什么首次标注速度只有3,544行/秒，而不是预期的90,000+行/秒
重点：分析UPDATE语句的性能瓶颈
"""

import time
import psycopg

# 数据库连接字符串
DSN = "postgresql://postgres:q5707073@localhost:5432/pump_station_optimization"

def analyze_update_performance():
    """分析UPDATE语句的性能瓶颈"""
    
    print("=" * 80)
    print("深度性能分析：UPDATE语句瓶颈")
    print("=" * 80)
    
    # 测试窗口
    start_ts = "2025-10-23 13:19:37+08"
    end_ts = "2025-10-23 15:19:37+08"
    
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            # 分析1：检查UPDATE语句的实际执行计划
            print("\n【分析1】UPDATE语句执行计划")
            print("-" * 80)
            
            # 模拟update_202的UPDATE语句
            explain_sql = """
            EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
            UPDATE public.fact_measurements u
            SET quality_codes = CASE
                  WHEN NOT (202 = ANY(COALESCE(u.quality_codes, '{}'::int[])))
                    THEN array_append(COALESCE(u.quality_codes, '{}'::int[]), 202)
                    ELSE u.quality_codes
                END,
                quality_status = CASE WHEN COALESCE(u.quality_status,0)=0 THEN 202 ELSE u.quality_status END,
                quality_type='间歇性中断',
                quality_meta=jsonb_build_object('gap_len_sec', 10)
            FROM (
                SELECT id FROM public.fact_measurements
                WHERE ts_bucket >= %s::timestamptz
                  AND ts_bucket < %s::timestamptz
                LIMIT 1000  -- 限制1000行进行测试
            ) t
            WHERE u.id=t.id
              AND NOT (202 = ANY(COALESCE(u.quality_codes, '{}'::int[])));
            """
            
            try:
                cur.execute(explain_sql, (start_ts, end_ts))
                print("\n执行计划：")
                for row in cur.fetchall():
                    print(row[0])
            except Exception as e:
                print(f"❌ 执行计划分析失败：{e}")
                conn.rollback()
            
            # 分析2：测试不同UPDATE策略的性能
            print("\n\n【分析2】不同UPDATE策略性能对比")
            print("-" * 80)
            
            # 策略1：当前策略（带CASE和数组操作）
            print("\n策略1：当前策略（带CASE和数组操作）")
            test_update_strategy_1(cur, start_ts, end_ts)
            conn.rollback()
            
            # 策略2：简化策略（直接赋值，不检查重复）
            print("\n策略2：简化策略（直接赋值，不检查重复）")
            test_update_strategy_2(cur, start_ts, end_ts)
            conn.rollback()
            
            # 策略3：批量UPDATE（使用临时表）
            print("\n策略3：批量UPDATE（使用临时表）")
            test_update_strategy_3(cur, start_ts, end_ts)
            conn.rollback()
            
            # 分析3：检查索引使用情况
            print("\n\n【分析3】索引使用情况")
            print("-" * 80)
            analyze_index_usage(cur)
            
            # 分析4：检查表膨胀和碎片化
            print("\n\n【分析4】表膨胀和碎片化")
            print("-" * 80)
            analyze_table_bloat(cur)

def test_update_strategy_1(cur, start_ts, end_ts):
    """测试策略1：当前策略"""
    sql = """
    UPDATE public.fact_measurements u
    SET quality_codes = CASE
          WHEN NOT (999 = ANY(COALESCE(u.quality_codes, '{}'::int[])))
            THEN array_append(COALESCE(u.quality_codes, '{}'::int[]), 999)
            ELSE u.quality_codes
        END,
        quality_status = CASE WHEN COALESCE(u.quality_status,0)=0 THEN 999 ELSE u.quality_status END
    FROM (
        SELECT id FROM public.fact_measurements
        WHERE ts_bucket >= %s::timestamptz
          AND ts_bucket < %s::timestamptz
        LIMIT 10000
    ) t
    WHERE u.id=t.id
      AND NOT (999 = ANY(COALESCE(u.quality_codes, '{}'::int[])));
    """
    
    start_time = time.time()
    cur.execute(sql, (start_ts, end_ts))
    duration = time.time() - start_time
    rows = cur.rowcount
    
    print(f"  耗时: {duration:.2f}秒")
    print(f"  影响行数: {rows}")
    print(f"  速率: {rows/duration:.0f} 行/秒")

def test_update_strategy_2(cur, start_ts, end_ts):
    """测试策略2：简化策略"""
    sql = """
    UPDATE public.fact_measurements u
    SET quality_codes = array_append(COALESCE(u.quality_codes, '{}'::int[]), 998),
        quality_status = COALESCE(NULLIF(u.quality_status, 0), 998)
    FROM (
        SELECT id FROM public.fact_measurements
        WHERE ts_bucket >= %s::timestamptz
          AND ts_bucket < %s::timestamptz
        LIMIT 10000
    ) t
    WHERE u.id=t.id;
    """
    
    start_time = time.time()
    cur.execute(sql, (start_ts, end_ts))
    duration = time.time() - start_time
    rows = cur.rowcount
    
    print(f"  耗时: {duration:.2f}秒")
    print(f"  影响行数: {rows}")
    print(f"  速率: {rows/duration:.0f} 行/秒")

def test_update_strategy_3(cur, start_ts, end_ts):
    """测试策略3：批量UPDATE"""
    # 创建临时表
    cur.execute("""
        CREATE TEMP TABLE test_ids ON COMMIT DROP AS
        SELECT id FROM public.fact_measurements
        WHERE ts_bucket >= %s::timestamptz
          AND ts_bucket < %s::timestamptz
        LIMIT 10000;
    """, (start_ts, end_ts))
    
    cur.execute("CREATE INDEX ON test_ids(id);")
    
    sql = """
    UPDATE public.fact_measurements u
    SET quality_codes = array_append(COALESCE(u.quality_codes, '{}'::int[]), 997),
        quality_status = COALESCE(NULLIF(u.quality_status, 0), 997)
    FROM test_ids t
    WHERE u.id=t.id;
    """
    
    start_time = time.time()
    cur.execute(sql)
    duration = time.time() - start_time
    rows = cur.rowcount
    
    print(f"  耗时: {duration:.2f}秒")
    print(f"  影响行数: {rows}")
    print(f"  速率: {rows/duration:.0f} 行/秒")

def analyze_index_usage(cur):
    """分析索引使用情况"""
    sql = """
    SELECT 
        indexrelname AS index_name,
        idx_scan AS index_scans,
        idx_tup_read AS tuples_read,
        idx_tup_fetch AS tuples_fetched,
        pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
    FROM pg_stat_user_indexes
    WHERE schemaname = 'public'
      AND relname = 'fact_measurements'
    ORDER BY idx_scan DESC;
    """
    
    cur.execute(sql)
    rows = cur.fetchall()
    
    print(f"\n{'索引名':<50} {'扫描次数':<15} {'读取元组':<15} {'获取元组':<15} {'大小':<10}")
    print("-" * 105)
    for row in rows:
        print(f"{row[0]:<50} {row[1]:<15} {row[2]:<15} {row[3]:<15} {row[4]:<10}")

def analyze_table_bloat(cur):
    """分析表膨胀"""
    sql = """
    SELECT 
        schemaname,
        relname,
        n_live_tup,
        n_dead_tup,
        CASE WHEN n_live_tup > 0 
             THEN ROUND(n_dead_tup::numeric / n_live_tup, 2)
             ELSE 0 END AS bloat_ratio,
        last_vacuum,
        last_autovacuum
    FROM pg_stat_user_tables
    WHERE relname LIKE '_hyper_3_32%'
    ORDER BY n_dead_tup DESC;
    """
    
    cur.execute(sql)
    rows = cur.fetchall()
    
    print(f"\n{'表名':<30} {'活跃行':<15} {'死亡行':<15} {'膨胀比例':<10} {'最后VACUUM':<25}")
    print("-" * 95)
    for row in rows:
        print(f"{row[1]:<30} {row[2]:<15} {row[3]:<15} {row[4]:<10} {str(row[6]):<25}")

if __name__ == "__main__":
    analyze_update_performance()

