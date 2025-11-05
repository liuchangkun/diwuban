BEGIN;

-- 1) 增加 code 维度列（可为空，兼容旧数据）；为便捷聚合增加组合索引
ALTER TABLE public.quality_profile_log
  ADD COLUMN IF NOT EXISTS code integer;

CREATE INDEX IF NOT EXISTS idx_qprof_time_dev_code
  ON public.quality_profile_log(window_start, window_end, device_id, code);

-- 2) 触发器：当 code 为空且 stage 为 'update_XXX' 时，自动解析 code
CREATE OR REPLACE FUNCTION public.fn_qprof_stage_to_code()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.code IS NULL AND NEW.stage IS NOT NULL AND position('update_' in NEW.stage) = 1 THEN
    BEGIN
      NEW.code := NULLIF(split_part(NEW.stage, '_', 2), '')::int;
    EXCEPTION WHEN others THEN
      NEW.code := NULL;
    END;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_qprof_set_code ON public.quality_profile_log;
CREATE TRIGGER trg_qprof_set_code
BEFORE INSERT ON public.quality_profile_log
FOR EACH ROW EXECUTE FUNCTION public.fn_qprof_stage_to_code();

COMMIT;

