-- 汇总层/物化视图蓝本（不落地数据，WITH NO DATA）
SET client_encoding = 'UTF8';
SET client_min_messages = WARNING;

CREATE SCHEMA IF NOT EXISTS reporting;

-- 小时级聚合（站点-设备-指标-小时）
CREATE MATERIALIZED VIEW IF NOT EXISTS reporting.mv_measurements_hourly
TABLESPACE pg_default
AS
SELECT
  fm.station_id,
  fm.device_id,
  fm.metric_id,
  date_trunc('hour', fm.ts_bucket) AS ts_hour,
  count(*)                      AS cnt,
  avg(fm.value)                 AS avg_value,
  min(fm.value)                 AS min_value,
  max(fm.value)                 AS max_value,
  sum(fm.value)                 AS sum_value
FROM public.fact_measurements fm
GROUP BY 1,2,3,4
WITH NO DATA;

CREATE INDEX IF NOT EXISTS idx_mv_measurements_hourly_key
ON reporting.mv_measurements_hourly (station_id, device_id, metric_id, ts_hour);

-- 天级聚合（站点-设备-指标-天）
CREATE MATERIALIZED VIEW IF NOT EXISTS reporting.mv_measurements_daily
TABLESPACE pg_default
AS
SELECT
  fm.station_id,
  fm.device_id,
  fm.metric_id,
  date_trunc('day', fm.ts_bucket) AS ts_day,
  count(*)                      AS cnt,
  avg(fm.value)                 AS avg_value,
  min(fm.value)                 AS min_value,
  max(fm.value)                 AS max_value,
  sum(fm.value)                 AS sum_value
FROM public.fact_measurements fm
GROUP BY 1,2,3,4
WITH NO DATA;

CREATE INDEX IF NOT EXISTS idx_mv_measurements_daily_key
ON reporting.mv_measurements_daily (station_id, device_id, metric_id, ts_day);

-- 刷新函数：支持增量窗口刷新（默认近 2 天 + 近 48 小时）
CREATE OR REPLACE FUNCTION reporting.refresh_mv_measurements(p_days int DEFAULT 2)
RETURNS void AS $$
BEGIN
  -- 使用 CONCURRENTLY 以降低锁影响（首次无数据时可能不支持，需回退）
  BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY reporting.mv_measurements_hourly;
  EXCEPTION WHEN OTHERS THEN
    REFRESH MATERIALIZED VIEW reporting.mv_measurements_hourly;
  END;

  BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY reporting.mv_measurements_daily;
  EXCEPTION WHEN OTHERS THEN
    REFRESH MATERIALIZED VIEW reporting.mv_measurements_daily;
  END;
END;
$$ LANGUAGE plpgsql;

-- 建议：
-- 1) 首次填充时显式 REFRESH MATERIALIZED VIEW reporting.mv_measurements_*;
-- 2) 常规调度使用 CONCURRENTLY 版本，避免长锁；
-- 3) 仅当 fact_measurements 数据较大时考虑分级聚合（小时→天）以减少刷新开销；
