\encoding UTF8
SET client_encoding = 'UTF8';

/*
函数名称: fn_running_state_1s
函数用途: 从 device_running_thresholds 读取阈值，按秒输出 is_running（on/off 滞回 + 缺报延续）。
创建时间: 2025-09-03
*/

CREATE OR REPLACE FUNCTION public.fn_running_state_1s(
  p_station_id  bigint,
  p_device_id   bigint,
  p_start_ts    timestamptz,
  p_end_ts      timestamptz
)
RETURNS TABLE (
  ts_bucket  timestamptz,
  is_running boolean,
  max_i      double precision,
  p          double precision,
  f          double precision,
  source     text
)
LANGUAGE plpgsql
STABLE
AS $fn$
DECLARE
  v_ei boolean; v_ep boolean; v_ef boolean;
  v_i_on double precision; v_i_off double precision;
  v_p_on double precision; v_p_off double precision;
  v_f_on double precision; v_f_off double precision;
  v_grace integer;
  v_state boolean := NULL;
  v_hold integer := 0;
  r_ts timestamptz; r_max_i double precision; r_p double precision; r_f double precision; r_has_any boolean;
BEGIN
  SELECT COALESCE(enable_i,false), COALESCE(enable_p,false), COALESCE(enable_f,false),
         i_on, i_off, p_on, p_off, f_on, f_off,
         grace_hold_secs
    INTO v_ei, v_ep, v_ef,
         v_i_on, v_i_off, v_p_on, v_p_off, v_f_on, v_f_off,
         v_grace
  FROM public.device_running_thresholds
  WHERE device_id = p_device_id;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'fn_running_state_1s: 未找到 device_id=% 的阈值配置', p_device_id;
  END IF;

  FOR r_ts, r_max_i, r_p, r_f, r_has_any IN
    WITH series AS (
      SELECT generate_series(p_start_ts, p_end_ts - interval '1 second', interval '1 second') AS ts
    ), raw AS (
      SELECT fm.ts_bucket, mc.metric_key, fm.value::double precision AS val
      FROM public.fact_measurements fm
      JOIN public.dim_metric_config mc ON mc.id = fm.metric_id
      WHERE fm.station_id = p_station_id
        AND fm.device_id  = p_device_id
        AND fm.ts_bucket >= p_start_ts AND fm.ts_bucket < p_end_ts
        AND mc.metric_key IN ('pump_current_a','pump_current_b','pump_current_c','pump_active_power','pump_frequency')
    ), cur0 AS (
      SELECT r.ts_bucket AS ts_bucket,
             MAX(r.val) FILTER (WHERE r.metric_key='pump_current_a') AS ia,
             MAX(r.val) FILTER (WHERE r.metric_key='pump_current_b') AS ib,
             MAX(r.val) FILTER (WHERE r.metric_key='pump_current_c') AS ic,
             MAX(r.val) FILTER (WHERE r.metric_key='pump_active_power') AS p,
             MAX(r.val) FILTER (WHERE r.metric_key='pump_frequency')    AS f
      FROM raw r GROUP BY r.ts_bucket
    ), cur AS (
      SELECT s.ts AS ts_bucket,
             GREATEST(COALESCE(c0.ia,0), COALESCE(c0.ib,0), COALESCE(c0.ic,0)) AS max_i,
             COALESCE(c0.p,0) AS p,
             COALESCE(c0.f,0) AS f,
             (c0.ts_bucket IS NOT NULL) AS has_any
      FROM series s
      LEFT JOIN cur0 c0 ON c0.ts_bucket = s.ts
      ORDER BY s.ts
    )
    SELECT c.ts_bucket, c.max_i, c.p, c.f, c.has_any FROM cur c
  LOOP
    IF v_state IS NULL THEN
      v_state := ( (v_ei AND r_max_i >= v_i_on)
                OR (v_ep AND r_p     >= v_p_on)
                OR (v_ef AND r_f     >= v_f_on) );
      v_hold := 0;
      ts_bucket := r_ts; is_running := v_state; max_i := r_max_i; p := r_p; f := r_f;
      source := CASE WHEN NOT r_has_any AND v_grace > 0 THEN 'hold' ELSE 'det' END;
      RETURN NEXT;
      CONTINUE;
    END IF;

    IF r_has_any THEN
      v_hold := 0;
      IF v_state THEN
        IF ( (NOT v_ei OR r_max_i <= v_i_off)
             AND (NOT v_ep OR r_p <= v_p_off)
             AND (NOT v_ef OR r_f <= v_f_off) ) THEN
          v_state := false;
        END IF;
      ELSE
        IF ( (v_ei AND r_max_i >= v_i_on)
             OR (v_ep AND r_p >= v_p_on)
             OR (v_ef AND r_f >= v_f_on) ) THEN
          v_state := true;
        END IF;
      END IF;
      ts_bucket := r_ts; is_running := v_state; max_i := r_max_i; p := r_p; f := r_f; source := 'det';
      RETURN NEXT;
    ELSE
      IF v_grace > 0 THEN
        IF v_hold < v_grace THEN v_hold := v_hold + 1; END IF;
        ts_bucket := r_ts; is_running := v_state; max_i := r_max_i; p := r_p; f := r_f; source := 'hold';
        RETURN NEXT;
      ELSE
        ts_bucket := r_ts; is_running := v_state; max_i := r_max_i; p := r_p; f := r_f; source := 'det';
        RETURN NEXT;
      END IF;
    END IF;
  END LOOP;
END;
$fn$;

