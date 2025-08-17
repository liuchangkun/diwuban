-- CRUD优化函数集合
-- 用于支持频繁的增删改查操作

SET client_encoding = 'UTF8';
SET client_min_messages = WARNING;
SET search_path = public;

BEGIN;

-- ============================================================================
-- 1. 数据一致性保障函数
-- ============================================================================

-- 1.1 安全的UPSERT函数，避免并发冲突
CREATE OR REPLACE FUNCTION safe_upsert_measurement(
  p_station_id bigint,
  p_device_id bigint,
  p_metric_id bigint,
  p_ts_raw timestamptz,
  p_value numeric,
  p_source_hint text
) RETURNS boolean AS $$
DECLARE
  v_ts_bucket timestamptz;
  v_affected_rows int;
BEGIN
  v_ts_bucket := date_trunc('second', p_ts_raw);

  -- 使用 SELECT FOR UPDATE 避免并发冲突
  PERFORM 1 FROM fact_measurements
  WHERE station_id = p_station_id
    AND device_id = p_device_id
    AND metric_id = p_metric_id
    AND ts_bucket = v_ts_bucket
  FOR UPDATE NOWAIT;

  -- 执行UPSERT
  INSERT INTO fact_measurements (station_id, device_id, metric_id, ts_raw, ts_bucket, value, source_hint)
  VALUES (p_station_id, p_device_id, p_metric_id, p_ts_raw, v_ts_bucket, p_value, p_source_hint)
  ON CONFLICT (station_id, device_id, metric_id, ts_bucket)
  DO UPDATE SET
    value = EXCLUDED.value,
    ts_raw = EXCLUDED.ts_raw,
    source_hint = EXCLUDED.source_hint,
    inserted_at = now();

  GET DIAGNOSTICS v_affected_rows = ROW_COUNT;
  RETURN v_affected_rows > 0;

EXCEPTION
  WHEN lock_not_available THEN
    RAISE NOTICE 'Record locked, skipping update for station %, device %, metric % at %',
                 p_station_id, p_device_id, p_metric_id, v_ts_bucket;
    RETURN false;
END;
$$ LANGUAGE plpgsql;

-- 1.2 数据一致性检查函数
CREATE OR REPLACE FUNCTION check_data_consistency()
RETURNS TABLE(issue_type text, details text) AS $$
BEGIN
  -- 检查重复记录
  RETURN QUERY
  SELECT 'duplicate_records'::text,
         format('Station %s, Device %s, Metric %s has %s records at %s',
                station_id, device_id, metric_id, cnt, ts_bucket)
  FROM (
    SELECT station_id, device_id, metric_id, ts_bucket, count(*) as cnt
    FROM fact_measurements
    WHERE ts_bucket >= now() - interval '1 hour'
    GROUP BY station_id, device_id, metric_id, ts_bucket
    HAVING count(*) > 1
  ) duplicates;

  -- 检查外键完整性
  RETURN QUERY
  SELECT 'missing_references'::text,
         format('Metric ID %s not found in dim_metric_config', metric_id)
  FROM fact_measurements fm
  LEFT JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
  WHERE dmc.id IS NULL
  AND fm.ts_bucket >= now() - interval '1 hour'
  LIMIT 10;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 2. 性能监控函数
-- ============================================================================

-- 2.1 性能指标监控函数
CREATE OR REPLACE FUNCTION get_performance_metrics()
RETURNS TABLE(
  metric_name text,
  current_value numeric,
  threshold_value numeric,
  status text
) AS $$
BEGIN
  -- 查询性能指标
  RETURN QUERY
  SELECT 'avg_query_time'::text,
         COALESCE(avg(total_time), 0)::numeric,
         1000::numeric,  -- 1秒阈值
         CASE WHEN COALESCE(avg(total_time), 0) > 1000 THEN 'WARNING' ELSE 'OK' END
  FROM pg_stat_statements
  WHERE query LIKE '%fact_measurements%'
    AND calls > 10;

  -- 锁等待指标
  RETURN QUERY
  SELECT 'lock_waits'::text,
         count(*)::numeric,
         10::numeric,  -- 10个锁等待阈值
         CASE WHEN count(*) > 10 THEN 'CRITICAL' ELSE 'OK' END
  FROM pg_locks
  WHERE NOT granted;

  -- 连接数指标
  RETURN QUERY
  SELECT 'active_connections'::text,
         count(*)::numeric,
         100::numeric,  -- 100连接阈值
         CASE WHEN count(*) > 100 THEN 'WARNING' ELSE 'OK' END
  FROM pg_stat_activity
  WHERE state = 'active';

  -- 死元组比例
  RETURN QUERY
  SELECT 'dead_tuple_ratio'::text,
         CASE WHEN n_live_tup > 0 THEN (n_dead_tup::numeric / n_live_tup::numeric * 100) ELSE 0 END,
         20::numeric,  -- 20%阈值
         CASE WHEN n_live_tup > 0 AND (n_dead_tup::numeric / n_live_tup::numeric * 100) > 20 THEN 'WARNING' ELSE 'OK' END
  FROM pg_stat_user_tables
  WHERE relname = 'fact_measurements';
