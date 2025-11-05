-- 046_create_calc_config_tables.sql
-- 目的：新增计算相关配置/方法/标定/验证四张表；不修改 fact_measurements 结构
-- 口径：统一使用 metric_id（FK dim_metric_config）；窗口按 [start,end)；逐点以 ts_bucket 秒级对齐（由应用侧保证）

BEGIN;

/* 1) 指标计算配置：按设备×指标控制开关与优先级（device_id 可空表示默认） */
CREATE TABLE IF NOT EXISTS public.metric_calculation_config (
  id                 bigserial PRIMARY KEY,
  device_id          bigint NULL REFERENCES public.dim_devices(id),
  metric_id          bigint NOT NULL REFERENCES public.dim_metric_config(id),
  calculation_enabled boolean NOT NULL DEFAULT true,
  priority_level     smallint NOT NULL DEFAULT 0,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE  public.metric_calculation_config IS '指标计算配置：按设备×指标控制是否计算与优先级（device_id可空表示默认；应用侧合并优先级）';
COMMENT ON COLUMN public.metric_calculation_config.device_id IS '设备ID：可为空，表示默认配置（优先级合并策略由应用层定义）';
COMMENT ON COLUMN public.metric_calculation_config.metric_id IS '指标ID（FK dim_metric_config.id）';
COMMENT ON COLUMN public.metric_calculation_config.calculation_enabled IS '是否启用该指标的计算（true/false）';
COMMENT ON COLUMN public.metric_calculation_config.priority_level IS '优先级（0为默认，值越大优先）';
CREATE UNIQUE INDEX IF NOT EXISTS ux_mcc_dev_metric ON public.metric_calculation_config(device_id, metric_id);
CREATE INDEX IF NOT EXISTS idx_mcc_metric ON public.metric_calculation_config(metric_id);

/* 2) 计算方法选择：登记方法及适用条件/所需输入/公式/精度 */
CREATE TABLE IF NOT EXISTS public.calculation_method_selector (
  method_id          bigserial PRIMARY KEY,
  method_name        text NOT NULL UNIQUE,
  applicable_metrics text[] NOT NULL DEFAULT '{}'::text[],
  required_inputs    text[] NOT NULL DEFAULT '{}'::text[],
  calculation_formula text NULL,
  accuracy_level     smallint NULL,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE  public.calculation_method_selector IS '计算方法选择表：存储方法名称、适用指标（metric_key 列表）、所需输入、公式说明与精度评级';
COMMENT ON COLUMN public.calculation_method_selector.method_name IS '方法名称（唯一）';
COMMENT ON COLUMN public.calculation_method_selector.applicable_metrics IS '适用指标集合（metric_key 列表，如 {pump_head,pump_efficiency}）';
COMMENT ON COLUMN public.calculation_method_selector.required_inputs IS '所需输入指标集合（metric_key 列表，如 {pump_active_power,pump_flow_rate}）';
COMMENT ON COLUMN public.calculation_method_selector.calculation_formula IS '计算公式/伪代码/参考（Markdown 文本）';
COMMENT ON COLUMN public.calculation_method_selector.accuracy_level IS '精度评级（小整数，数值越大表示经验上更可靠）';
CREATE INDEX IF NOT EXISTS idx_cms_accuracy ON public.calculation_method_selector(accuracy_level);

/* 3) RLS 参数标定：按设备记录每次标定的参数值与性能评分 */
CREATE TABLE IF NOT EXISTS public.rls_parameter_calibration (
  id                bigserial PRIMARY KEY,
  device_id         bigint NOT NULL REFERENCES public.dim_devices(id),
  parameter_name    text   NOT NULL,
  parameter_value   double precision NOT NULL,
  calibration_date  timestamptz NOT NULL DEFAULT now(),
  performance_score double precision NULL,
  remark            text NULL
);

COMMENT ON TABLE  public.rls_parameter_calibration IS 'RLS参数标定历史：记录设备级关键参数的每次标定结果与表现评分';
COMMENT ON COLUMN public.rls_parameter_calibration.parameter_name IS '参数名称（如：eta_coeff_a、eta_coeff_b、loss_k 等）';
COMMENT ON COLUMN public.rls_parameter_calibration.parameter_value IS '参数数值（double precision）';
COMMENT ON COLUMN public.rls_parameter_calibration.calibration_date IS '标定时间（默认 now()）';
COMMENT ON COLUMN public.rls_parameter_calibration.performance_score IS '本次标定在验证集上的得分/拟合优度等';
CREATE INDEX IF NOT EXISTS idx_rls_dev_param_time ON public.rls_parameter_calibration(device_id, parameter_name, calibration_date DESC);

/* 4) 计算结果验证：按 calculation_id 留痕各类验证（物理约束/特性曲线等） */
CREATE TABLE IF NOT EXISTS public.calculation_result_validation (
  id                   bigserial PRIMARY KEY,
  calculation_id       text NOT NULL,
  validation_type      text NOT NULL,
  validation_result    boolean NOT NULL,
  failure_reason       text NULL,
  validation_timestamp timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE  public.calculation_result_validation IS '计算结果验证留痕：按计算ID记录物理约束/特性曲线等验证通过/失败与原因';
COMMENT ON COLUMN public.calculation_result_validation.calculation_id IS '计算ID（应用侧生成的全局ID/UUID），用于关联一次计算';
COMMENT ON COLUMN public.calculation_result_validation.validation_type IS '验证类型（如：物理约束/特性曲线/边界条件/单调性等）';
COMMENT ON COLUMN public.calculation_result_validation.validation_result IS '验证结论：true=通过，false=失败';
COMMENT ON COLUMN public.calculation_result_validation.failure_reason IS '失败原因（结构化/半结构化文本，必要时包含统计量）';
CREATE INDEX IF NOT EXISTS idx_crv_calcid_time ON public.calculation_result_validation(calculation_id, validation_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_crv_type_time   ON public.calculation_result_validation(validation_type, validation_timestamp DESC);

COMMIT;

