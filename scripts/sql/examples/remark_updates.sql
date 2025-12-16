-- 示例：501/602 阈值与差异化 remark 批量更新（remark 为 text 列，兼容历史非JSON内容）

-- 工具表达式：将 remark(text) 安全转 jsonb（非JSON则给空对象）
-- 用法示例： (CASE WHEN remark IS NOT NULL AND trim(remark) LIKE '{%' THEN remark::jsonb ELSE '{}'::jsonb END)

-- 501 全局默认：5s
UPDATE public.metric_quality_rules
SET remark = ((CASE WHEN remark IS NOT NULL AND trim(remark) LIKE '{%' THEN remark::jsonb ELSE '{}'::jsonb END)
              || '{"clock_skew_sec": 5}'::jsonb)::text
WHERE station_id IS NULL AND device_id IS NULL AND metric_id IS NULL;

-- 501 某站点：8s（示例）
-- UPDATE public.metric_quality_rules
-- SET remark = ((CASE WHEN remark IS NOT NULL AND trim(remark) LIKE '{%' THEN remark::jsonb ELSE '{}'::jsonb END)
--               || '{"clock_skew_sec": 8}'::jsonb)::text
-- WHERE station_id = 123 AND device_id IS NULL AND metric_id IS NULL;

-- 501 某设备：10s（示例）
-- UPDATE public.metric_quality_rules
-- SET remark = ((CASE WHEN remark IS NOT NULL AND trim(remark) LIKE '{%' THEN remark::jsonb ELSE '{}'::jsonb END)
--               || '{"clock_skew_sec": 10}'::jsonb)::text
-- WHERE device_id = 456 AND metric_id IS NULL;

-- 602 全局默认：k×MAD=4.0
UPDATE public.metric_quality_rules
SET remark = ((CASE WHEN remark IS NOT NULL AND trim(remark) LIKE '{%' THEN remark::jsonb ELSE '{}'::jsonb END)
              || '{"calib_bias_k_mad": 4.0}'::jsonb)::text
WHERE station_id IS NULL AND device_id IS NULL AND metric_id IS NULL;

-- 602 流量类：k×MAD=5.0
UPDATE public.metric_quality_rules r
SET remark = ((CASE WHEN r.remark IS NOT NULL AND trim(r.remark) LIKE '{%' THEN r.remark::jsonb ELSE '{}'::jsonb END)
              || '{"calib_bias_k_mad": 5.0}'::jsonb)::text
FROM public.dim_metric_config m
WHERE r.metric_id = m.id AND m.metric_key IN ('pump_flow_rate','main_pipeline_flow_rate');

-- 602 功率类：k×MAD=4.5
UPDATE public.metric_quality_rules r
SET remark = ((CASE WHEN r.remark IS NOT NULL AND trim(r.remark) LIKE '{%' THEN r.remark::jsonb ELSE '{}'::jsonb END)
              || '{"calib_bias_k_mad": 4.5}'::jsonb)::text
FROM public.dim_metric_config m
WHERE r.metric_id = m.id AND m.metric_key IN ('pump_active_power','active_power','power');

-- 602 前置约束：最小存在/运行秒数（默认方案）
-- 示例：全局要求 present>=600s、running>=300s
UPDATE public.metric_quality_rules
SET remark = ((CASE WHEN remark IS NOT NULL AND trim(remark) LIKE '{%' THEN remark::jsonb ELSE '{}'::jsonb END)
              || '{"calib_min_present_secs": 600, "calib_min_running_secs": 300}'::jsonb)::text
WHERE station_id IS NULL AND device_id IS NULL AND metric_id IS NULL;

