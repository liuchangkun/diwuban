\encoding UTF8
SET client_encoding = 'UTF8';

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
LANGUAGE sql
STABLE
AS $fn$
WITH thr AS (
  SELECT * FROM public.device_running_thresholds t WHERE t.device_id = p_device_id
),
series AS (
  SELECT generate_series(p_start_ts, p_end_ts - interval '1 second', interval '1 second')::timestamptz AS ts, row_number() over () AS rn
),
raw AS (
  SELECT fm.ts_bucket, mc.metric_key, fm.value::double precision AS val
  FROM public.fact_measurements fm
  JOIN public.dim_metric_config mc ON mc.id = fm.metric_id
  WHERE fm.station_id = p_station_id
    AND fm.device_id  = p_device_id
    AND fm.ts_bucket >= p_start_ts AND fm.ts_bucket < p_end_ts
    AND mc.metric_key IN ('pump_current_a','pump_current_b','pump_current_c','pump_active_power','pump_frequency')
),
cur0 AS (
  SELECT ts_bucket,
         MAX(val) FILTER (WHERE metric_key='pump_current_a') AS ia,
         MAX(val) FILTER (WHERE metric_key='pump_current_b') AS ib,
         MAX(val) FILTER (WHERE metric_key='pump_current_c') AS ic,
         MAX(val) FILTER (WHERE metric_key='pump_active_power') AS p,
         MAX(val) FILTER (WHERE metric_key='pump_frequency')    AS f
  FROM raw
  GROUP BY ts_bucket
),
cur AS (
  SELECT ts_bucket,
         GREATEST(COALESCE(ia,0), COALESCE(ib,0), COALESCE(ic,0)) AS max_i,
         COALESCE(p,0) AS p,
         COALESCE(f,0) AS f
  FROM cur0
),
joined AS (
  SELECT s.rn, s.ts AS ts_bucket, c.max_i, c.p, c.f,
         (c.ts_bucket IS NOT NULL) AS has_any
  FROM series s
  LEFT JOIN cur c ON c.ts_bucket = s.ts
),
param AS (
  SELECT
    COALESCE(enable_i, false) AS ei,
    COALESCE(enable_p, false) AS ep,
    COALESCE(enable_f, false) AS ef,
    i_on, i_off, p_on, p_off, f_on, f_off,
    grace_hold_secs
  FROM thr
),
ordered AS (
  SELECT j.rn, j.ts_bucket, j.max_i, j.p, j.f, j.has_any,
         (SELECT ei FROM param) AS ei,
         (SELECT ep FROM param) AS ep,
         (SELECT ef FROM param) AS ef,
         (SELECT i_on FROM param) AS i_on,
         (SELECT i_off FROM param) AS i_off,
         (SELECT p_on FROM param) AS p_on,
         (SELECT p_off FROM param) AS p_off,
         (SELECT f_on FROM param) AS f_on,
         (SELECT f_off FROM param) AS f_off,
         (SELECT grace_hold_secs FROM param) AS grace_hold_secs
  FROM joined j
),
det AS (
  SELECT rn, ts_bucket, max_i, p, f, has_any, ei, ep, ef, i_on, i_off, p_on, p_off, f_on, f_off, grace_hold_secs,
         ( (ei AND max_i >= i_on) OR (ep AND p >= p_on) OR (ef AND f >= f_on) ) AS on_hit,
         ( (NOT ei OR max_i <= i_off)
           AND (NOT ep OR p <= p_off)
           AND (NOT ef OR f <= f_off) ) AS off_hit
  FROM ordered
)
SELECT d1.ts_bucket,
       d1.max_i, d1.p, d1.f,
       CASE WHEN d1.rn = 1 THEN d1.on_hit
            ELSE CASE WHEN lag(state) OVER (ORDER BY d1.rn) THEN (NOT d1.off_hit)
                      ELSE d1.on_hit END
       END AS is_running,
       CASE WHEN NOT d1.has_any AND (SELECT grace_hold_secs FROM param) > 0 AND
                 (CASE WHEN d1.rn = 1 THEN 0
                       ELSE (CASE WHEN lag(d1.has_any) OVER (ORDER BY d1.rn) THEN 0 ELSE 1 END)
                  END) > 0
            THEN 'hold' ELSE 'det' END AS source
FROM (
  SELECT d.*,  -- 为便于 LAG(state) 写法，这里先假设 state = on_hit（仅用于窗口推进）
         on_hit AS state
  FROM det d
) d1
ORDER BY d1.ts_bucket;
$fn$;

