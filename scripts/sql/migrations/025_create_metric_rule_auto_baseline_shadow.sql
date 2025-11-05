-- 影子表：metric_rule_auto_baseline_shadow（方案B输出，不污染正式表）
-- 用途：存放方案B（STL/稳健残差等）生成的自动基线结果，供对照与验证

BEGIN;

CREATE TABLE IF NOT EXISTS public.metric_rule_auto_baseline_shadow (
  station_id bigint NOT NULL REFERENCES public.dim_stations(id),
  device_id  bigint NOT NULL REFERENCES public.dim_devices(id),
  metric_id  bigint NOT NULL REFERENCES public.dim_metric_config(id),
  lookback_days int NOT NULL,
  method text NOT NULL,         -- 'stl_residual' 等
  version text NOT NULL,        -- 'vB_shadow'
  p05 double precision NULL,
  p95 double precision NULL,
  median double precision NULL,
  mad double precision NULL,
  spike_abs double precision NULL,
  roc_abs double precision NULL,
  roc_ratio double precision NULL,
  flatline_eps double precision NULL,
  flatline_delta double precision NULL,
  computed_at timestamptz NOT NULL DEFAULT now(),
  remark text NULL,
  PRIMARY KEY (station_id, device_id, metric_id, lookback_days, method, version)
);

COMMENT ON TABLE public.metric_rule_auto_baseline_shadow IS '影子输出：方案B自动基线（STL/残差稳健）';

COMMIT;

