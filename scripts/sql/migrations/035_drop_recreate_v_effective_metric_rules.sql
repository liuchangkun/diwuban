BEGIN;

-- 重新创建视图：在末尾追加 flatline_secs 列（仅手工规则侧提供），保持原有列顺序与名称不变
DROP VIEW IF EXISTS public.v_effective_metric_rules;

CREATE VIEW public.v_effective_metric_rules AS
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
  -- 平台期（保持原有列名与顺序）
  COALESCE(r.flatline_eps,   b.flatline_eps)   AS flatline_eps,
  COALESCE(r.flatline_delta, b.flatline_delta) AS flatline_delta,
  -- 新增列（末尾追加）：最小持续秒数，仅来自手工规则，自动基线为 NULL
  r.flatline_secs AS flatline_secs
FROM public.metric_quality_rules r
FULL JOIN public.metric_rule_auto_baseline b
  ON r.metric_id = b.metric_id
 AND (r.station_id IS NOT DISTINCT FROM b.station_id)
 AND (r.device_id  IS NOT DISTINCT FROM b.device_id);

COMMENT ON VIEW public.v_effective_metric_rules IS '生效规则：手工优先，自动基线兜底；末尾追加 flatline_secs（仅手工）以支持平台期最小持续秒数。';

COMMIT;

