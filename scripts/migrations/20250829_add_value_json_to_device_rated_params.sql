-- 增加 device_rated_params.value_json 字段，并更新约束
-- 目的：在不增加大量列的前提下，支持数组/对象等结构化参数（如 minor_K 列表、传感器可用性、拓扑标志等）

BEGIN;

-- 1) 增加 JSONB 字段
ALTER TABLE IF EXISTS public.device_rated_params
  ADD COLUMN IF NOT EXISTS value_json JSONB;

COMMENT ON COLUMN public.device_rated_params.value_json IS 'JSON 参数值（用于数组/对象等结构化参数）';

-- 2) 更新“至少一个值非空”的约束
ALTER TABLE IF EXISTS public.device_rated_params
  DROP CONSTRAINT IF EXISTS chk_rated_value_presence;

ALTER TABLE IF EXISTS public.device_rated_params
  ADD CONSTRAINT chk_rated_value_presence
  CHECK (value_numeric IS NOT NULL OR value_text IS NOT NULL OR value_json IS NOT NULL);

-- 3) 可选索引：按需为 JSONB 字段建立 GIN 索引（查询频繁时启用）
-- CREATE INDEX IF NOT EXISTS idx_rated_params_value_json ON public.device_rated_params USING GIN (value_json);

COMMIT;

