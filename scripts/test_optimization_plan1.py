"""
测试优化方案1：修改WHERE条件

对比：
- 当前方案：AND NOT (202 = ANY(COALESCE(u.quality_codes, '{}'::int[])))
- 优化方案：AND u.quality_status = 0
"""

import time
import psycopg

DSN = "postgresql://postgres:q5707073@localhost:5432/pump_station_optimization"

def test_optimization():
    print("=" * 80)
    print("测试优化方案1：修改WHERE条件")
    print("=" * 80)
    
    start_ts = "2025-10-23 13:19:37+08"
    end_ts = "2025-10-23 15:19:37+08"
    
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            # 测试1：当前方案（数组操作）
            print("\n【测试1】当前方案（数组操作）")
            print("-" * 80)
            test_current_approach(cur, start_ts, end_ts)
            conn.rollback()
            
            # 测试2：优化方案（quality_status过滤）
            print("\n【测试2】优化方案（quality_status过滤）")
            print("-" * 80)
            test_optimized_approach(cur, start_ts, end_ts)
            conn.rollback()
            
            # 测试3：执行计划对比
            print("\n【测试3】执行计划对比")
            print("-" * 80)
            compare_execution_plans(cur, start_ts, end_ts)

def test_current_approach(cur, start_ts, end_ts):
    """测试当前方案"""
    # 创建临时表模拟t202_ids
    cur.execute("""
        CREATE TEMP TABLE test_t202_ids ON COMMIT DROP AS
        SELECT id, 10 AS gap_len_sec
        FROM public.fact_measurements
        WHERE ts_bucket >= %s::timestamptz
          AND ts_bucket < %s::timestamptz
        LIMIT 10000;
    """, (start_ts, end_ts))
    
    cur.execute("CREATE INDEX ON test_t202_ids(id);")
    
    # 当前UPDATE语句
    sql = """
    UPDATE public.fact_measurements u
    SET quality_codes = CASE
          WHEN NOT (999 = ANY(COALESCE(u.quality_codes, '{}'::int[])))
            THEN array_append(COALESCE(u.quality_codes, '{}'::int[]), 999)
            ELSE u.quality_codes
        END,
        quality_status = CASE WHEN COALESCE(u.quality_status,0)=0 THEN 999 ELSE u.quality_status END,
        quality_type='测试',
        quality_meta=jsonb_build_object('gap_len_sec',t.gap_len_sec)
    FROM test_t202_ids t
    WHERE u.id=t.id
      AND NOT (999 = ANY(COALESCE(u.quality_codes, '{}'::int[])));
    """
    
    start_time = time.time()
    cur.execute(sql)
    duration = time.time() - start_time
    rows = cur.rowcount
    
    print(f"  耗时: {duration:.2f}秒")
    print(f"  影响行数: {rows}")
    print(f"  速率: {rows/duration:.0f} 行/秒")

def test_optimized_approach(cur, start_ts, end_ts):
    """测试优化方案"""
    # 创建临时表模拟t202_ids
    cur.execute("""
        CREATE TEMP TABLE test_t202_ids_opt ON COMMIT DROP AS
        SELECT id, 10 AS gap_len_sec
        FROM public.fact_measurements
        WHERE ts_bucket >= %s::timestamptz
          AND ts_bucket < %s::timestamptz
        LIMIT 10000;
    """, (start_ts, end_ts))
    
    cur.execute("CREATE INDEX ON test_t202_ids_opt(id);")
    
    # 优化UPDATE语句
    sql = """
    UPDATE public.fact_measurements u
    SET quality_codes = array_append(COALESCE(u.quality_codes, '{}'::int[]), 998),
        quality_status = COALESCE(NULLIF(u.quality_status, 0), 998),
        quality_type='测试优化',
        quality_meta=jsonb_build_object('gap_len_sec',t.gap_len_sec)
    FROM test_t202_ids_opt t
    WHERE u.id=t.id
      AND u.quality_status = 0;  -- 优化：使用整数字段过滤
    """
    
    start_time = time.time()
    cur.execute(sql)
    duration = time.time() - start_time
    rows = cur.rowcount
    
    print(f"  耗时: {duration:.2f}秒")
    print(f"  影响行数: {rows}")
    print(f"  速率: {rows/duration:.0f} 行/秒")

def compare_execution_plans(cur, start_ts, end_ts):
    """对比执行计划"""
    # 创建临时表
    cur.execute("""
        CREATE TEMP TABLE test_ids_plan ON COMMIT DROP AS
        SELECT id FROM public.fact_measurements
        WHERE ts_bucket >= %s::timestamptz
          AND ts_bucket < %s::timestamptz
        LIMIT 1000;
    """, (start_ts, end_ts))
    
    cur.execute("CREATE INDEX ON test_ids_plan(id);")
    
    # 执行计划1：当前方案
    print("\n执行计划1：当前方案（数组操作）")
    print("-" * 80)
    cur.execute("""
        EXPLAIN (ANALYZE, BUFFERS)
        UPDATE public.fact_measurements u
        SET quality_codes = array_append(COALESCE(u.quality_codes, '{}'::int[]), 997)
        FROM test_ids_plan t
        WHERE u.id=t.id
          AND NOT (997 = ANY(COALESCE(u.quality_codes, '{}'::int[])));
    """)
    
    for row in cur.fetchall():
        if 'Seq Scan' in row[0] or 'Index Scan' in row[0] or 'actual time' in row[0]:
            print(row[0])
    
    cur.execute("ROLLBACK;")
    
    # 重新创建临时表
    cur.execute("""
        CREATE TEMP TABLE test_ids_plan2 ON COMMIT DROP AS
        SELECT id FROM public.fact_measurements
        WHERE ts_bucket >= %s::timestamptz
          AND ts_bucket < %s::timestamptz
        LIMIT 1000;
    """, (start_ts, end_ts))
    
    cur.execute("CREATE INDEX ON test_ids_plan2(id);")
    
    # 执行计划2：优化方案
    print("\n执行计划2：优化方案（quality_status过滤）")
    print("-" * 80)
    cur.execute("""
        EXPLAIN (ANALYZE, BUFFERS)
        UPDATE public.fact_measurements u
        SET quality_codes = array_append(COALESCE(u.quality_codes, '{}'::int[]), 996)
        FROM test_ids_plan2 t
        WHERE u.id=t.id
          AND u.quality_status = 0;
    """)
    
    for row in cur.fetchall():
        if 'Seq Scan' in row[0] or 'Index Scan' in row[0] or 'actual time' in row[0]:
            print(row[0])

if __name__ == "__main__":
    test_optimization()

