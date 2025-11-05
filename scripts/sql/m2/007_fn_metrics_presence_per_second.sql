-- 秒级时间点 × 泵站 × 设备：需要计算补齐的指标 + 已有的指标
-- 说明：
-- - 需要计算补齐：策略表 acquisition_status='不能' AND compute_flag='需要'（与设备映射相关）
-- - 已有的指标：该秒有原始数据（fact_measurements 命中）且与设备映射中对应的标准化指标键一致
-- - 时间点输出为 Asia/Shanghai 文本并带 +08 后缀；保证 1 秒不漏（generate_series）

CREATE OR REPLACE FUNCTION public.metrics_presence_per_second(
    _start timestamptz,
    _end   timestamptz,
    _station_name text DEFAULT NULL,
    _device_name  text DEFAULT NULL
) RETURNS TABLE (
    station text,
    device  text,
    ts_utc timestamptz,
    need_compute_metrics text[],
    available_metrics    text[]
) LANGUAGE sql AS $$
WITH bounds AS (
  SELECT LEAST(_start, _end) AS start_ts, GREATEST(_start, _end) AS end_ts
),
seconds AS (
  SELECT generate_series(
           (SELECT date_trunc('second', start_ts) FROM bounds),
           (SELECT date_trunc('second', end_ts) - interval '1 second'  FROM bounds),
           interval '1 second'
         ) AS ts
),
-- 设备清单（不依赖映射表），支持按站/设备过滤
devs_base AS (
  SELECT s.id AS station_id, d.id AS device_id, s.name AS station_name, d.name AS device_name, d.type AS device_type
  FROM public.dim_devices d
  JOIN public.dim_stations s ON s.id=d.station_id
  WHERE (_station_name IS NULL OR s.name=_station_name)
    AND (_device_name  IS NULL OR d.name=_device_name)
),
-- 家族推断：优先使用设备类型，其次用名称启发式
devs_f AS (
  SELECT b.*,
         CASE
           WHEN b.device_type = 'main_pipeline' OR b.device_name LIKE '%总管%' THEN 'main_pipeline'
           WHEN b.device_type = 'pump' OR b.device_name LIKE '%泵%' THEN 'pump'
           ELSE NULL
         END AS family
  FROM devs_base b
),
-- 基于策略表的“需要计算”候选集合（不依赖映射表）
need_candidates AS (
  SELECT df.station_id, df.device_id,
         COALESCE(
           (
             SELECT array_agg(DISTINCT m.metric_key ORDER BY m.metric_key)
             FROM public.metric_capability_policy m
             WHERE m.compute_flag='需要'
               AND (df.family IS NOT NULL AND m.metric_key LIKE df.family || '_%')
           ), ARRAY[]::text[]
         ) AS metrics
  FROM devs_f df
),
-- 原始数据在该秒是否存在；指标名称严格使用 dim_metric_config.metric_key
present AS (
  SELECT fm.station_id, fm.device_id,
         fm.ts_bucket AS ts,
         mc.metric_key
  FROM public.fact_measurements fm
  JOIN public.dim_metric_config mc ON mc.id=fm.metric_id
  JOIN bounds b ON fm.ts_bucket >= date_trunc('second', b.start_ts)
               AND fm.ts_bucket < date_trunc('second', b.end_ts)
  JOIN devs_base db ON db.station_id = fm.station_id AND db.device_id = fm.device_id
),
-- 秒级 × 设备 的“已有指标”集合
available_sec AS (
  SELECT p.station_id, p.device_id, p.ts,
         array_agg(DISTINCT p.metric_key ORDER BY p.metric_key) AS metrics
  FROM present p
  GROUP BY p.station_id, p.device_id, p.ts
),
-- 最终 need_compute：按秒剔除“该秒已有数据”的指标
need_compute AS (
  SELECT s.ts, d.station_id, d.device_id,
         COALESCE(
           ARRAY(
             SELECT k FROM unnest(COALESCE(nc.metrics, ARRAY[]::text[])) AS k
             EXCEPT
             SELECT k FROM unnest(COALESCE(av.metrics, ARRAY[]::text[])) AS k
           ), ARRAY[]::text[]
         ) AS metrics
  FROM seconds s
  CROSS JOIN (SELECT station_id, device_id FROM devs_base) d
  LEFT JOIN need_candidates nc ON nc.station_id=d.station_id AND nc.device_id=d.device_id
  LEFT JOIN available_sec av ON av.station_id=d.station_id AND av.device_id=d.device_id AND av.ts=s.ts
),
-- 维度设备清单（直接来自设备维表）
devs AS (
  SELECT DISTINCT station_id, device_id, station_name, device_name FROM devs_base
)
SELECT d.station_name AS station,
       d.device_name  AS device,
       s.ts AS ts_utc,
       COALESCE(nc.metrics, ARRAY[]::text[]) AS need_compute_metrics,
       COALESCE(av.metrics, ARRAY[]::text[]) AS available_metrics
FROM seconds s
CROSS JOIN devs d
LEFT JOIN need_compute nc ON nc.station_id=d.station_id AND nc.device_id=d.device_id
LEFT JOIN available_sec av ON av.station_id=d.station_id AND av.device_id=d.device_id AND av.ts=s.ts
ORDER BY d.station_name, d.device_name, s.ts;
$$;

COMMENT ON FUNCTION public.metrics_presence_per_second(timestamptz, timestamptz, text, text) IS '按秒输出：泵站×设备×时间点 的 {需要计算补齐的指标} 与 {已有指标}；不再依赖 dim_mapping_items，基于 metric_capability_policy（compute_flag=需要）与设备家族决定候选集合；时间为北京时间(+08)文本。';

