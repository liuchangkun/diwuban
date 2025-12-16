-- Timescale Hypertable migration for staging tables (no compression, no retention)
-- Idempotent: only creates hypertables if not already present
-- Requirements: TimescaleDB extension installed

DO $$
BEGIN
  -- staging_raw -> Hypertable on loaded_at
  IF NOT EXISTS (
    SELECT 1 FROM timescaledb_information.hypertables
    WHERE hypertable_schema='public' AND hypertable_name='staging_raw'
  ) THEN
    PERFORM create_hypertable('public.staging_raw', 'loaded_at', if_not_exists=>TRUE);
  END IF;

  -- staging_rejects -> Hypertable on rejected_at
  IF NOT EXISTS (
    SELECT 1 FROM timescaledb_information.hypertables
    WHERE hypertable_schema='public' AND hypertable_name='staging_rejects'
  ) THEN
    PERFORM create_hypertable('public.staging_rejects', 'rejected_at', if_not_exists=>TRUE);
  END IF;
END$$;

-- Verification snapshot (read-only)
SELECT json_build_object(
  'staging_raw_is_hypertable', EXISTS(
    SELECT 1 FROM timescaledb_information.hypertables WHERE hypertable_schema='public' AND hypertable_name='staging_raw'),
  'staging_rejects_is_hypertable', EXISTS(
    SELECT 1 FROM timescaledb_information.hypertables WHERE hypertable_schema='public' AND hypertable_name='staging_rejects')
) AS snapshot;

