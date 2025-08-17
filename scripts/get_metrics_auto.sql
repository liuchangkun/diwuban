-- 自动粒度路由函数：根据时间跨度选择小时/天聚合
SET client_encoding = 'UTF8';
SET client_min_messages = WARNING;

CREATE SCHEMA IF NOT EXISTS reporting;

-- 单站点版本：跨度>3天用日粒度，否则用小时粒度
CREATE OR REPLACE FUNCTION reporting.get_metrics_auto(
  p_station_id bigint,
  p_start_ts   timestamptz,
  p_end_ts     timestamptz,
  p_metric_ids bigint[] DEFAULT NULL,
  p_threshold_days int  DEFAULT 3
) RETURNS TABLE(
  station_id bigint,
  device_id bigint,
  metric_id bigint,
  ts timestamptz,
  cnt bigint,
  avg_value double precision,
  min_value double precision,
  max_value double precision,
  sum_value double precision
) AS $$
BEGIN
  IF (p_end_ts - p_start_ts) > (p_threshold_days || ' days')::interval THEN
    RETURN QUERY
    SELECT station_id, device_id, metric_id, ts::timestamptz, cnt, avg_value, min_value, max_value, sum_value
    FROM reporting.get_metrics_daily(p_station_id, (p_start_ts AT TIME ZONE 'UTC')::date, (p_end_ts AT TIME ZONE 'UTC')::date, p_metric_ids);
  ELSE
    RETURN QUERY
    SELECT station_id, device_id, metric_id, ts_hour AS ts, cnt, avg_value, min_value, max_value, sum_value
    FROM reporting.get_metrics_hourly(p_station_id, p_start_ts, p_end_ts, p_metric_ids);
  END IF;
END;
$$ LANGUAGE plpgsql STABLE;

-- 多站点版本
CREATE OR REPLACE FUNCTION reporting.get_metrics_auto_multi(
  p_station_ids bigint[],
  p_start_ts    timestamptz,
  p_end_ts      timestamptz,
  p_device_ids  bigint[] DEFAULT NULL,
  p_metric_ids  bigint[] DEFAULT NULL,
  p_threshold_days int   DEFAULT 3
) RETURNS TABLE(
  station_id bigint,
  device_id bigint,
  metric_id bigint,
  ts timestamptz,
  cnt bigint,
  avg_value double precision,
  min_value double precision,
  max_value double precision,
  sum_value double precision
) AS $$
BEGIN
  IF (p_end_ts - p_start_ts) > (p_threshold_days || ' days')::interval THEN
    RETURN QUERY
    SELECT station_id, device_id, metric_id, ts::timestamptz, cnt, avg_value, min_value, max_value, sum_value
    FROM reporting.get_metrics_daily_multi(p_station_ids, (p_start_ts AT TIME ZONE 'UTC')::date, (p_end_ts AT TIME ZONE 'UTC')::date, p_device_ids, p_metric_ids);
  ELSE
    RETURN QUERY
    SELECT station_id, device_id, metric_id, ts_hour AS ts, cnt, avg_value, min_value, max_value, sum_value
    FROM reporting.get_metrics_hourly_multi(p_station_ids, p_start_ts, p_end_ts, p_device_ids, p_metric_ids);
  END IF;
END;
$$ LANGUAGE plpgsql STABLE;
