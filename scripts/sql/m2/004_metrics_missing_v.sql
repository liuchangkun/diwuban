-- 缺失与待处理项视图（供计算/补采程序直接读取）

CREATE OR REPLACE VIEW public.metrics_missing_v AS
SELECT *,
       CASE
         WHEN status='compute_required' THEN 'compute'
         WHEN status='missing_raw'      THEN 'acquire'
         ELSE NULL
       END AS method_hint
FROM public.metrics_availability_v_weekly
WHERE status IN ('missing_raw','compute_required');

COMMENT ON VIEW public.metrics_missing_v IS '缺失与待处理视图：从逐周可用性视图中过滤出缺失与必须计算的项，并提供 method_hint=compute/acquire。\n使用示例：\nSELECT * FROM public.metrics_missing_v\nWHERE week_start >= date_trunc(''week'', now()) - interval ''8 weeks''\nORDER BY station_id, device_id, metric_id, week_start\nLIMIT 200;';
COMMENT ON COLUMN public.metrics_missing_v.method_hint IS '处理方式：compute=计算补齐；acquire=采集补齐';

