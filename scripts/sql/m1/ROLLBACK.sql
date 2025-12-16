-- ROLLBACK（M1 范围内最小回滚，仅对象）
-- 注意：仅供开发环境使用；生产请评审

DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_proc WHERE proname='fn_startstop_windows' AND pg_function_is_visible(oid)) THEN
    EXECUTE 'DROP FUNCTION public.fn_startstop_windows(bigint,timestamptz,timestamptz)';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_proc WHERE proname='fn_running_state_1s' AND pg_function_is_visible(oid)) THEN
    EXECUTE 'DROP FUNCTION public.fn_running_state_1s(bigint,bigint,timestamptz,timestamptz)';
  END IF;
END $$;

-- 如需回滚阈值表（谨慎）：
-- DROP TABLE public.device_running_thresholds;

