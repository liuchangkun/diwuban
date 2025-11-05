-- Create read index for CAgg presence (idempotent)
CREATE INDEX IF NOT EXISTS ix_cagg_presence_sdt ON public.cagg_presence_per_second (station_id, device_id, ts_second);

-- Verify
SELECT json_build_object(
  'cagg_index_exists', EXISTS(
    SELECT 1 FROM pg_indexes WHERE schemaname='public' AND tablename='cagg_presence_per_second' AND indexname='ix_cagg_presence_sdt'
  )
) AS result;

