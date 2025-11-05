-- Timescale Hypertable migration for staging tables (convert UNLOGGED -> LOGGED, no compression/retention)
-- Idempotent & safe to re-run

DO $$
BEGIN
  -- staging_raw -> ensure LOGGED then create hypertable on loaded_at
  IF NOT EXISTS (
    SELECT 1 FROM timescaledb_information.hypertables
    WHERE hypertable_schema='public' AND hypertable_name='staging_raw'
  ) THEN
    IF to_regclass('public.staging_raw') IS NOT NULL THEN
      -- If table is UNLOGGED, switch to LOGGED (Timescale requires logged tables)
      IF EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relname='staging_raw' AND c.relpersistence='u'
      ) THEN
        EXECUTE 'ALTER TABLE public.staging_raw SET LOGGED';
      END IF;
      PERFORM create_hypertable('public.staging_raw', 'loaded_at', if_not_exists=>TRUE);
    END IF;
  END IF;

  -- staging_rejects -> ensure LOGGED then create hypertable on rejected_at
  IF NOT EXISTS (
    SELECT 1 FROM timescaledb_information.hypertables
    WHERE hypertable_schema='public' AND hypertable_name='staging_rejects'
  ) THEN
    IF to_regclass('public.staging_rejects') IS NOT NULL THEN
      IF EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relname='staging_rejects' AND c.relpersistence='u'
      ) THEN
        EXECUTE 'ALTER TABLE public.staging_rejects SET LOGGED';
      END IF;
      PERFORM create_hypertable('public.staging_rejects', 'rejected_at', if_not_exists=>TRUE);
    END IF;
  END IF;
END$$;

-- Verification snapshot
WITH p AS (
  SELECT n.nspname, c.relname, c.relpersistence
  FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
  WHERE n.nspname='public' AND c.relname IN ('staging_raw','staging_rejects')
)
SELECT json_build_object(
  'staging_raw', json_build_object(
    'exists', (to_regclass('public.staging_raw') IS NOT NULL),
    'persistence', (SELECT relpersistence FROM p WHERE relname='staging_raw'),
    'is_hypertable', EXISTS(
      SELECT 1 FROM timescaledb_information.hypertables WHERE hypertable_schema='public' AND hypertable_name='staging_raw')
  ),
  'staging_rejects', json_build_object(
    'exists', (to_regclass('public.staging_rejects') IS NOT NULL),
    'persistence', (SELECT relpersistence FROM p WHERE relname='staging_rejects'),
    'is_hypertable', EXISTS(
      SELECT 1 FROM timescaledb_information.hypertables WHERE hypertable_schema='public' AND hypertable_name='staging_rejects')
  )
) AS snapshot;

