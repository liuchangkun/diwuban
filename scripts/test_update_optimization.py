"""
测试UPDATE语句优化

对比：
- 当前方案：复杂的CASE和重复的条件检查
- 优化方案：简化的UPDATE语句
"""

import time
import psycopg

DSN = "postgresql://postgres:q5707073@localhost:5432/pump_station_optimization"

def test_update_optimization():
    print("=" * 80)
    print("测试UPDATE语句优化")
    print("=" * 80)
    
    start_ts = "2025-10-23 13:19:37+08"
    end_ts = "2025-10-23 15:19:37+08"
    
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            # 设置work_mem
            cur.execute("SET work_mem = '256MB';")
            
            # 测试1：当前UPDATE语句（复杂版本）
            print("\n【测试1】当前UPDATE语句（复杂版本）")
            print("-" * 80)
            test_current_update(cur, start_ts, end_ts)
            conn.rollback()
            
            # 测试2：优化UPDATE语句（简化版本）
            print("\n【测试2】优化UPDATE语句（简化版本）")
            print("-" * 80)
            test_optimized_update(cur, start_ts, end_ts)
            conn.rollback()
            
            # 测试3：完整流程测试（模拟update_202规则）
            print("\n【测试3】完整流程测试（模拟update_202规则）")
            print("-" * 80)
            test_full_rule_202(cur, start_ts, end_ts)
            conn.rollback()

def test_current_update(cur, start_ts, end_ts):
    """测试当前UPDATE语句"""
    # 创建临时表
    cur.execute("""
        CREATE TEMP TABLE test_t202_current ON COMMIT DROP AS
        SELECT id, 10 AS gap_len_sec
        FROM public.fact_measurements
        WHERE ts_bucket >= %s::timestamptz
          AND ts_bucket < %s::timestamptz
        LIMIT 50000;
    """, (start_ts, end_ts))
    
    cur.execute("CREATE INDEX ON test_t202_current(id);")
    
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
    FROM test_t202_current t
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

def test_optimized_update(cur, start_ts, end_ts):
    """测试优化UPDATE语句"""
    # 创建临时表
    cur.execute("""
        CREATE TEMP TABLE test_t202_opt ON COMMIT DROP AS
        SELECT id, 10 AS gap_len_sec
        FROM public.fact_measurements
        WHERE ts_bucket >= %s::timestamptz
          AND ts_bucket < %s::timestamptz
        LIMIT 50000;
    """, (start_ts, end_ts))
    
    cur.execute("CREATE INDEX ON test_t202_opt(id);")
    
    # 优化UPDATE语句
    sql = """
    UPDATE public.fact_measurements u
    SET quality_codes = array_append(u.quality_codes, 998),
        quality_status = COALESCE(NULLIF(u.quality_status, 0), 998),
        quality_type='测试优化',
        quality_meta=jsonb_build_object('gap_len_sec',t.gap_len_sec)
    FROM test_t202_opt t
    WHERE u.id=t.id
      AND u.quality_codes = '{}'::int[];
    """
    
    start_time = time.time()
    cur.execute(sql)
    duration = time.time() - start_time
    rows = cur.rowcount
    
    print(f"  耗时: {duration:.2f}秒")
    print(f"  影响行数: {rows}")
    print(f"  速率: {rows/duration:.0f} 行/秒")

