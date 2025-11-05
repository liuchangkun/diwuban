\encoding UTF8
SET client_encoding = 'UTF8';

/*
函数名称: fn_quality_stats_1d
函数用途: 按天统计指定对象在时间窗口内的数据质量指标（覆盖率、空值、离群计数等），统一 1 秒步长与 UTC 口径。
输入参数:
  p_station_id bigint      - 站点ID
  p_device_id  bigint      - 设备ID
  p_metric_id  bigint      - 指标ID
  p_start_ts   timestamptz - 窗口起（UTC，含）
  p_end_ts     timestamptz - 窗口止（UTC，含）
返回格式:
  date_bucket    date              - 天粒度（UTC）
  total_points   bigint            - 记录条数
  null_count     bigint            - value 为 NULL 的条数
  coverage_rate  double precision  - 覆盖率（当日内有值秒数 / 当日秒数，边界天按窗口截断计算）
  outlier_count  bigint            - 离群点条数（|z|>3，按当日均值/样本标准差）
使用示例:
  SELECT * FROM public.fn_quality_stats_1d(1,1,1,'2025-09-01T00:00:00Z','2025-09-03T00:00:00Z');
创建时间: 2025-09-03
*/

CREATE OR REPLACE FUNCTION public.fn_quality_stats_1d(
  p_station_id bigint,
  p_device_id  bigint,
  p_metric_id  bigint,
  p_start_ts   timestamptz,
  p_end_ts     timestamptz
)
RETURNS TABLE (
  date_bucket   date,
  total_points  bigint,
  null_count    bigint,
  coverage_rate double precision,
  outlier_count bigint
)
LANGUAGE sql
STABLE
AS $fn$
WITH base AS (
  SELECT date_trunc('day', fm.ts_bucket)::date AS d,
         fm.ts_bucket,
         fm.value::double precision AS v
  FROM public.fact_measurements fm
  WHERE fm.station_id = p_station_id
    AND fm.device_id  = p_device_id
    AND fm.metric_id  = p_metric_id
    AND fm.ts_bucket >= p_start_ts AND fm.ts_bucket < p_end_ts
), day_bounds AS (
  /* 计算每个涉及到的日期在窗口内的有效秒数（边界天截断） */
  SELECT d::date AS d,
         GREATEST(p_start_ts, d::timestamptz) AS day_start,
         LEAST(p_end_ts,   (d::timestamptz + INTERVAL '1 day')) AS day_end,
         EXTRACT(EPOCH FROM (LEAST(p_end_ts, (d::timestamptz + INTERVAL '1 day'))
                           - GREATEST(p_start_ts, d::timestamptz)))::bigint AS day_secs
  FROM (
    SELECT DISTINCT date_trunc('day', ts_bucket)::date AS d FROM base
  ) days
), per_day AS (
  SELECT b.d,
         COUNT(*) AS total_points,
         COUNT(*) FILTER (WHERE v IS NULL) AS null_count,
         COUNT(DISTINCT b.ts_bucket) AS present_secs,
         AVG(v) FILTER (WHERE v IS NOT NULL) AS mu,
         STDDEV_SAMP(v) FILTER (WHERE v IS NOT NULL) AS sigma
  FROM base b
  GROUP BY b.d
), outliers AS (
  SELECT b.d,
         COUNT(*) FILTER (WHERE p.sigma IS NOT NULL AND p.sigma > 0 AND ABS((b.v - p.mu)/p.sigma) > 3) AS outlier_count
  FROM base b
  JOIN per_day p ON p.d = b.d
  GROUP BY b.d
)
SELECT p.d AS date_bucket,
       p.total_points,
       p.null_count,
       CASE WHEN db.day_secs IS NULL OR db.day_secs <= 0 THEN 0
            ELSE (p.present_secs::double precision / db.day_secs::double precision) END AS coverage_rate,
       COALESCE(o.outlier_count, 0) AS outlier_count
FROM per_day p
LEFT JOIN day_bounds db ON db.d = p.d
LEFT JOIN outliers o ON o.d = p.d
ORDER BY p.d;
$fn$;

COMMENT ON FUNCTION public.fn_quality_stats_1d(bigint,bigint,bigint,timestamptz,timestamptz) IS $DOC$
函数名称: fn_quality_stats_1d
函数用途: 按天统计指定对象在时间窗口内的数据质量指标（覆盖率、空值、离群计数等），统一 1 秒步长与 UTC 口径。
输入参数: p_station_id bigint; p_device_id bigint; p_metric_id bigint; p_start_ts timestamptz; p_end_ts timestamptz。
返回格式: (date_bucket date, total_points bigint, null_count bigint, coverage_rate double precision, outlier_count bigint)
使用示例: SELECT * FROM public.fn_quality_stats_1d(1,1,1,'2025-09-01T00:00:00Z','2025-09-03T00:00:00Z');
创建时间: 2025-09-03
$DOC$;

