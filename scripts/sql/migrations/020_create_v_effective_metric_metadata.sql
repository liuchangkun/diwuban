-- “有效”指标元数据视图（合并全局与覆盖，设备>站点>全局 优先级）
-- 简化消费侧读取：优先返回设备/站点覆盖，否则返回全局默认

BEGIN;

CREATE OR REPLACE VIEW public.v_effective_metric_metadata AS
WITH base AS (
  SELECT metric_id, unit, resolution, phys_min, phys_max, saturation_min, saturation_max
  FROM public.dim_metric_metadata
),
-- 设备级覆盖
od AS (
  SELECT device_id, metric_id, resolution, phys_min, phys_max, saturation_min, saturation_max
  FROM public.dim_metric_metadata_override WHERE device_id IS NOT NULL
),
-- 站点级覆盖
os AS (
  SELECT station_id, metric_id, resolution, phys_min, phys_max, saturation_min, saturation_max
  FROM public.dim_metric_metadata_override WHERE device_id IS NULL AND station_id IS NOT NULL
)
SELECT
  COALESCE(od.device_id, NULL) AS device_id,
  COALESCE(os.station_id, NULL) AS station_id,
  b.metric_id,
  b.unit,
  COALESCE(od.resolution, os.resolution, b.resolution) AS resolution,
  COALESCE(od.phys_min,   os.phys_min,   b.phys_min)   AS phys_min,
  COALESCE(od.phys_max,   os.phys_max,   b.phys_max)   AS phys_max,
  COALESCE(od.saturation_min, os.saturation_min, b.saturation_min) AS saturation_min,
  COALESCE(od.saturation_max, os.saturation_max, b.saturation_max) AS saturation_max
FROM base b
LEFT JOIN os ON os.metric_id=b.metric_id
LEFT JOIN od ON od.metric_id=b.metric_id;

COMMENT ON VIEW public.v_effective_metric_metadata IS '有效指标元数据视图：按优先级(设备>站点>全局)合并覆盖，供算法统一读取。';

COMMIT;

