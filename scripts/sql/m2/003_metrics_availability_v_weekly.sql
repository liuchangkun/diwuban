-- 逐周指标可用性与缺失分类视图（阈值0.99，按全历史逐周统计）
-- 说明：仅只读视图，不改动事实层；覆盖率=present_secs/604800

CREATE OR REPLACE VIEW public.metrics_availability_v_weekly AS
WITH weeks AS (
    SELECT DISTINCT date_trunc('week', ts_bucket) AS week_start
    FROM public.fact_measurements
),
present AS (
    SELECT station_id,
           device_id,
           metric_id,
           date_trunc('week', ts_bucket) AS week_start,
           COUNT(*)::bigint AS present_secs
    FROM public.fact_measurements
    GROUP BY 1,2,3,4
),
expected AS (
    SELECT s.id AS station_id,
           d.id AS device_id,
           mc.id AS metric_id,
           mc.metric_key
    FROM public.dim_mapping_items mi
    JOIN public.dim_stations s ON s.name = mi.station_name
    JOIN public.dim_devices d ON d.station_id = s.id AND d.name = mi.device_name
    JOIN public.dim_metric_config mc ON mc.metric_key = mi.metric_key
)
SELECT e.station_id,
       e.device_id,
       e.metric_id,
       e.metric_key,
       w.week_start,
       COALESCE(p.present_secs, 0) AS present_secs,
       7*24*3600::bigint          AS total_secs,
       (COALESCE(p.present_secs,0)::double precision)/(7*24*3600) AS coverage_rate,
       mcp.acquisition_status,
       mcp.compute_flag,
       CASE
         WHEN mcp.acquisition_status='不能' AND mcp.compute_flag='需要' THEN 'compute_required'
         WHEN mcp.acquisition_status='不能' AND mcp.compute_flag='不需要' THEN 'not_computable'
         WHEN mcp.acquisition_status IN ('可以','可能') AND
              (COALESCE(p.present_secs,0)::double precision)/(7*24*3600) >= 0.99 THEN 'available'
         ELSE 'missing_raw'
       END AS status
FROM weeks w
CROSS JOIN expected e
LEFT JOIN present p ON p.station_id=e.station_id AND p.device_id=e.device_id AND p.metric_id=e.metric_id AND p.week_start=w.week_start
LEFT JOIN public.metric_capability_policy mcp ON mcp.metric_key = e.metric_key;

COMMENT ON VIEW public.metrics_availability_v_weekly IS '逐周指标可用性与缺失分类视图：按周统计覆盖率；阈值0.99；结合策略表输出 available/missing_raw/compute_required/not_computable。\n使用示例：\nSELECT * FROM public.metrics_availability_v_weekly\nWHERE week_start >= date_trunc(''week'', now()) - interval ''4 weeks''\nORDER BY station_id, device_id, metric_id, week_start\nLIMIT 200;';
COMMENT ON COLUMN public.metrics_availability_v_weekly.station_id IS '站点ID';
COMMENT ON COLUMN public.metrics_availability_v_weekly.device_id IS '设备ID';
COMMENT ON COLUMN public.metrics_availability_v_weekly.metric_id IS '指标ID（dim_metric_config.id）';
COMMENT ON COLUMN public.metrics_availability_v_weekly.metric_key IS '指标键（dim_metric_config.metric_key）';
COMMENT ON COLUMN public.metrics_availability_v_weekly.week_start IS '周起始(UTC)';
COMMENT ON COLUMN public.metrics_availability_v_weekly.present_secs IS '该周存在的秒数（行数）';
COMMENT ON COLUMN public.metrics_availability_v_weekly.total_secs IS '该周总秒数=604800';
COMMENT ON COLUMN public.metrics_availability_v_weekly.coverage_rate IS '覆盖率=present_secs/total_secs';
COMMENT ON COLUMN public.metrics_availability_v_weekly.acquisition_status IS '获取情况：不能/可能/可以';
COMMENT ON COLUMN public.metrics_availability_v_weekly.compute_flag IS '是否计算补充：需要/不需要';
COMMENT ON COLUMN public.metrics_availability_v_weekly.status IS '分类：available/missing_raw/compute_required/not_computable';

