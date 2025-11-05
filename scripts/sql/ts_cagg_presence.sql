-- Continuous aggregate for presence (1-second buckets). No compression/retention.
-- Idempotent via guard + dynamic EXECUTE with single-quoted string

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM timescaledb_information.continuous_aggregates
    WHERE view_schema='public' AND view_name='cagg_presence_per_second'
  ) THEN
    EXECUTE '
      CREATE MATERIALIZED VIEW public.cagg_presence_per_second
      WITH (timescaledb.continuous) AS
      SELECT
        fm.station_id,
        fm.device_id,
        time_bucket(''1 second'', fm.ts_bucket) AS ts_second,
        array_agg(DISTINCT mc.metric_key ORDER BY mc.metric_key) AS available_metrics
      FROM public.fact_measurements fm
      JOIN public.dim_metric_config mc ON mc.id = fm.metric_id
      GROUP BY fm.station_id, fm.device_id, ts_second
      WITH NO DATA
    ';
  END IF;
END$$;

-- Index to speed up syncing reads
CREATE INDEX IF NOT EXISTS ix_cagg_presence_sdt ON public.cagg_presence_per_second (station_id, device_id, ts_second);

-- Verification
SELECT json_build_object(
  'cagg_exists', EXISTS(
    SELECT 1 FROM timescaledb_information.continuous_aggregates WHERE view_schema='public' AND view_name='cagg_presence_per_second'
  ),
  'cagg_index_exists', EXISTS(
    SELECT 1 FROM pg_indexes WHERE schemaname='public' AND tablename='cagg_presence_per_second' AND indexname='ix_cagg_presence_sdt'
  )
) AS snapshot;

