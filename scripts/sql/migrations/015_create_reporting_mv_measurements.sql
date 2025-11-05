BEGIN;

-- 小时级物化视图：reporting.mv_measurements_hourly
CREATE SCHEMA IF NOT EXISTS reporting;

CREATE MATERIALIZED VIEW IF NOT EXISTS reporting.mv_measurements_hourly AS
SELECT
  fm.station_id,
  fm.device_id,
  fm.metric_id,
  date_trunc('hour', fm.ts_bucket) AS ts_hour,
  COUNT(*)::bigint AS cnt,
  AVG(fm.value)::double precision AS avg_value,
  MIN(fm.value)::double precision AS min_value,
  MAX(fm.value)::double precision AS max_value,
  SUM(fm.value)::double precision AS sum_value
FROM public.fact_measurements fm
GROUP BY 1,2,3,4
WITH NO DATA;

CREATE INDEX IF NOT EXISTS idx_mv_hourly_station_device_metric_ts
ON reporting.mv_measurements_hourly (station_id, device_id, metric_id, ts_hour);

-- 日级物化视图：reporting.mv_measurements_daily
CREATE MATERIALIZED VIEW IF NOT EXISTS reporting.mv_measurements_daily AS
SELECT
  fm.station_id,
  fm.device_id,
  fm.metric_id,
  date_trunc('day', fm.ts_bucket) AS ts,
  COUNT(*)::bigint AS cnt,
  AVG(fm.value)::double precision AS avg_value,
  MIN(fm.value)::double precision AS min_value,
  MAX(fm.value)::double precision AS max_value,
  SUM(fm.value)::double precision AS sum_value
FROM public.fact_measurements fm
GROUP BY 1,2,3,4
WITH NO DATA;

CREATE INDEX IF NOT EXISTS idx_mv_daily_station_device_metric_ts
ON reporting.mv_measurements_daily (station_id, device_id, metric_id, ts);

COMMIT;

-- 初次刷新（全量）
REFRESH MATERIALIZED VIEW reporting.mv_measurements_hourly;
REFRESH MATERIALIZED VIEW reporting.mv_measurements_daily;

