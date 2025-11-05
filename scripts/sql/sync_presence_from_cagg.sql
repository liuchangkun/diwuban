-- Sync presence into public.metrics_presence_per_second_device (no CAgg/table deps)
-- Parameters order (psycopg execute): [1]: start, [2]: end, [3]: station_id (bigint or NULL), [4]: device_id (bigint or NULL)
-- Semantics: [start, end) half-open

WITH bounds AS (
  SELECT %s::timestamptz AS s, %s::timestamptz AS e, %s::bigint AS station_id, %s::bigint AS device_id
), seconds AS (
  SELECT generate_series((SELECT s FROM bounds), (SELECT e FROM bounds) - interval '1 second', interval '1 second') AS ts
), devs_base AS (
  SELECT d.id AS device_id, s.id AS station_id, d.name AS device_name, s.name AS station_name, d.type AS device_type
  FROM public.dim_devices d
  JOIN public.dim_stations s ON s.id = d.station_id
  WHERE ((SELECT station_id FROM bounds) IS NULL OR s.id = (SELECT station_id FROM bounds))
    AND ((SELECT device_id FROM bounds) IS NULL OR d.id = (SELECT device_id FROM bounds))
    AND COALESCE(d.is_active, TRUE) = TRUE
    AND COALESCE(NULLIF(d.type,''),'') NOT IN ('clear_water_pool','other')
), devs_f AS (
  SELECT b.*,
         CASE
           WHEN b.device_type = 'main_pipeline' OR POSITION('总管' IN b.device_name) > 0 THEN 'main_pipeline'
           WHEN b.device_type = 'pump' OR POSITION('泵' IN b.device_name) > 0 THEN 'pump'
           ELSE NULL
         END AS family
  FROM devs_base b
), grid AS (
  SELECT d.station_id, d.device_id, sec.ts AS ts_second
  FROM devs_f d CROSS JOIN seconds sec
), present AS (
  SELECT fm.station_id, fm.device_id, fm.ts_bucket AS ts, mc.metric_key
  FROM public.fact_measurements fm
  JOIN public.dim_metric_config mc ON mc.id = fm.metric_id
  WHERE fm.ts_bucket >= (SELECT s FROM bounds) AND fm.ts_bucket < (SELECT e FROM bounds)
), available_sec AS (
  SELECT p.station_id, p.device_id, p.ts AS ts_second,
         array_agg(DISTINCT p.metric_key ORDER BY p.metric_key) AS available_metrics
  FROM present p
  GROUP BY p.station_id, p.device_id, p.ts
), need_candidates AS (
  SELECT df.station_id, df.device_id,
         COALESCE(
           (
             SELECT array_agg(DISTINCT m.metric_key ORDER BY m.metric_key)
             FROM public.metric_capability_policy m
             WHERE m.compute_flag = '需要'
               AND (df.family IS NOT NULL AND LEFT(m.metric_key, length(df.family)+1) = df.family || '_')
           ), ARRAY[]::text[]
         ) AS metrics
  FROM devs_f df
)
INSERT INTO public.metrics_presence_per_second_device
(station_id, device_id, ts_second, available_metrics, need_compute_metrics)
SELECT g.station_id,
       g.device_id,
       g.ts_second,
       COALESCE(av.available_metrics, ARRAY[]::text[]) AS available_metrics,
       COALESCE(ARRAY(SELECT k FROM unnest(COALESCE(nc.metrics, ARRAY[]::text[])) AS k
                      EXCEPT SELECT k FROM unnest(COALESCE(av.available_metrics, ARRAY[]::text[])) AS k), ARRAY[]::text[]) AS need_compute_metrics
FROM grid g
LEFT JOIN available_sec av ON av.station_id=g.station_id AND av.device_id=g.device_id AND av.ts_second=g.ts_second
LEFT JOIN need_candidates nc ON nc.station_id=g.station_id AND nc.device_id=g.device_id
ON CONFLICT (station_id, device_id, ts_second) DO UPDATE
SET available_metrics = EXCLUDED.available_metrics,
    need_compute_metrics = EXCLUDED.need_compute_metrics
WHERE public.metrics_presence_per_second_device.available_metrics IS DISTINCT FROM EXCLUDED.available_metrics
   OR public.metrics_presence_per_second_device.need_compute_metrics IS DISTINCT FROM EXCLUDED.need_compute_metrics;

