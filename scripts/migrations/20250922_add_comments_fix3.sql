-- 增量验证：仅做两条显式注释，便于核查是否生效
-- 注意：本文件仅用于测试 COMMENT 上线有效性

-- A) 视图列：v_effective_metric_metadata.device_id
COMMENT ON COLUMN public.v_effective_metric_metadata.device_id IS '测试-列注释-设备ID';

-- B) 函数：time_bucket(interval, date)
COMMENT ON FUNCTION public.time_bucket(interval, date) IS '测试-函数注释-date';

