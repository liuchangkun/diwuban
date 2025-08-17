-- 查询改写样例：优先命中物化视图的看板查询接口
SET client_encoding = 'UTF8';
SET client_min_messages = WARNING;

CREATE SCHEMA IF NOT EXISTS reporting;

-- 统一视图：选择小时或天聚合（示例：天聚合）
CREATE OR REPLACE VIEW reporting.v_metrics_daily AS
SELECT station_id, device_id, metric_id, ts_day AS ts, cnt, avg_value, min_value, max_value, sum_value
FROM reporting.mv_measurements_daily;

-- 查询函数：根据粒度选择来源（示例用日粒度；若需小时，可写另一函数）
CREATE OR REPLACE FUNCTION reporting.get_metrics_daily(
  p_station_id bigint,
  p_start_date date,
  p_end_date   date,
  p_metric_ids bigint[] DEFAULT NULL
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
  SELECT station_id, device_id, metric_id, ts::date, cnt, avg_value, min_value, max_value, sum_value
  FROM reporting.v_metrics_daily
  WHERE station_id = p_station_id
    AND ts >= p_start_date
    AND ts <= p_end_date
    AND (p_metric_ids IS NULL OR metric_id = ANY(p_metric_ids))
  ORDER BY ts, device_id, metric_id;
END;
$$ LANGUAGE plpgsql STABLE;
