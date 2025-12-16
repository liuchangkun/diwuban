-- 指标全局物理元数据表（每个 metric 一行）
-- 目的：沉淀单位、分辨率与物理/量程边界，供质量判定与阈值/基线计算使用

BEGIN;

CREATE TABLE IF NOT EXISTS public.dim_metric_metadata (
  metric_id bigint PRIMARY KEY REFERENCES public.dim_metric_config(id),
  unit text NULL,
  resolution double precision NULL,
  phys_min double precision NULL,
  phys_max double precision NULL,
  saturation_min double precision NULL,
  saturation_max double precision NULL,
  remark text NULL,
  updated_at timestamptz NOT NULL DEFAULT now(),
  updated_by text NULL
);

COMMENT ON TABLE public.dim_metric_metadata IS '全局指标物理元数据表：每个 metric 一行，存放单位、分辨率、物理/量程边界、饱和判据等。';
COMMENT ON COLUMN public.dim_metric_metadata.metric_id IS '指标ID（关联 dim_metric_config.id）。';
COMMENT ON COLUMN public.dim_metric_metadata.unit IS '单位（如：kW、A、V、Hz、m、kPa、m3/h、kWh 等）。';
COMMENT ON COLUMN public.dim_metric_metadata.resolution IS '分辨率/最小可分辨值（例如 0.01 kW、1 V）。';
COMMENT ON COLUMN public.dim_metric_metadata.phys_min IS '物理/量程下界（可空表示未知或由统计回退）。';
COMMENT ON COLUMN public.dim_metric_metadata.phys_max IS '物理/量程上界（可空表示未知或由统计回退）。';
COMMENT ON COLUMN public.dim_metric_metadata.saturation_min IS '下饱和判据阈值（接近 phys_min 持续判为饱和）。';
COMMENT ON COLUMN public.dim_metric_metadata.saturation_max IS '上饱和判据阈值（接近 phys_max 持续判为饱和）。';
COMMENT ON COLUMN public.dim_metric_metadata.remark IS '中文备注与口径说明。';
COMMENT ON COLUMN public.dim_metric_metadata.updated_at IS '更新时间（自动）。';
COMMENT ON COLUMN public.dim_metric_metadata.updated_by IS '更新人（可空）。';

COMMIT;

