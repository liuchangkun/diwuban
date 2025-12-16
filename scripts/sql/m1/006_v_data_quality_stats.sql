\encoding UTF8
SET client_encoding = 'UTF8';

/*
视图名称: v_data_quality_stats
视图用途: 按日统计数据质量（覆盖率/空值/离群计数），统一 UTC 与 1 秒对齐口径。
数据来源: fact_measurements 聚合（可在查询侧按 station/device/metric/time 过滤）
字段映射:
  - date_bucket <- date_trunc('day', ts_bucket)::date
  - station_id <- fact_measurements.station_id
  - device_id  <- fact_measurements.device_id
  - metric_id  <- fact_measurements.metric_id
  - total_points <- count(*)
  - null_count   <- count(*) filter (value is null)
  - outlier_count<- |z|>3 计数（当日内均值/样本标准差）
  - coverage_rate<- present_secs / 86400.0（当日全秒，供全局对比；如需窗口截断，建议调用函数 fn_quality_stats_1d）
过滤逻辑: 无对象白名单；执行时建议追加 WHERE 进行裁剪，避免全表聚合
创建时间: 2025-09-03
*/

CREATE OR REPLACE VIEW public.v_data_quality_stats AS
WITH base AS (
  SELECT date_trunc('day', fm.ts_bucket)::date AS date_bucket,
         fm.station_id,
         fm.device_id,
         fm.metric_id,
         fm.ts_bucket,
         fm.value::double precision AS v
  FROM public.fact_measurements fm
), per_day AS (
  SELECT date_bucket,
         station_id,
         device_id,
         metric_id,
         COUNT(*) AS total_points,
         COUNT(*) FILTER (WHERE v IS NULL) AS null_count,
         COUNT(DISTINCT ts_bucket) AS present_secs,
         AVG(v) FILTER (WHERE v IS NOT NULL) AS mu,
         STDDEV_SAMP(v) FILTER (WHERE v IS NOT NULL) AS sigma
  FROM base
  GROUP BY date_bucket, station_id, device_id, metric_id
), outliers AS (
  SELECT b.date_bucket, b.station_id, b.device_id, b.metric_id,
         COUNT(*) FILTER (
           WHERE p.sigma IS NOT NULL AND p.sigma > 0
             AND ABS((b.v - p.mu)/p.sigma) > 3
         ) AS outlier_count
  FROM base b
  JOIN per_day p USING (date_bucket, station_id, device_id, metric_id)
  GROUP BY b.date_bucket, b.station_id, b.device_id, b.metric_id
)
SELECT p.date_bucket,
       p.station_id,
       p.device_id,
       p.metric_id,
       p.total_points,
       p.null_count,
       CASE WHEN p.present_secs IS NULL OR p.present_secs = 0 THEN 0
            ELSE (p.present_secs::double precision / 86400.0) END AS coverage_rate,
       COALESCE(o.outlier_count, 0) AS outlier_count
FROM per_day p
LEFT JOIN outliers o USING (date_bucket, station_id, device_id, metric_id)
ORDER BY p.date_bucket, p.station_id, p.device_id, p.metric_id;

COMMENT ON VIEW public.v_data_quality_stats IS $DOC$
视图名称: v_data_quality_stats
视图用途: 按日统计数据质量（覆盖率/空值/离群计数），统一 UTC 与 1 秒对齐口径。覆盖率以当日全秒 86400 为分母；如需窗口截断请使用函数 fn_quality_stats_1d。
创建时间: 2025-09-03
$DOC$;

