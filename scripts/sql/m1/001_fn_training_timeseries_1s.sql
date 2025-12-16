\encoding UTF8
SET client_encoding = 'UTF8';

/*
函数名称: fn_training_timeseries_1s
函数用途: 提供统一的 1 秒步长 UTC 训练/分析读取口径，返回指定站点-设备-指标在时间窗口内的逐秒时序。
输入参数:
  p_station_id bigint      - 站点ID（维表 dim_stations.id）
  p_device_id  bigint      - 设备ID（维表 dim_devices.id）
  p_metric_id  bigint      - 指标ID（维表 dim_metric_config.id）
  p_start_ts   timestamptz - 时间窗口起（UTC，含）
  p_end_ts     timestamptz - 时间窗口止（UTC，含）
返回格式:
  ts_bucket   timestamptz      - UTC 秒对齐时间戳
  value       double precision - 数值（fact_measurements.value 映射，转换为双精度）
  station_id  bigint
  device_id   bigint
  metric_id   bigint
使用示例:
  SELECT * FROM public.fn_training_timeseries_1s(1,1,1,'2025-09-01T00:00:00Z','2025-09-01T00:00:05Z');
创建时间: 2025-09-03
*/

CREATE OR REPLACE FUNCTION public.fn_training_timeseries_1s(
  p_station_id bigint,
  p_device_id  bigint,
  p_metric_id  bigint,
  p_start_ts   timestamptz,
  p_end_ts     timestamptz
)
RETURNS TABLE (
  ts_bucket   timestamptz,
  value       double precision,
  station_id  bigint,
  device_id   bigint,
  metric_id   bigint
)
LANGUAGE sql
STABLE
AS $fn$
WITH series AS (
  /* 生成 1 秒步长的 UTC 时间序列（含起止） */
  SELECT generate_series(p_start_ts, p_end_ts - INTERVAL '1 second', INTERVAL '1 second')::timestamptz AS ts_bucket
), data AS (
  /* 仅扫描命中对象与时间范围的分区；匹配现有 BTREE/BRIN 索引与分区裁剪 */
  SELECT fm.ts_bucket, fm.value::double precision
  FROM public.fact_measurements fm
  WHERE fm.station_id = p_station_id
    AND fm.device_id  = p_device_id
    AND fm.metric_id  = p_metric_id
    AND fm.ts_bucket >= p_start_ts AND fm.ts_bucket < p_end_ts
)
SELECT s.ts_bucket,
       d.value,
       p_station_id AS station_id,
       p_device_id  AS device_id,
       p_metric_id  AS metric_id
FROM series s
LEFT JOIN data d USING (ts_bucket)
ORDER BY s.ts_bucket;
$fn$;

COMMENT ON FUNCTION public.fn_training_timeseries_1s(bigint,bigint,bigint,timestamptz,timestamptz) IS $DOC$
函数名称: fn_training_timeseries_1s
函数用途: 提供统一的 1 秒步长 UTC 训练/分析读取口径，返回指定站点-设备-指标在时间窗口内的逐秒时序。
输入参数:
  p_station_id bigint; p_device_id bigint; p_metric_id bigint; p_start_ts timestamptz; p_end_ts timestamptz。
返回格式: (ts_bucket timestamptz, value double precision, station_id bigint, device_id bigint, metric_id bigint)
使用示例: SELECT * FROM public.fn_training_timeseries_1s(1,1,1,'2025-09-01T00:00:00Z','2025-09-01T00:00:05Z');
创建时间: 2025-09-03
$DOC$;

