-- 目的：度量质量规则阈值（手工覆盖用），支持按站/设备/指标粒度配置

BEGIN;

CREATE TABLE IF NOT EXISTS public.metric_quality_rules(
  rule_id bigserial PRIMARY KEY,
  station_id bigint NULL,
  device_id  bigint NULL,
  metric_id  bigint NOT NULL,
  -- 数值区间
  value_min double precision NULL,
  value_max double precision NULL,
  -- 跳变/速率
  spike_abs double precision NULL,
  roc_abs   double precision NULL,
  roc_ratio double precision NULL,
  -- 平台期
  flatline_secs  int NULL,
  flatline_eps   double precision NULL,
  flatline_delta double precision NULL,
  -- 饱和
  saturation_min double precision NULL,
  saturation_max double precision NULL,
  -- 噪声
  noise_stddev_max double precision NULL,
  -- 备注与审计
  remark text NULL,
  updated_at timestamptz DEFAULT now(),
  updated_by text
);

COMMENT ON TABLE public.metric_quality_rules IS '度量质量规则阈值（手工覆盖）。用于越界/跳变/速率/平台期等常规规则的参数管理。';
COMMENT ON COLUMN public.metric_quality_rules.station_id IS '站点ID（可空，表示全站通用默认）。';
COMMENT ON COLUMN public.metric_quality_rules.device_id  IS '设备ID（可空，表示该站点通用或全局默认）。';
COMMENT ON COLUMN public.metric_quality_rules.metric_id  IS '指标ID（必填）。';
COMMENT ON COLUMN public.metric_quality_rules.value_min IS '越界下限（可空则使用自动基线 p05）。';
COMMENT ON COLUMN public.metric_quality_rules.value_max IS '越界上限（可空则使用自动基线 p95）。';
COMMENT ON COLUMN public.metric_quality_rules.spike_abs IS '异常跳变阈值（相邻秒绝对差）。';
COMMENT ON COLUMN public.metric_quality_rules.roc_abs   IS '变化率绝对差阈值。';
COMMENT ON COLUMN public.metric_quality_rules.roc_ratio IS '相对变化率阈值（|Δx/prev|）。';
COMMENT ON COLUMN public.metric_quality_rules.flatline_secs  IS '平台期判定最小持续秒数。';
COMMENT ON COLUMN public.metric_quality_rules.flatline_eps   IS '平台期窗口内标准差上限。';
COMMENT ON COLUMN public.metric_quality_rules.flatline_delta IS '平台期窗口内最大-最小差上限。';
COMMENT ON COLUMN public.metric_quality_rules.saturation_min IS '下饱和阈值。';
COMMENT ON COLUMN public.metric_quality_rules.saturation_max IS '上饱和阈值。';
COMMENT ON COLUMN public.metric_quality_rules.noise_stddev_max IS '短窗噪声标准差上限。';
COMMENT ON COLUMN public.metric_quality_rules.remark IS '中文备注/规则说明。';

COMMIT;

