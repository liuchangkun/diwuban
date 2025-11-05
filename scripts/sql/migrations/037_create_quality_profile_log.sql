BEGIN;

CREATE TABLE IF NOT EXISTS public.quality_profile_log (
  id           bigserial PRIMARY KEY,
  created_at   timestamptz NOT NULL DEFAULT now(),
  window_start timestamptz NOT NULL,
  window_end   timestamptz NOT NULL,
  station_id   bigint NULL,
  device_id    bigint NULL,
  stage        text NOT NULL,
  duration_ms  numeric NULL,
  rows_affected bigint NULL,
  details      jsonb NULL
);

CREATE INDEX IF NOT EXISTS idx_qprof_time ON public.quality_profile_log(window_start, window_end);
CREATE INDEX IF NOT EXISTS idx_qprof_stage ON public.quality_profile_log(stage);
CREATE INDEX IF NOT EXISTS idx_qprof_device ON public.quality_profile_log(station_id, device_id);

COMMENT ON TABLE public.quality_profile_log IS '质量过程性能剖析日志（按窗口/阶段记录耗时与行数）';

COMMIT;

