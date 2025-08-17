-- Phase 1: 立即优化（安全可回滚）
-- 注意：本脚本不包含 BEGIN/COMMIT，以便允许 CONCURRENTLY。
-- 使用示例：
--   psql -h <host> -U <user> -d pump_station_optimization -f scripts/phase1_optimization.sql

\echo '==[1/3] 调整存储参数（fact_measurements）=='
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema='public' AND table_name='fact_measurements'
  ) THEN
    EXECUTE $$ALTER TABLE public.fact_measurements SET (
      fillfactor = 70,
      autovacuum_vacuum_scale_factor = 0.05,
      autovacuum_analyze_scale_factor = 0.02,
      autovacuum_vacuum_cost_delay = 5,
      autovacuum_vacuum_cost_limit = 2000,
      autovacuum_vacuum_threshold = 1000
    )$$;
  ELSE
    RAISE NOTICE '表 public.fact_measurements 不存在，跳过存储参数调整';
  END IF;
END$$;

\echo '==[2/3] 索引策略：活跃数据部分索引 + 历史数据BRIN索引 =='
-- 活跃数据（最近7天）部分索引（避免锁表，使用 CONCURRENTLY）
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fm_recent_active
ON public.fact_measurements (station_id, device_id, metric_id, ts_bucket)
WHERE ts_bucket >= now() - interval '7 days'
WITH (fillfactor = 70);

-- 历史数据（7天前）BRIN索引（极轻量）
CREATE INDEX IF NOT EXISTS idx_fm_historical_brin
ON public.fact_measurements USING BRIN (ts_bucket)
WHERE ts_bucket < now() - interval '7 days';

-- 主查询覆盖索引（减少回表）。提示：CONCURRENTLY 可能较慢，但不中断写入。
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fm_optimized
ON public.fact_measurements (station_id, ts_bucket, device_id, metric_id)
INCLUDE (value, source_hint)
WITH (fillfactor = 70);

\echo '==[3/3] 部署监控/一致性/维护函数与视图 =='
\i scripts/crud_optimization_functions.sql

\echo '== 验证：健康检查与关键指标 =='
\echo '— 数据一致性问题（近1小时）'
SELECT * FROM check_data_consistency() LIMIT 20;

\echo '— 关键性能指标（若无 pg_stat_statements 可忽略该项）'
SELECT * FROM get_performance_metrics();

\echo '— 存储监控（按大小倒序）'
SELECT * FROM v_storage_monitoring LIMIT 20;
