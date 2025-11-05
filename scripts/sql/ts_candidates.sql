-- device_metric_candidates (static/low-frequency refreshed). No compression/retention.
-- Idempotent.

CREATE TABLE IF NOT EXISTS public.device_metric_candidates (
  device_id bigint PRIMARY KEY,
  metrics   text[] NOT NULL
);

-- Optional helper index if querying by metrics content becomes frequent (kept but commented)
-- CREATE INDEX IF NOT EXISTS ix_dmc_metrics_gin ON public.device_metric_candidates USING gin (metrics);

-- Verification
SELECT json_build_object(
  'device_metric_candidates_exists', (to_regclass('public.device_metric_candidates') IS NOT NULL)
) AS snapshot;

