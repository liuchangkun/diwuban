-- 指标元数据覆盖表（可按站点/设备粒度覆盖全局默认）
-- 目的：为特定站点/设备提供更精细的单位/分辨率/量程与饱和阈值覆盖

BEGIN;

CREATE TABLE IF NOT EXISTS public.dim_metric_metadata_override (
  rule_id bigserial PRIMARY KEY,
  station_id bigint NULL REFERENCES public.dim_stations(id),
  device_id  bigint NULL REFERENCES public.dim_devices(id),
  metric_id  bigint NOT NULL REFERENCES public.dim_metric_config(id),
  resolution double precision NULL,
  phys_min   double precision NULL,
  phys_max   double precision NULL,
  saturation_min double precision NULL,
  saturation_max double precision NULL,
  remark text NULL,
  updated_at timestamptz NOT NULL DEFAULT now(),
  updated_by text NULL
);

COMMENT ON TABLE public.dim_metric_metadata_override IS '指标元数据覆盖表：可按站点/设备粒度覆盖全局默认。优先级：设备 > 站点 > 全局。';
COMMENT ON COLUMN public.dim_metric_metadata_override.rule_id IS '主键ID。';
COMMENT ON COLUMN public.dim_metric_metadata_override.station_id IS '站点ID（可空）。';
COMMENT ON COLUMN public.dim_metric_metadata_override.device_id IS '设备ID（可空）。';
COMMENT ON COLUMN public.dim_metric_metadata_override.metric_id IS '指标ID（关联 dim_metric_config.id）。';
COMMENT ON COLUMN public.dim_metric_metadata_override.resolution IS '覆盖分辨率。';
COMMENT ON COLUMN public.dim_metric_metadata_override.phys_min IS '覆盖物理/量程下界。';
COMMENT ON COLUMN public.dim_metric_metadata_override.phys_max IS '覆盖物理/量程上界。';
COMMENT ON COLUMN public.dim_metric_metadata_override.saturation_min IS '覆盖下饱和阈值。';
COMMENT ON COLUMN public.dim_metric_metadata_override.saturation_max IS '覆盖上饱和阈值。';
COMMENT ON COLUMN public.dim_metric_metadata_override.remark IS '中文备注与口径说明。';
COMMENT ON COLUMN public.dim_metric_metadata_override.updated_at IS '更新时间（自动）。';
COMMENT ON COLUMN public.dim_metric_metadata_override.updated_by IS '更新人（可空）。';

COMMIT;

