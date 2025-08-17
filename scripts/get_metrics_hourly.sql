-- 小时级查询函数：优先命中 MV
SET client_encoding = 'UTF8';
SET client_min_messages = WARNING;

CREATE SCHEMA IF NOT EXISTS reporting;

CREATE OR REPLACE FUNCTION reporting.get_metrics_hourly(
  p_station_id bigint,
  p_start_ts   timestamptz,
  p_end_ts     timestamptz,
  p_metric_ids bigint[] DEFAULT NULL
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
  WHERE station_id = p_station_id
    AND ts_hour >= date_trunc('hour', p_start_ts)
    AND ts_hour <= date_trunc('hour', p_end_ts)
    AND (p_metric_ids IS NULL OR metric_id = ANY(p_metric_ids))
  ORDER BY ts_hour, device_id, metric_id;
END;
$$ LANGUAGE plpgsql STABLE;
