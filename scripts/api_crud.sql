-- API 层 CRUD 便捷函数（基于 fact_measurements 与现有 safe_upsert）
SET client_encoding = 'UTF8';
SET client_min_messages = WARNING;

CREATE SCHEMA IF NOT EXISTS api;
SET search_path = public;

-- 1) 查询：按多维过滤与时间范围分页查询原始明细
CREATE OR REPLACE FUNCTION api.get_measurements(
  p_station_ids bigint[],           -- 必填：限制站点集合以启用分区剪枝
  p_start_ts   timestamptz,         -- 必填：时间范围起
  p_end_ts     timestamptz,         -- 必填：时间范围止
  p_device_ids bigint[] DEFAULT NULL,
  p_metric_ids bigint[] DEFAULT NULL,
  p_limit      int      DEFAULT 1000,
  p_offset     int      DEFAULT 0
) RETURNS TABLE(
  station_id bigint,
  device_id bigint,
  metric_id bigint,
  ts_raw timestamptz,
  ts_bucket timestamptz,
  value numeric,
  source_hint text,
  inserted_at timestamptz
) AS $$
BEGIN
  RETURN QUERY
  SELECT fm.station_id, fm.device_id, fm.metric_id, fm.ts_raw, fm.ts_bucket, fm.value, fm.source_hint, fm.inserted_at
  FROM fact_measurements fm
  WHERE fm.station_id = ANY(p_station_ids)
    AND fm.ts_bucket BETWEEN p_start_ts AND p_end_ts
    AND (p_device_ids IS NULL OR fm.device_id = ANY(p_device_ids))
    AND (p_metric_ids IS NULL OR fm.metric_id = ANY(p_metric_ids))
  ORDER BY fm.ts_bucket, fm.station_id, fm.device_id, fm.metric_id
  LIMIT p_limit OFFSET p_offset;
END;
$$ LANGUAGE plpgsql STABLE;

-- 2) 单条插入/更新（包装 safe_upsert_measurement）
CREATE OR REPLACE FUNCTION api.upsert_measurement(
  p_station_id bigint,
  p_device_id  bigint,
  p_metric_id  bigint,
  p_ts_raw     timestamptz,
  p_value      numeric,
  p_source_hint text DEFAULT NULL
) RETURNS boolean AS $$
BEGIN
  RETURN safe_upsert_measurement(p_station_id, p_device_id, p_metric_id, p_ts_raw, p_value, p_source_hint);
END;
$$ LANGUAGE plpgsql;

-- 3) 批量 UPSERT（JSONB 数组） [{station_id,device_id,metric_id,ts_raw,value,source_hint}]
CREATE OR REPLACE FUNCTION api.upsert_measurements_json(p_rows jsonb)
RETURNS TABLE(processed int, succeeded int, failed int) AS $$
DECLARE
  r jsonb;
  ok boolean;
  cnt_total int := 0;
  cnt_ok int := 0;
  cnt_fail int := 0;
BEGIN
  IF jsonb_typeof(p_rows) <> 'array' THEN
    RAISE EXCEPTION 'p_rows 必须是 JSON 数组';
  END IF;

  FOR r IN SELECT jsonb_array_elements(p_rows)
  LOOP
    cnt_total := cnt_total + 1;
    BEGIN
      ok := api.upsert_measurement(
        (r->>'station_id')::bigint,
        (r->>'device_id')::bigint,
        (r->>'metric_id')::bigint,
        (r->>'ts_raw')::timestamptz,
        (r->>'value')::numeric,
        r->>'source_hint'
      );
      IF ok THEN cnt_ok := cnt_ok + 1; END IF;
    EXCEPTION WHEN OTHERS THEN
      cnt_fail := cnt_fail + 1;
    END;
  END LOOP;
  RETURN QUERY SELECT cnt_total, cnt_ok, cnt_fail;
END;
$$ LANGUAGE plpgsql;

-- 4) 单条更新（按PK定位）
CREATE OR REPLACE FUNCTION api.update_measurement_value(
  p_station_id bigint,
  p_device_id  bigint,
  p_metric_id  bigint,
  p_ts_raw     timestamptz,  -- 将被截断到秒作为 ts_bucket
  p_new_value  numeric,
  p_source_hint text DEFAULT NULL
) RETURNS integer AS $$
DECLARE
  v_ts_bucket timestamptz;
  affected int;
BEGIN
  v_ts_bucket := date_trunc('second', p_ts_raw);
  UPDATE fact_measurements
    SET value = p_new_value,
        source_hint = COALESCE(p_source_hint, source_hint),
        inserted_at = now()
  WHERE station_id = p_station_id AND device_id = p_device_id AND metric_id = p_metric_id AND ts_bucket = v_ts_bucket;
  GET DIAGNOSTICS affected = ROW_COUNT;
  RETURN affected;
END;
$$ LANGUAGE plpgsql;

-- 5) 批量删除（按多维过滤 + 时间范围，分批，避免长时间锁）
CREATE OR REPLACE FUNCTION api.delete_measurements_by_filter(
  p_station_ids bigint[],
  p_start_ts   timestamptz,
  p_end_ts     timestamptz,
  p_device_ids bigint[] DEFAULT NULL,
  p_metric_ids bigint[] DEFAULT NULL,
  p_batch_size int      DEFAULT 5000
) RETURNS TABLE(total_deleted int) AS $$
DECLARE
  deleted_once int;
  total int := 0;
BEGIN
  LOOP
    WITH c AS (
      SELECT ctid FROM fact_measurements
      WHERE station_id = ANY(p_station_ids)
        AND ts_bucket BETWEEN p_start_ts AND p_end_ts
        AND (p_device_ids IS NULL OR device_id = ANY(p_device_ids))
        AND (p_metric_ids IS NULL OR metric_id = ANY(p_metric_ids))
      LIMIT p_batch_size
    )
    DELETE FROM fact_measurements fm USING c
    WHERE fm.ctid = c.ctid;

    GET DIAGNOSTICS deleted_once = ROW_COUNT;
    total := total + deleted_once;
    EXIT WHEN deleted_once = 0;
    PERFORM pg_sleep(0.05);
  END LOOP;
  RETURN QUERY SELECT total;
END;
$$ LANGUAGE plpgsql;

-- 6) 单条删除（按PK）
CREATE OR REPLACE FUNCTION api.delete_measurement(
  p_station_id bigint,
  p_device_id  bigint,
  p_metric_id  bigint,
  p_ts_raw     timestamptz
) RETURNS integer AS $$
DECLARE
  v_ts_bucket timestamptz := date_trunc('second', p_ts_raw);
  affected int;
BEGIN
  DELETE FROM fact_measurements
  WHERE station_id = p_station_id AND device_id = p_device_id AND metric_id = p_metric_id AND ts_bucket = v_ts_bucket;
  GET DIAGNOSTICS affected = ROW_COUNT;
  RETURN affected;
END;
$$ LANGUAGE plpgsql;
