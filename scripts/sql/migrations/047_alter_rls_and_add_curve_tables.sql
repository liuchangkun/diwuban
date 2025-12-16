-- 047_alter_rls_and_add_curve_tables.sql
-- 目的：按设备成套管理优化参数与标定；预留特性曲线接口用于第二层验证
-- 说明：不修改 fact_measurements 结构；与 046_* 表配套

BEGIN;

/* A) 设备级参数成套：头表 rls_parameter_set（每设备可有多套，唯一激活一套） */
CREATE TABLE IF NOT EXISTS public.rls_parameter_set (
  set_id          text PRIMARY KEY,
  device_id       bigint NOT NULL REFERENCES public.dim_devices(id),
  method_id       bigint NULL REFERENCES public.calculation_method_selector(method_id),
  label           text NULL,
  source          text NULL,
  performance_score double precision NULL,
  is_active       boolean NOT NULL DEFAULT false,
  activation_ts   timestamptz NULL,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE  public.rls_parameter_set IS 'RLS参数成套：设备级参数集合的头表，支持多套并标记唯一激活集（is_active）';
COMMENT ON COLUMN public.rls_parameter_set.set_id IS '参数集ID（建议UUID，由应用侧生成）';
COMMENT ON COLUMN public.rls_parameter_set.device_id IS '设备ID（dim_devices.id）';
COMMENT ON COLUMN public.rls_parameter_set.method_id IS '可选：关联计算方法（calculation_method_selector.method_id）';
COMMENT ON COLUMN public.rls_parameter_set.label IS '参数集标签/版本名';
COMMENT ON COLUMN public.rls_parameter_set.source IS '来源（拟合/人工/迁移等）';
COMMENT ON COLUMN public.rls_parameter_set.performance_score IS '该参数集在验证集上的表现评分';
COMMENT ON COLUMN public.rls_parameter_set.is_active IS '是否为当前激活参数集（每设备唯一激活）';
CREATE UNIQUE INDEX IF NOT EXISTS ux_rls_set_active_per_device
ON public.rls_parameter_set(device_id)
WHERE is_active;
CREATE INDEX IF NOT EXISTS idx_rls_set_device ON public.rls_parameter_set(device_id);

/* B) 细表 rls_parameter_calibration：补充 set_id 外键，支持将参数条目归属到某一成套 */
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='public' AND table_name='rls_parameter_calibration' AND column_name='set_id'
  ) THEN
    ALTER TABLE public.rls_parameter_calibration
      ADD COLUMN set_id text NULL REFERENCES public.rls_parameter_set(set_id);
  END IF;
END$$;

COMMENT ON COLUMN public.rls_parameter_calibration.set_id IS '归属参数集（rls_parameter_set.set_id），可为空以兼容历史数据';
CREATE INDEX IF NOT EXISTS idx_rls_param_set ON public.rls_parameter_calibration(set_id);

/* C) 特性曲线库：用于验证与优化（不直接参与基础计算） */
CREATE TABLE IF NOT EXISTS public.characteristic_curve_library (
  curve_id        bigserial PRIMARY KEY,
  device_id       bigint NULL REFERENCES public.dim_devices(id),
  curve_type      text NOT NULL CHECK (curve_type IN ('H-Q','eta-Q','P-Q')),
  fit_type        text NULL, -- polynomial/affinity/spline/other
  coefficients    jsonb NOT NULL, -- 系数数组或对象（{a0,a1,...} 或 [{x,y},...]）
  valid_from      timestamptz NULL,
  valid_to        timestamptz NULL,
  version_tag     text NULL,
  source          text NULL,
  performance_score double precision NULL,
  is_active       boolean NOT NULL DEFAULT false,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE  public.characteristic_curve_library IS '特性曲线库：存储设备/通用泵的H-Q/η-Q/P-Q曲线（第二层验证/优化使用，基础计算不直接依赖）';
COMMENT ON COLUMN public.characteristic_curve_library.device_id IS '设备ID：可为空表示通用曲线（按设备族/型号适用），为空时由应用层选择匹配规则';
COMMENT ON COLUMN public.characteristic_curve_library.curve_type IS '曲线类型：H-Q（扬程-流量）、eta-Q（效率-流量）、P-Q（功率-流量）';
COMMENT ON COLUMN public.characteristic_curve_library.fit_type IS '拟合类型：polynomial/affinity/spline/other';
COMMENT ON COLUMN public.characteristic_curve_library.coefficients IS '拟合系数或采样点，JSON结构';
COMMENT ON COLUMN public.characteristic_curve_library.is_active IS '是否为当前激活曲线（设备维度，唯一激活）';
CREATE INDEX IF NOT EXISTS idx_curve_device_type ON public.characteristic_curve_library(device_id, curve_type);
CREATE UNIQUE INDEX IF NOT EXISTS ux_curve_active_per_device_type
ON public.characteristic_curve_library(device_id, curve_type)
WHERE is_active;

COMMIT;

