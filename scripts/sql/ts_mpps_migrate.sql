-- Migrate public.metrics_presence_per_second_device to Timescale Hypertable (ts_second, station_id)
-- No compression, no retention. Idempotent. Zero-downtime swap preserving original as *_legacy.

DO $$
DECLARE
  is_ht boolean;
BEGIN
  SELECT EXISTS(
    SELECT 1 FROM timescaledb_information.hypertables
    WHERE hypertable_schema='public' AND hypertable_name='metrics_presence_per_second_device'
  ) INTO is_ht;

  IF is_ht THEN
    -- Ensure helper indexes exist on the hypertable (use distinct names to avoid legacy conflicts)
    PERFORM 1 FROM pg_indexes WHERE schemaname='public' AND tablename='metrics_presence_per_second_device' AND indexname='mpps_ht_brin_ts';
    IF NOT FOUND THEN
      EXECUTE 'CREATE INDEX IF NOT EXISTS mpps_ht_brin_ts ON public.metrics_presence_per_second_device USING brin (ts_second)';
    END IF;
    PERFORM 1 FROM pg_indexes WHERE schemaname='public' AND tablename='metrics_presence_per_second_device' AND indexname='mpps_ht_gin_av';
    IF NOT FOUND THEN
      EXECUTE 'CREATE INDEX IF NOT EXISTS mpps_ht_gin_av ON public.metrics_presence_per_second_device USING gin (available_metrics)';
    END IF;
    PERFORM 1 FROM pg_indexes WHERE schemaname='public' AND tablename='metrics_presence_per_second_device' AND indexname='mpps_ht_gin_nc';
    IF NOT FOUND THEN
      EXECUTE 'CREATE INDEX IF NOT EXISTS mpps_ht_gin_nc ON public.metrics_presence_per_second_device USING gin (need_compute_metrics)';
    END IF;
    RETURN;
  END IF;

  -- Create new hypertable with explicit columns and PK (avoid inheriting partitioning)
  IF to_regclass('public.mpps_new') IS NOT NULL THEN
    EXECUTE 'DROP TABLE IF EXISTS public.mpps_new CASCADE';
  END IF;
  EXECUTE $DDL$
    CREATE TABLE public.mpps_new (
      station_id bigint NOT NULL,
      device_id  bigint NOT NULL,
      ts_second  timestamptz NOT NULL,
      available_metrics text[] NOT NULL DEFAULT '{}'::text[],
      need_compute_metrics text[] NOT NULL DEFAULT '{}'::text[],
      created_at timestamptz NOT NULL DEFAULT now(),
      CONSTRAINT mpps_ht_pkey PRIMARY KEY (station_id, device_id, ts_second)
    )
  $DDL$;
  EXECUTE 'SELECT create_hypertable(''public.mpps_new'',''ts_second'',''station_id'',16, if_not_exists=>TRUE)';

  -- Copy data if any
  IF EXISTS (SELECT 1 FROM pg_class WHERE oid='public.metrics_presence_per_second_device'::regclass) THEN
    EXECUTE 'INSERT INTO public.mpps_new (station_id, device_id, ts_second, available_metrics, need_compute_metrics, created_at)
             SELECT station_id, device_id, ts_second, available_metrics, need_compute_metrics, created_at
             FROM public.metrics_presence_per_second_device';
  END IF;

  -- Swap tables
  EXECUTE 'ALTER TABLE public.metrics_presence_per_second_device RENAME TO metrics_presence_per_second_device_legacy';
  EXECUTE 'ALTER TABLE public.mpps_new RENAME TO metrics_presence_per_second_device';

  -- Create helper indexes on the new hypertable (use distinct names)
  EXECUTE 'CREATE INDEX IF NOT EXISTS mpps_ht_brin_ts ON public.metrics_presence_per_second_device USING brin (ts_second)';
  EXECUTE 'CREATE INDEX IF NOT EXISTS mpps_ht_gin_av ON public.metrics_presence_per_second_device USING gin (available_metrics)';
  EXECUTE 'CREATE INDEX IF NOT EXISTS mpps_ht_gin_nc ON public.metrics_presence_per_second_device USING gin (need_compute_metrics)';
END$$;

-- Verification snapshot
SELECT json_build_object(
  'mpps_is_hypertable', EXISTS(
    SELECT 1 FROM timescaledb_information.hypertables WHERE hypertable_schema='public' AND hypertable_name='metrics_presence_per_second_device'
  ),
  'indexes', json_build_object(
    'brin_ts', (SELECT EXISTS(SELECT 1 FROM pg_indexes WHERE schemaname='public' AND tablename='metrics_presence_per_second_device' AND indexname='mpps_ht_brin_ts')),
    'gin_av',  (SELECT EXISTS(SELECT 1 FROM pg_indexes WHERE schemaname='public' AND tablename='metrics_presence_per_second_device' AND indexname='mpps_ht_gin_av')),
    'gin_nc',  (SELECT EXISTS(SELECT 1 FROM pg_indexes WHERE schemaname='public' AND tablename='metrics_presence_per_second_device' AND indexname='mpps_ht_gin_nc'))
  )
) AS snapshot;

