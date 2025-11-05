-- 迁移至 deprecated：原 sp_compute_device_phase 定义，仅保留存档，不再使用
-- 原路径：scripts/sql/migrations/010_create_sp_compute_device_phase.sql

-- 目的：按窗口为每台设备生成 device_phase 指标（0停止/1稳态运行/2启动中/3停止中），写入 fact_measurements
-- 用法：CALL public.sp_compute_device_phase('2025-01-01','2025-01-02', NULL);

BEGIN;

CREATE OR REPLACE PROCEDURE public.sp_compute_device_phase(
  IN p_start timestamptz,
  IN p_end   timestamptz,
  IN p_device_id bigint DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_running_metric_id bigint;
  v_phase_metric_id   bigint;
BEGIN
  SELECT id INTO v_running_metric_id FROM public.dim_metric_config WHERE metric_key='device_running';
  IF v_running_metric_id IS NULL THEN
    RAISE EXCEPTION '缺少 device_running 指标配置';
  END IF;
  SELECT id INTO v_phase_metric_id FROM public.dim_metric_config WHERE metric_key='device_phase';
  IF v_phase_metric_id IS NULL THEN
    RAISE EXCEPTION '缺少 device_phase 指标配置';
  END IF;

  -- 基于启停阈值表的窗口参数，构造启动/停止相位区间
  WITH run AS (
    SELECT f.station_id, f.device_id, f.ts_bucket, (f.value)::int AS running
    FROM public.fact_measurements f
    WHERE f.metric_id=v_running_metric_id AND f.ts_bucket >= p_start AND f.ts_bucket < p_end
      AND (p_device_id IS NULL OR f.device_id=p_device_id)
  ), edges AS (
    SELECT r.*, LAG(running) OVER (PARTITION BY station_id, device_id ORDER BY ts_bucket) AS prev
    FROM run r
  ), params AS (
    SELECT t.device_id,
           COALESCE(t.start_pre_secs,  3) AS start_pre,
           COALESCE(t.start_post_secs, 5) AS start_post,
           COALESCE(t.stop_pre_secs,   3) AS stop_pre,
           COALESCE(t.stop_post_secs,  3) AS stop_post
    FROM public.device_running_thresholds t
  ), devices AS (
    SELECT DISTINCT station_id, device_id FROM run
  ), series AS (
    SELECT d.station_id, d.device_id,
           gs AS ts_bucket
    FROM devices d
    CROSS JOIN generate_series(p_start, p_end - interval '1 second', interval '1 second') AS gs
  ), phase AS (
    SELECT s.station_id, s.device_id, s.ts_bucket,
           CASE
             WHEN EXISTS (
               SELECT 1 FROM edges up JOIN params p ON p.device_id=up.device_id
               WHERE up.station_id=s.station_id AND up.device_id=s.device_id
                 AND up.running=1 AND up.prev=0
                 AND s.ts_bucket BETWEEN up.ts_bucket - (p.start_pre||' seconds')::interval
                                      AND up.ts_bucket + (p.start_post||' seconds')::interval
             ) THEN 2
             WHEN EXISTS (
               SELECT 1 FROM edges dn JOIN params p ON p.device_id=dn.device_id
               WHERE dn.station_id=s.station_id AND dn.device_id=s.device_id
                 AND dn.running=0 AND dn.prev=1
                 AND s.ts_bucket BETWEEN dn.ts_bucket - (p.stop_pre||' seconds')::interval
                                      AND dn.ts_bucket + (p.stop_post||' seconds')::interval
             ) THEN 3
             ELSE COALESCE(r2.running, 0)
           END AS phase_code
    FROM series s
    LEFT JOIN run r2 ON r2.station_id=s.station_id AND r2.device_id=s.device_id AND r2.ts_bucket=s.ts_bucket
  )
  INSERT INTO public.fact_measurements(id, station_id, device_id, metric_id, ts_raw, ts_bucket, value, source_hint)
  SELECT
    CASE WHEN pg_get_serial_sequence('public.fact_measurements','id') IS NOT NULL THEN
      nextval(pg_get_serial_sequence('public.fact_measurements','id'))
    ELSE
      abs(('x' || substr(md5(station_id::text||'-'||device_id::text||'-'||v_phase_metric_id::text||'-'||ts_bucket::text),1,16))::bit(64)::bigint)
    END,
    station_id, device_id, v_phase_metric_id, now(), ts_bucket, phase_code::numeric, 'device_phase'
  FROM phase
  ON CONFLICT (station_id, device_id, metric_id, ts_bucket)
  DO UPDATE SET value = EXCLUDED.value, ts_raw = EXCLUDED.ts_raw, source_hint = EXCLUDED.source_hint;
END;
$$;

COMMENT ON PROCEDURE public.sp_compute_device_phase(timestamptz, timestamptz, bigint)
IS '生成设备运行相位 device_phase(0/1/2/3)：基于 device_running 边沿与阈值表的启动/停止窗口，逐秒写入 fact_measurements。';

COMMIT;

