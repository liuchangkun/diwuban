-- 多维过滤查询函数：优先命中 MV（小时/天）
SET client_encoding = 'UTF8';
SET client_min_messages = WARNING;

CREATE SCHEMA IF NOT EXISTS reporting;

-- 天级多维过滤
CREATE OR REPLACE FUNCTION reporting.get_metrics_daily_multi(
  p_station_ids bigint[],
  p_start_date  date,
  p_end_date    date,
  p_device_ids  bigint[] DEFAULT NULL,
  p_metric_ids  bigint[] DEFAULT NULL
) RETURNS TABLE(
  station_id bigint,
  device_id bigint,
  metric_id bigint,
  ts date,
  cnt bigint,
  avg_value double precision,
  min_value double precision,
  max_value double precision,
  sum_value double precision
) AS $$
BEGIN
  RETURN QUERY
  SELECT station_id, device_id, metric_id, ts_day::date AS ts, cnt, avg_value, min_value, max_value, sum_value
  FROM reporting.mv_measurements_daily
  WHERE station_id = ANY(p_station_ids)
    AND (p_device_ids IS NULL OR device_id = ANY(p_device_ids))
    AND (p_metric_ids IS NULL OR metric_id = ANY(p_metric_ids))
    AND ts_day >= p_start_date
    AND ts_day <= p_end_date
  ORDER BY ts, station_id, device_id, metric_id;
END;
$$ LANGUAGE plpgsql STABLE;

-- 小时级多维过滤
CREATE OR REPLACE FUNCTION reporting.get_metrics_hourly_multi(
  p_station_ids bigint[],
  p_start_ts    timestamptz,
  p_end_ts      timestamptz,
  p_device_ids  bigint[] DEFAULT NULL,
  p_metric_ids  bigint[] DEFAULT NULL
) RETURNS TABLE(
  station_id bigint,
  device_id bigint,
  metric_id bigint,
  ts_hour timestamptz,
  cnt bigint,
  avg_value double precision,
  min_value double precision,
  max_value double precision,
  sum_value double precision
) AS $$
BEGIN
  RETURN QUERY
  SELECT station_id, device_id, metric_id, ts_hour, cnt, avg_value, min_value, max_value, sum_value
  FROM reporting.mv_measurements_hourly
  WHERE station_id = ANY(p_station_ids)
    AND (p_device_ids IS NULL OR device_id = ANY(p_device_ids))
    AND (p_metric_ids IS NULL OR metric_id = ANY(p_metric_ids))
    AND ts_hour >= date_trunc('hour', p_start_ts)
    AND ts_hour <= date_trunc('hour', p_end_ts)
  ORDER BY ts_hour, station_id, device_id, metric_id;
END;
$$ LANGUAGE plpgsql STABLE;
