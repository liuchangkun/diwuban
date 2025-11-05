-- 目的：将行级质量码投影为“指标化”的只读视图，兼容按指标消费的场景

BEGIN;

CREATE OR REPLACE VIEW public.v_quality_code_metric AS
SELECT station_id, device_id, metric_id,
       ts_bucket,
       quality_status::numeric AS value
FROM public.fact_measurements;

COMMENT ON VIEW public.v_quality_code_metric IS '质量码指标视图：将 fact_measurements.quality_status 投影为 value，便于与其它指标统一消费。';

COMMIT;

