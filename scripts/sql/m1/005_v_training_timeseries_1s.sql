\encoding UTF8
SET client_encoding = 'UTF8';

/*
视图名称: v_training_timeseries_1s
视图用途: 统一对外 1 秒步长 UTC 时序读取口径，包含站点/设备/指标基础维度与显示单位。
数据来源: fact_measurements（明细） + dim_devices + dim_metric_config + dim_stations
字段映射:
  - ts_bucket <- fact_measurements.ts_bucket
  - station_id <- dim_devices.station_id
  - station_name <- dim_stations.name
  - device_id <- fact_measurements.device_id
  - device_name <- dim_devices.name
  - metric_id <- fact_measurements.metric_id
  - metric_key <- dim_metric_config.metric_key
  - unit_display <- COALESCE(dim_metric_config.unit_display, dim_metric_config.unit)
  - value <- fact_measurements.value::double precision
过滤逻辑: 无对象白名单；按需在查询侧追加 WHERE 条件
创建时间: 2025-09-03
*/

CREATE OR REPLACE VIEW public.v_training_timeseries_1s AS
SELECT
  fm.ts_bucket::timestamptz AS ts_bucket,
  d.station_id,
  s.name AS station_name,
  fm.device_id,
  d.name AS device_name,
  fm.metric_id,
  mc.metric_key,
  COALESCE(mc.unit_display, mc.unit) AS unit_display,
  fm.value::double precision AS value
FROM public.fact_measurements fm
JOIN public.dim_devices d ON d.id = fm.device_id
JOIN public.dim_metric_config mc ON mc.id = fm.metric_id
JOIN public.dim_stations s ON s.id = d.station_id;

COMMENT ON VIEW public.v_training_timeseries_1s IS $DOC$
视图名称: v_training_timeseries_1s
视图用途: 统一对外 1 秒步长 UTC 时序读取口径，包含站点/设备/指标基础维度与显示单位。
来源: fact_measurements + dim_devices + dim_metric_config + dim_stations
字段: ts_bucket, station_id, station_name, device_id, device_name, metric_id, metric_key, unit_display, value
创建时间: 2025-09-03
$DOC$;

