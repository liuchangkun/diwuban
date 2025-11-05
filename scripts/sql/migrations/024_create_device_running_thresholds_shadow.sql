-- 影子表：device_running_thresholds_shadow（方案B输出，不污染正式表）
-- 用途：存放方案B（GMM等）计算出来的 PF 阈值，供对照与验证

BEGIN;

CREATE TABLE IF NOT EXISTS public.device_running_thresholds_shadow (
  device_id bigint NOT NULL REFERENCES public.dim_devices(id),
  method text NOT NULL,            -- 'gmm_bimodal' 等
  version text NOT NULL,           -- 'vB_shadow'
  pf_min double precision NULL,
  pf_max double precision NULL,
  computed_at timestamptz NOT NULL DEFAULT now(),
  remark text NULL,
  PRIMARY KEY (device_id, method, version)
);

COMMENT ON TABLE public.device_running_thresholds_shadow IS '影子输出：方案B的PF阈值（不影响正式表）。';
COMMENT ON COLUMN public.device_running_thresholds_shadow.device_id IS '设备ID';
COMMENT ON COLUMN public.device_running_thresholds_shadow.method IS '计算方法（如 gmm_bimodal）';
COMMENT ON COLUMN public.device_running_thresholds_shadow.version IS '版本标记（默认 vB_shadow）';
COMMENT ON COLUMN public.device_running_thresholds_shadow.pf_min IS '功率因数最小阈值（影子）';
COMMENT ON COLUMN public.device_running_thresholds_shadow.pf_max IS '功率因数最大阈值（影子）';
COMMENT ON COLUMN public.device_running_thresholds_shadow.computed_at IS '计算时间';
COMMENT ON COLUMN public.device_running_thresholds_shadow.remark IS '备注';

COMMIT;

