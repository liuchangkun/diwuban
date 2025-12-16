-- 042: Introduce multi-code storage for quality flags using int[]
BEGIN;

-- 1) Add array column for multi-quality codes (phase 1 of Scheme B)
ALTER TABLE public.fact_measurements
  ADD COLUMN IF NOT EXISTS quality_codes integer[] DEFAULT '{}'::integer[];

-- 2) Backfill from legacy integer quality_status
UPDATE public.fact_measurements
SET quality_codes = CASE WHEN COALESCE(quality_status,0) > 0 THEN ARRAY[quality_status] ELSE '{}'::int[] END
WHERE (quality_codes IS NULL) OR (array_length(quality_codes,1) IS NULL);

-- 3) Index for containment queries
CREATE INDEX IF NOT EXISTS idx_fact_measurements_quality_codes_gin
  ON public.fact_measurements USING GIN (quality_codes);

COMMIT;

