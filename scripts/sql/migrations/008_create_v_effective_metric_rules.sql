-- 目的：统一“手工规则表 + 自动基线表”的生效视图（优先手工，缺省用自动）

BEGIN;

CREATE OR REPLACE VIEW public.v_effective_metric_rules (
  station_id, device_id, metric_id,
  value_min, value_max,
  spike_abs, roc_abs, roc_ratio,
  flatline_secs, flatline_eps, flatline_delta
) AS
SELECT
  COALESCE(r.station_id, b.station_id) AS station_id,
  COALESCE(r.device_id,  b.device_id)  AS device_id,
  COALESCE(r.metric_id,  b.metric_id)  AS metric_id,
  -- 数值区间：手工优先，否则采用自动基线分位数
  COALESCE(r.value_min, b.p05) AS value_min,
  COALESCE(r.value_max, b.p95) AS value_max,
  -- 跳变/速率：手工优先，否则采用自动建议
  COALESCE(r.spike_abs, b.spike_abs) AS spike_abs,
  COALESCE(r.roc_abs,   b.roc_abs)   AS roc_abs,
  COALESCE(r.roc_ratio, b.roc_ratio) AS roc_ratio,
  -- 平台期
  r.flatline_secs AS flatline_secs,
  COALESCE(r.flatline_eps,   b.flatline_eps)   AS flatline_eps,
  COALESCE(r.flatline_delta, b.flatline_delta) AS flatline_delta
FROM public.metric_quality_rules r
FULL JOIN public.metric_rule_auto_baseline b
  ON r.metric_id = b.metric_id
 AND (r.station_id IS NOT DISTINCT FROM b.station_id)
 AND (r.device_id  IS NOT DISTINCT FROM b.device_id);

COMMENT ON VIEW public.v_effective_metric_rules IS '生效的度量质量规则：手工规则优先，缺省用自动基线的统计建议值。';

COMMIT;

