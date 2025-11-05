-- 影子表：metric_quality_rules_shadow（方案B输出，不污染正式表）
-- 用途：存放由方案B（STL/残差稳健等）生成的质量规则参数，供对照验证

BEGIN;

CREATE TABLE IF NOT EXISTS public.metric_quality_rules_shadow (
  station_id bigint NULL REFERENCES public.dim_stations(id),
  device_id  bigint NULL REFERENCES public.dim_devices(id),
  metric_id  bigint NOT NULL REFERENCES public.dim_metric_config(id),
  method text NOT NULL,                 -- stl_residual / gmm_bimodal 等
  version text NOT NULL,                -- vB_shadow
  value_min double precision NULL,
  value_max double precision NULL,
  spike_abs double precision NULL,
  roc_abs double precision NULL,
  roc_ratio double precision NULL,
  flatline_eps double precision NULL,
  flatline_delta double precision NULL,
  computed_at timestamptz NOT NULL DEFAULT now(),
  remark text NULL,
  PRIMARY KEY (station_id, device_id, metric_id, method, version)
);

COMMENT ON TABLE public.metric_quality_rules_shadow IS '影子输出：方案B质量规则参数（基于STL残差等），不影响正式表。';

COMMIT;

