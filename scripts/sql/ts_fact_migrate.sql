-- Timescale Hypertable migration for public.fact_measurements (no compression/retention)
-- Idempotent & safe. Preserves table name; if original was partitioned, uses new-table swap.

DO $$
DECLARE
  is_ht boolean;
  has_children boolean;
  rowcount bigint;
BEGIN
  SELECT EXISTS(
    SELECT 1 FROM timescaledb_information.hypertables
    WHERE hypertable_schema='public' AND hypertable_name='fact_measurements'
  ) INTO is_ht;

  IF is_ht THEN
    -- Already hypertable: ensure required unique index exists
    PERFORM 1 FROM pg_indexes WHERE schemaname='public' AND tablename='fact_measurements' AND indexname='ux_fact_sdm_tb';
    IF NOT FOUND THEN
      EXECUTE 'CREATE UNIQUE INDEX IF NOT EXISTS ux_fact_sdm_tb ON public.fact_measurements (station_id, device_id, metric_id, ts_bucket)';
    END IF;
    -- Optional covering index
    PERFORM 1 FROM pg_indexes WHERE schemaname='public' AND tablename='fact_measurements' AND indexname='ix_fact_sdm_tb';
    IF NOT FOUND THEN
      EXECUTE 'CREATE INDEX IF NOT EXISTS ix_fact_sdm_tb ON public.fact_measurements (station_id, device_id, metric_id, ts_bucket) INCLUDE (value)';
    END IF;
    RETURN;
  END IF;

  -- Not hypertable. Check if partitioned parent with children
  SELECT EXISTS(
    SELECT 1 FROM pg_inherits WHERE inhparent='public.fact_measurements'::regclass
  ) INTO has_children;

  -- Check row count (fast estimate acceptable)
  SELECT COALESCE((SELECT n_live_tup FROM pg_stat_all_tables WHERE relid='public.fact_measurements'::regclass),0) INTO rowcount;

  IF NOT has_children THEN
    -- Regular table: convert in-place (migrate_data handles existing rows)
    EXECUTE 'SELECT create_hypertable(''public.fact_measurements'',''ts_bucket'',''station_id'',16, if_not_exists=>TRUE, migrate_data=>TRUE)';
  ELSE
    -- Partitioned parent: create new hypertable and swap
    IF to_regclass('public.fact_measurements_new') IS NOT NULL THEN
      EXECUTE 'DROP TABLE IF EXISTS public.fact_measurements_new CASCADE';
    END IF;
    EXECUTE 'CREATE TABLE public.fact_measurements_new (LIKE public.fact_measurements INCLUDING ALL)';
    EXECUTE 'SELECT create_hypertable(''public.fact_measurements_new'',''ts_bucket'',''station_id'',16, if_not_exists=>TRUE)';
    -- Copy data (if any)
    IF rowcount > 0 THEN
      EXECUTE 'INSERT INTO public.fact_measurements_new SELECT * FROM public.fact_measurements';
    END IF;
    -- Swap
    EXECUTE 'ALTER TABLE public.fact_measurements RENAME TO fact_measurements_legacy';
    EXECUTE 'ALTER TABLE public.fact_measurements_new RENAME TO fact_measurements';
  END IF;

  -- Ensure indexes on the (new) hypertable
  EXECUTE 'CREATE UNIQUE INDEX IF NOT EXISTS ux_fact_sdm_tb ON public.fact_measurements (station_id, device_id, metric_id, ts_bucket)';
  EXECUTE 'CREATE INDEX IF NOT EXISTS ix_fact_sdm_tb ON public.fact_measurements (station_id, device_id, metric_id, ts_bucket) INCLUDE (value)';
END$$;

-- Verification snapshot
SELECT json_build_object(
  'fact_is_hypertable', EXISTS(
    SELECT 1 FROM timescaledb_information.hypertables WHERE hypertable_schema='public' AND hypertable_name='fact_measurements'),
  'unique_index', (SELECT EXISTS(SELECT 1 FROM pg_indexes WHERE schemaname='public' AND tablename='fact_measurements' AND indexname='ux_fact_sdm_tb')),
  'covering_index', (SELECT EXISTS(SELECT 1 FROM pg_indexes WHERE schemaname='public' AND tablename='fact_measurements' AND indexname='ix_fact_sdm_tb'))
) AS snapshot;

