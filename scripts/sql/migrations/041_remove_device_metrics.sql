-- 041_remove_device_metrics.sql
-- 目的：删除 dim_metric_config 中 device_running / device_phase 指标（合并到 mv_device_running_1s 后不再需要）
-- 说明：先删除可能的元数据依赖，再删除 dim_metric_config 本体；若不存在则忽略。

BEGIN;

-- 清理元数据依赖
DELETE FROM public.dim_metric_metadata m
WHERE EXISTS (
  SELECT 1 FROM public.dim_metric_config c
  WHERE c.id = m.metric_id AND c.metric_key IN ('device_running','device_phase')
);

-- 删除指标定义
DELETE FROM public.dim_metric_config c
WHERE c.metric_key IN ('device_running','device_phase');

COMMIT;

