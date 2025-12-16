-- V2-4 phase 2: targeted indexes for 602 rule fast-paths
-- Note: executed in a single transaction by scripts/dev/apply_sql_file.py (no CONCURRENTLY)

-- 1) Auto-baseline lookup (LATERAL) prioritizes device>station>default and latest computed_at
CREATE INDEX IF NOT EXISTS idx_bl_m_d_s_ca
ON public.metric_rule_auto_baseline (metric_id, device_id, station_id, computed_at DESC);

-- Optional fast-path for default baseline rows
CREATE INDEX IF NOT EXISTS idx_bl_m_nullnull_ca
ON public.metric_rule_auto_baseline (metric_id, computed_at DESC)
WHERE device_id IS NULL AND station_id IS NULL;

-- 2) Quality rules remark lookup (LATERAL) with same specificity priority
CREATE INDEX IF NOT EXISTS idx_mqr_m_d_s
ON public.metric_quality_rules (metric_id, device_id, station_id);

-- 3) Device running seconds aggregation, frequent filter running=1
CREATE INDEX IF NOT EXISTS idx_run_sd_t_running
ON public.mv_device_running_1s (station_id, device_id, ts_bucket)
WHERE running = 1;

