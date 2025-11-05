BEGIN;

-- 创建兼容视图：mv_presence_1s_any
-- 设计：优先兼容已有 mv_presence_1s（若存在则与 mpps 联合），否则仅基于 mpps 展开
DO $$
BEGIN
  IF to_regclass('public.mv_presence_1s') IS NOT NULL THEN
    EXECUTE $v$
      CREATE OR REPLACE VIEW public.mv_presence_1s_any AS
      SELECT station_id, device_id, metric_id, ts_bucket, present
      FROM public.mv_presence_1s
      UNION
      SELECT mpps.station_id,
             mpps.device_id,
             mc.id AS metric_id,
             mpps.ts_second AS ts_bucket,
             1::smallint AS present
      FROM public.metrics_presence_per_second_device mpps
      CROSS JOIN LATERAL unnest(mpps.available_metrics) AS u(metric_key)
      JOIN public.dim_metric_config mc ON mc.metric_key = u.metric_key
    $v$;
  ELSE
    EXECUTE $v$
      CREATE OR REPLACE VIEW public.mv_presence_1s_any AS
      SELECT mpps.station_id,
             mpps.device_id,
             mc.id AS metric_id,
             mpps.ts_second AS ts_bucket,
             1::smallint AS present
      FROM public.metrics_presence_per_second_device mpps
      CROSS JOIN LATERAL unnest(mpps.available_metrics) AS u(metric_key)
      JOIN public.dim_metric_config mc ON mc.metric_key = u.metric_key
    $v$;
  END IF;
END
$$ LANGUAGE plpgsql;

-- 性能：为 mpps.available_metrics 建 GIN 索引（若未存在）
CREATE INDEX IF NOT EXISTS ix_mpps_available_metrics
ON public.metrics_presence_per_second_device USING gin (available_metrics);

COMMIT;

