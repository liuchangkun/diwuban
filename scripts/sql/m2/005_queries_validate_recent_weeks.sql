-- 只读验证示例：最近4/8周的缺失分类查询与分片模板

-- 最近4周：必须计算（compute_required）
SELECT * FROM public.metrics_missing_v
WHERE method_hint='compute'
  AND week_start >= date_trunc('week', now()) - interval '4 weeks'
ORDER BY station_id, device_id, metric_id, week_start;

-- 最近8周：采集缺失（missing_raw）
SELECT * FROM public.metrics_missing_v
WHERE method_hint='acquire'
  AND week_start >= date_trunc('week', now()) - interval '8 weeks'
ORDER BY station_id, device_id, metric_id, week_start;

-- 全历史周列表（用于批处理遍历）
SELECT DISTINCT date_trunc('week', ts_bucket) AS week_start
FROM public.fact_measurements
ORDER BY 1;

-- 指定周 + 指定站点子集（数组）切片示例
-- SELECT * FROM public.metrics_availability_v_weekly
-- WHERE week_start = :week_start
--   AND station_id = ANY(:station_ids);

