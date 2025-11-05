-- 050: 方法目录与规则表（阶段1）
BEGIN;

-- 1) 计算方法目录：每种方法一行，用于声明依赖与适用范围（不含规则）
CREATE TABLE IF NOT EXISTS public.metric_compute_method_catalog (
  method_code text PRIMARY KEY,
  metric_key  text NOT NULL,                            -- 目标指标键（如 pump_flow_rate）
  description text NULL,                                -- 中文说明
  required_inputs text[] NOT NULL DEFAULT '{}'::text[], -- 依赖输入的 metric_key 列表（仅声明，不做过滤）
  require_station_level boolean NOT NULL DEFAULT false, -- 是否需要泵站级数据
  require_running smallint NULL,                        -- 运行要求：NULL=不限；1=要求运行；0=要求停机
  require_phase smallint[] NULL,                        -- 相位要求：{1}=稳态；{2,3}=启停等
  notes text NULL,
  updated_at timestamptz NOT NULL DEFAULT now(),
  updated_by text NULL
);

COMMENT ON TABLE  public.metric_compute_method_catalog IS '计算方法目录：声明方法依赖与适用性，用于方法选择器参考（非配置表）。';
COMMENT ON COLUMN public.metric_compute_method_catalog.method_code IS '方法唯一编码（如 head_from_dp, eff_from_pqh）。';
COMMENT ON COLUMN public.metric_compute_method_catalog.metric_key  IS '目标指标键（与 dim_metric_config.metric_key 对齐）。';
COMMENT ON COLUMN public.metric_compute_method_catalog.required_inputs IS '该方法所需的输入指标键集合。';
COMMENT ON COLUMN public.metric_compute_method_catalog.require_station_level IS '是否为泵站级方法（需要全站数据）。';
COMMENT ON COLUMN public.metric_compute_method_catalog.require_running IS '运行状态要求：NULL=不限；1=运行；0=停机。';
COMMENT ON COLUMN public.metric_compute_method_catalog.require_phase   IS '相位要求（smallint枚举）：0未知/1稳态/2启动/3停止。';

-- 2) 方法选择规则：可按 metric_key + 作用域（站/设备/型号）配置优先级
CREATE TABLE IF NOT EXISTS public.metric_compute_method_rules (
  rule_id bigserial PRIMARY KEY,
  metric_key  text NOT NULL,
  station_id  bigint NULL,
  device_id   bigint NULL,
  device_type text NULL,
  model       text NULL,
  priority    smallint NOT NULL,                         -- 1=最高优先级，数值越小越优先
  method_code text NOT NULL REFERENCES public.metric_compute_method_catalog(method_code),
  effective_from timestamptz NULL,
  effective_to   timestamptz NULL,
  enabled boolean NOT NULL DEFAULT true,
  min_input_coverage numeric NULL,                       -- 最小可用输入占比（0~1），用于 presence 判定，不越界于质量窗口
  remark text NULL,
  updated_at timestamptz NOT NULL DEFAULT now(),
  updated_by text NULL
);

COMMENT ON TABLE  public.metric_compute_method_rules IS '方法选择规则：按指标与作用域配置方法优先级与生效区间。';
COMMENT ON COLUMN public.metric_compute_method_rules.metric_key  IS '目标指标键。';
COMMENT ON COLUMN public.metric_compute_method_rules.station_id  IS '限定站点（可空=全局）。';
COMMENT ON COLUMN public.metric_compute_method_rules.device_id   IS '限定设备（可空=全局）。';
COMMENT ON COLUMN public.metric_compute_method_rules.device_type IS '限定设备类型/型号（可空）。';
COMMENT ON COLUMN public.metric_compute_method_rules.priority    IS '优先级：1为最高；当多条命中时取数字最小者。';
COMMENT ON COLUMN public.metric_compute_method_rules.method_code IS '引用方法目录的编码。';
COMMENT ON COLUMN public.metric_compute_method_rules.min_input_coverage IS '方法可用的最低输入覆盖率（按 presence 统计）。';

-- 索引与唯一性建议
CREATE INDEX IF NOT EXISTS idx_mcmr_metric_scope_pri ON public.metric_compute_method_rules(metric_key, station_id, device_id, priority);
CREATE INDEX IF NOT EXISTS idx_mcmr_enabled_metric   ON public.metric_compute_method_rules(enabled, metric_key);

COMMIT;

