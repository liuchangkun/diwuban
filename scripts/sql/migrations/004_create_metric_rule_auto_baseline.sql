-- 目的：自动基线（来自历史有效数据的统计），减少人工干预

BEGIN;

CREATE TABLE IF NOT EXISTS public.metric_rule_auto_baseline(
  baseline_id bigserial PRIMARY KEY,
  station_id bigint NULL,
  device_id  bigint NULL,
  metric_id  bigint NOT NULL,
  lookback_days int NOT NULL,
  method text NOT NULL,
  -- 分布统计
  p05 double precision,
  p95 double precision,
  median double precision,
  mad double precision,
  -- 跳变/速率建议
  spike_abs double precision,
  roc_abs   double precision,
  roc_ratio double precision,
  -- 平台期建议
  flatline_eps   double precision,
  flatline_delta double precision,
  -- 审计
  computed_at timestamptz DEFAULT now(),
  version text
);

COMMENT ON TABLE public.metric_rule_auto_baseline IS '自动基线：从历史有效(quality=0)且稳态(operation_phase=1)数据计算出的缺省阈值。';
COMMENT ON COLUMN public.metric_rule_auto_baseline.station_id IS '站点ID（可空表示全局/设备默认）。';
COMMENT ON COLUMN public.metric_rule_auto_baseline.device_id  IS '设备ID（可空表示站点/全局默认）。';
COMMENT ON COLUMN public.metric_rule_auto_baseline.metric_id  IS '指标ID（必填）。';
COMMENT ON COLUMN public.metric_rule_auto_baseline.lookback_days IS '回溯天数，用于确定历史窗口大小。';
COMMENT ON COLUMN public.metric_rule_auto_baseline.method IS '计算方法（如：robust_pcnt, rolling_mad 等）。';
COMMENT ON COLUMN public.metric_rule_auto_baseline.p05 IS '第5分位数。';
COMMENT ON COLUMN public.metric_rule_auto_baseline.p95 IS '第95分位数。';
COMMENT ON COLUMN public.metric_rule_auto_baseline.median IS '中位数。';
COMMENT ON COLUMN public.metric_rule_auto_baseline.mad IS 'Median Absolute Deviation（稳健散度）。';
COMMENT ON COLUMN public.metric_rule_auto_baseline.spike_abs IS '异常跳变建议阈值（绝对差）。';
COMMENT ON COLUMN public.metric_rule_auto_baseline.roc_abs   IS '变化率绝对差建议阈值。';
COMMENT ON COLUMN public.metric_rule_auto_baseline.roc_ratio IS '相对变化率建议阈值。';
COMMENT ON COLUMN public.metric_rule_auto_baseline.flatline_eps   IS '平台期窗口标准差建议阈值。';
COMMENT ON COLUMN public.metric_rule_auto_baseline.flatline_delta IS '平台期窗口极差建议阈值。';
COMMENT ON COLUMN public.metric_rule_auto_baseline.computed_at IS '自动基线计算时间。';
COMMENT ON COLUMN public.metric_rule_auto_baseline.version IS '算法或规则版本。';

COMMIT;