END;
$$ LANGUAGE plpgsql;

-- 2.2 性能告警检查函数
CREATE OR REPLACE FUNCTION check_performance_alerts()
RETURNS text AS $$
DECLARE
  alert_message text := '';
  rec record;
BEGIN
  FOR rec IN SELECT * FROM get_performance_metrics() WHERE status != 'OK'
  LOOP
    alert_message := alert_message || format('ALERT: %s = %s (threshold: %s) - %s\n',
                                           rec.metric_name, rec.current_value,
                                           rec.threshold_value, rec.status);
  END LOOP;

  IF alert_message != '' THEN
    -- 记录到日志
    RAISE WARNING 'Performance Alert: %', alert_message;
  END IF;

  RETURN COALESCE(alert_message, 'All metrics OK');
END;
$$ LANGUAGE plpgsql;

-- 2.3 自动性能调优函数
CREATE OR REPLACE FUNCTION auto_performance_tuning()
RETURNS text AS $$
DECLARE
  tuning_actions text := '';
  rec record;
BEGIN
  -- 检查是否需要更新统计信息
  IF EXISTS (
    SELECT 1 FROM pg_stat_user_tables
    WHERE schemaname = 'public'
      AND relname = 'fact_measurements'
      AND n_mod_since_analyze > 100000  -- 大量修改未分析
  ) THEN
    tuning_actions := tuning_actions || 'Updating table statistics\n';
    ANALYZE fact_measurements;
  END IF;

  -- 检查分区统计信息
  FOR rec IN
    SELECT tablename FROM pg_tables
    WHERE tablename LIKE 'fact_measurements_%'
      AND schemaname = 'public'
  LOOP
    IF EXISTS (
      SELECT 1 FROM pg_stat_user_tables
      WHERE relname = rec.tablename
        AND n_mod_since_analyze > 10000
    ) THEN
      tuning_actions := tuning_actions || format('Analyzing partition %s\n', rec.tablename);
      EXECUTE format('ANALYZE %s', rec.tablename);
    END IF;
  END LOOP;

  RETURN COALESCE(tuning_actions, 'No tuning needed');
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 3. 存储管理函数
-- ============================================================================

-- 3.1 智能VACUUM策略函数
CREATE OR REPLACE FUNCTION smart_vacuum_strategy()
RETURNS text AS $$
DECLARE
  partition_name text;
  dead_tuple_ratio numeric;
  vacuum_actions text := '';
  rec record;
BEGIN
  -- 检查每个分区的死元组比例
  FOR rec IN
    SELECT schemaname, tablename,
           CASE WHEN n_live_tup > 0 THEN n_dead_tup::numeric / n_live_tup::numeric ELSE 0 END as ratio,
           n_dead_tup, n_live_tup
    FROM pg_stat_user_tables
    WHERE tablename LIKE 'fact_measurements%'
      AND schemaname = 'public'
  LOOP
    partition_name := rec.schemaname || '.' || rec.tablename;
    dead_tuple_ratio := rec.ratio;

    -- 根据死元组比例决定VACUUM策略
    IF dead_tuple_ratio > 0.2 THEN  -- 20%以上死元组
      vacuum_actions := vacuum_actions || format('VACUUM (VERBOSE, ANALYZE) %s; -- %.1f%% dead tuples\n',
                                                 partition_name, dead_tuple_ratio * 100);
      EXECUTE format('VACUUM (VERBOSE, ANALYZE) %s', partition_name);
    ELSIF dead_tuple_ratio > 0.1 THEN  -- 10-20%死元组
      vacuum_actions := vacuum_actions || format('VACUUM %s; -- %.1f%% dead tuples\n',
                                                 partition_name, dead_tuple_ratio * 100);
      EXECUTE format('VACUUM %s', partition_name);
    END IF;
  END LOOP;

  RETURN COALESCE(vacuum_actions, 'No vacuum needed');
END;
$$ LANGUAGE plpgsql;

-- 3.2 存储监控视图
CREATE OR REPLACE VIEW v_storage_monitoring AS
SELECT
  schemaname,
  relname AS tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||relname)) as total_size,
  pg_size_pretty(pg_relation_size(schemaname||'.'||relname)) as table_size,
  pg_size_pretty(pg_indexes_size(schemaname||'.'||relname)) as index_size,
  n_live_tup,
  n_dead_tup,
  CASE
    WHEN n_live_tup > 0 THEN round((n_dead_tup::numeric / n_live_tup::numeric) * 100, 2)
    ELSE 0
  END as dead_tuple_ratio,
  last_vacuum,
  last_autovacuum,
  last_analyze,
  last_autoanalyze
