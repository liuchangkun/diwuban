-- 目的：为事实表增加“数据质量”与“运行相位”标注列，统一行级过滤与审计
-- 注意：该脚本仅添加列与中文注释，不修改既有行为；默认值保证向后兼容

BEGIN;

ALTER TABLE public.fact_measurements
  ADD COLUMN IF NOT EXISTS quality_status smallint NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS quality_type   text,
  ADD COLUMN IF NOT EXISTS quality_meta   jsonb,
  ADD COLUMN IF NOT EXISTS operation_phase smallint NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS operation_phase_type text;

COMMENT ON TABLE public.fact_measurements IS '事实表（秒级对齐）。质量与相位字段用于行级数据过滤与追踪。';
COMMENT ON COLUMN public.fact_measurements.quality_status IS '数据质量状态码：0=正常；>0 为异常码（参见 quality_code_dict）。';
COMMENT ON COLUMN public.fact_measurements.quality_type   IS '数据质量中文标签（如：越界、异常跳变、平台期、状态矛盾、功率因数异常、液位流量守恒异常等）。';
COMMENT ON COLUMN public.fact_measurements.quality_meta   IS '质量判定元数据（JSON）：阈值、证据、参与信号、相位、规则版本等。';
COMMENT ON COLUMN public.fact_measurements.operation_phase IS '运行相位：0=未知/未标注；1=运行(稳态)；2=启动中；3=停止中。';
COMMENT ON COLUMN public.fact_measurements.operation_phase_type IS '运行相位中文标签（如：稳态、启动中、停止中）。';

COMMIT;