def test_full_rule_202(cur, start_ts, end_ts):
    """测试完整的update_202规则流程"""
    print("\n  步骤1：构建fwin临时表")
    t1 = time.time()
    cur.execute("""
        CREATE TEMP TABLE fwin_test ON COMMIT DROP AS
        SELECT id, station_id, device_id, metric_id, ts_bucket, value, 
               COALESCE(quality_status,0) AS qs,
               quality_codes
        FROM public.fact_measurements
        WHERE ts_bucket >= %s::timestamptz
          AND ts_bucket < %s::timestamptz;
    """, (start_ts, end_ts))
    cur.execute("CREATE INDEX ON fwin_test(station_id, device_id, metric_id, ts_bucket);")
    d1 = time.time() - t1
    print(f"    耗时: {d1:.2f}秒")
    
    print("\n  步骤2：构建t_pr_miss（presence misses）")
    t2 = time.time()
    cur.execute("""
        CREATE TEMP TABLE t_pr_miss_test ON COMMIT DROP AS
        SELECT f.station_id, f.device_id, f.metric_id, f.ts_bucket
        FROM fwin_test f
        JOIN public.dim_metric_config mc ON mc.id=f.metric_id
        LEFT JOIN public.mv_presence_1s_any pr
          ON pr.station_id=f.station_id AND pr.device_id=f.device_id 
         AND pr.metric_id=f.metric_id AND pr.ts_bucket=f.ts_bucket
        WHERE f.qs=0
          AND mc.metric_key NOT IN ('device_running','device_phase')
          AND (pr.present IS NULL OR pr.present=0);
    """)
    d2 = time.time() - t2
    print(f"    耗时: {d2:.2f}秒")
    
    print("\n  步骤3：构建t_miss_spans（gap detection）")
    t3 = time.time()
    cur.execute("""
        CREATE TEMP TABLE t_miss_spans_test ON COMMIT DROP AS
        WITH x AS (
          SELECT station_id, device_id, metric_id, ts_bucket,
                 ts_bucket - (row_number() OVER (PARTITION BY station_id, device_id, metric_id ORDER BY ts_bucket))*interval '1 second' AS grp
          FROM t_pr_miss_test
        )
        SELECT station_id, device_id, metric_id,
               MIN(ts_bucket) AS gap_start_ts,
               MAX(ts_bucket) AS gap_end_ts,
               EXTRACT(EPOCH FROM (MAX(ts_bucket) - MIN(ts_bucket)))::int + 1 AS gap_len_sec
        FROM x
        GROUP BY station_id, device_id, metric_id, grp;
    """)
    d3 = time.time() - t3
    print(f"    耗时: {d3:.2f}秒")
    
    print("\n  步骤4：过滤t202_final（gap_len_sec >= 5）")
    t4 = time.time()
    cur.execute("""
        CREATE TEMP TABLE t202_final_test ON COMMIT DROP AS
        SELECT * FROM t_miss_spans_test WHERE gap_len_sec >= 5;
    """)
    d4 = time.time() - t4
    print(f"    耗时: {d4:.2f}秒")
    
    print("\n  步骤5：映射到row IDs（t202_ids）")
    t5 = time.time()
    cur.execute("""
        CREATE TEMP TABLE t202_ids_test ON COMMIT DROP AS
        SELECT f.id, f.station_id, f.device_id, f.metric_id, f.ts_bucket, t.gap_len_sec
        FROM fwin_test f
        JOIN t202_final_test t
          ON t.station_id=f.station_id AND t.device_id=f.device_id AND t.metric_id=f.metric_id
         AND f.ts_bucket BETWEEN t.gap_start_ts AND t.gap_end_ts;
    """)
    cur.execute("CREATE INDEX ON t202_ids_test(id);")
    d5 = time.time() - t5
    rows_to_update = cur.rowcount
    print(f"    耗时: {d5:.2f}秒")
    print(f"    待更新行数: {rows_to_update}")
    
    print("\n  步骤6：执行UPDATE（优化版本）")
    t6 = time.time()
    cur.execute("""
        UPDATE public.fact_measurements u
        SET quality_codes = array_append(u.quality_codes, 997),
            quality_status = COALESCE(NULLIF(u.quality_status, 0), 997),
            quality_type='测试完整流程',
            quality_meta=jsonb_build_object('gap_len_sec',t.gap_len_sec)
        FROM t202_ids_test t
        WHERE u.id=t.id
          AND u.quality_codes = '{}'::int[];
    """)
    d6 = time.time() - t6
    rows_updated = cur.rowcount
    print(f"    耗时: {d6:.2f}秒")
    print(f"    实际更新行数: {rows_updated}")
    print(f"    速率: {rows_updated/d6:.0f} 行/秒")
    
    total_time = d1 + d2 + d3 + d4 + d5 + d6
    print(f"\n  总耗时: {total_time:.2f}秒")
    print(f"  各步骤占比:")
    print(f"    fwin构建: {d1/total_time*100:.1f}%")
    print(f"    pr_miss: {d2/total_time*100:.1f}%")
    print(f"    miss_spans: {d3/total_time*100:.1f}%")
    print(f"    t202_final: {d4/total_time*100:.1f}%")
    print(f"    t202_ids: {d5/total_time*100:.1f}%")
    print(f"    UPDATE: {d6/total_time*100:.1f}%")

if __name__ == "__main__":
    test_update_optimization()