FROM pg_stat_user_tables
WHERE relname LIKE 'fact_measurements%'
ORDER BY pg_total_relation_size(schemaname||'.'||relname) DESC;

-- 3.3 自动空间回收函数
CREATE OR REPLACE FUNCTION auto_space_reclaim()
RETURNS text AS $$
DECLARE
  reclaim_actions text := '';
  partition_record record;
BEGIN
  -- 检查需要回收空间的分区
  FOR partition_record IN
    SELECT relname AS tablename,
           n_dead_tup,
           n_live_tup,
           pg_total_relation_size(schemaname||'.'||relname) as size_bytes
    FROM pg_stat_user_tables
    WHERE relname LIKE 'fact_measurements_%'
      AND n_dead_tup > 100000  -- 超过10万死元组
      AND n_dead_tup::numeric / GREATEST(n_live_tup, 1)::numeric > 0.3  -- 死元组比例>30%
  LOOP
    -- 记录需要VACUUM FULL的分区（注意：会锁表）
    IF partition_record.size_bytes > 1073741824 THEN  -- 大于1GB的分区
      reclaim_actions := reclaim_actions || format('-- VACUUM FULL %I; -- Size: %s, Dead: %s\n',
                                                   partition_record.tablename,
                                                   pg_size_pretty(partition_record.size_bytes),
                                                   partition_record.n_dead_tup);
    END IF;
  END LOOP;

  RETURN COALESCE(reclaim_actions, 'No space reclaim needed');
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 4. 批量操作辅助函数
-- ============================================================================

-- 4.1 批量删除历史数据函数
CREATE OR REPLACE FUNCTION batch_delete_old_data(
  p_cutoff_date timestamptz,
  p_batch_size int DEFAULT 10000
) RETURNS text AS $$
DECLARE
  deleted_count int := 0;
  total_deleted int := 0;
  delete_actions text := '';
BEGIN
  LOOP
    DELETE FROM fact_measurements
    WHERE ts_bucket < p_cutoff_date
    AND id IN (
      SELECT id FROM fact_measurements
      WHERE ts_bucket < p_cutoff_date
      LIMIT p_batch_size
    );

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    total_deleted := total_deleted + deleted_count;

    IF deleted_count = 0 THEN
      EXIT;
    END IF;

    -- 短暂休息，避免长时间锁表
    PERFORM pg_sleep(0.1);
  END LOOP;

  delete_actions := format('Deleted %s records older than %s', total_deleted, p_cutoff_date);
  RETURN delete_actions;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 5. 综合健康检查函数
-- ============================================================================

-- 5.1 数据库健康检查函数
CREATE OR REPLACE FUNCTION database_health_check()
RETURNS TABLE(
  check_category text,
  check_name text,
  status text,
  details text
) AS $$
BEGIN
  -- 数据一致性检查
  RETURN QUERY
  SELECT 'consistency'::text, 'data_integrity'::text,
         CASE WHEN count(*) = 0 THEN 'OK' ELSE 'WARNING' END,
         format('%s consistency issues found', count(*))
  FROM check_data_consistency();

  -- 性能检查
  RETURN QUERY
  SELECT 'performance'::text, metric_name, status,
         format('Current: %s, Threshold: %s', current_value, threshold_value)
  FROM get_performance_metrics();

  -- 存储检查
  RETURN QUERY
  SELECT 'storage'::text, 'table_sizes'::text, 'INFO'::text,
         format('Total size: %s', pg_size_pretty(sum(pg_total_relation_size(schemaname||'.'||relname))))
  FROM pg_stat_user_tables
  WHERE relname LIKE 'fact_measurements%';
END;
$$ LANGUAGE plpgsql;

COMMIT;

-- 添加函数注释
COMMENT ON FUNCTION safe_upsert_measurement IS '安全的UPSERT函数，避免并发冲突';
COMMENT ON FUNCTION check_data_consistency IS '检查数据一致性，发现重复记录和外键问题';
COMMENT ON FUNCTION get_performance_metrics IS '获取关键性能指标';
COMMENT ON FUNCTION smart_vacuum_strategy IS '智能VACUUM策略，根据死元组比例自动调整';
COMMENT ON FUNCTION auto_space_reclaim IS '自动空间回收，识别需要VACUUM FULL的分区';
COMMENT ON FUNCTION database_health_check IS '综合数据库健康检查';

-- 使用示例
/*
-- 执行健康检查
SELECT * FROM database_health_check();

-- 检查性能指标
SELECT * FROM get_performance_metrics();

-- 执行智能VACUUM
SELECT smart_vacuum_strategy();

-- 检查数据一致性
SELECT * FROM check_data_consistency();

-- 查看存储状态
SELECT * FROM v_storage_monitoring;
*/
