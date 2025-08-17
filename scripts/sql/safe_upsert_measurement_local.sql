-- safe_upsert_measurement_local.sql
-- 目的：提供“本地时间 + 站点时区”写入的安全 UPSERT 接口
-- 约定：
-- - 入参 ts_local 为不带时区的 timestamp（来源 CSV 或本地系统时间）
-- - 依据 dim_stations.tz 映射将 ts_local 转为 UTC，并对齐到整秒作为 ts_bucket
-- - 与 safe_upsert_measurement 的逻辑保持一致：同一主键（秒）冲突时进行合并/更新

CREATE OR REPLACE FUNCTION public.safe_upsert_measurement_local(
  p_station_id bigint,
  p_device_id  bigint,
  p_metric_id  bigint,
  p_ts_local   timestamp,
  p_value      numeric,
  p_source_hint text DEFAULT NULL
) RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE
  v_tz text;
  v_ts_utc timestamptz;
  v_ts_bucket timestamptz;
BEGIN
  -- 1) 读取站点时区（若无则默认 UTC）
  SELECT COALESCE(s.tz, 'UTC') INTO v_tz
  FROM public.dim_stations s
  WHERE s.station_id = p_station_id;

  -- 2) 本地时间按站点时区转为 UTC
  --    注意：timestamp AT TIME ZONE 'zone' 结果为 timestamptz（以 UTC 表示该本地时间）
  v_ts_utc := (p_ts_local AT TIME ZONE v_tz);

  -- 3) 对齐到整秒
  v_ts_bucket := date_trunc('second', v_ts_utc);

  -- 4) 调用已有 upsert 逻辑（若已有 safe_upsert_measurement 实现，则重用）
  RETURN public.safe_upsert_measurement(
    p_station_id,
    p_device_id,
    p_metric_id,
    v_ts_bucket,
    p_value,
    p_source_hint
  );
EXCEPTION WHEN OTHERS THEN
  -- 与现有实现一致：异常返回 false，避免长事务
  RETURN false;
END;
$$;
