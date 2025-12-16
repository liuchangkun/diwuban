-- 任意开始/结束时间窗口的指标可用性/缺失分类函数
-- 输入：_start, _end（timestamptz，自动秒对齐；若 _start>_end 自动互换）
-- 输出：站点/设备/指标 + present_secs / total_secs / coverage_rate + status + method_hint

CREATE OR REPLACE FUNCTION public.metrics_availability_window(
    _start timestamptz,
    _end   timestamptz
) RETURNS TABLE (
    station_id int,
    device_id  int,
    metric_id  int,
    metric_key text,
    start_ts   timestamptz,
    end_ts     timestamptz,
    present_secs bigint,
    total_secs   bigint,
    coverage_rate double precision,
    acquisition_status text,
    compute_flag text,
    status text,
    method_hint text
) LANGUAGE sql AS $$
WITH bounds AS (
  SELECT LEAST(_start, _end) AS start_ts, GREATEST(_start, _end) AS end_ts
),
seconds_bounds AS (
  SELECT date_trunc('second', start_ts) AS start_ts,
         date_trunc('second', end_ts)   AS end_ts
  FROM bounds
),
present AS (
  SELECT fm.station_id,
         fm.device_id,
         fm.metric_id,
         mc.metric_key AS raw_metric_key,
         CASE mc.metric_key
           WHEN 'pump_voltage_a' THEN 'voltage_a'
           WHEN 'pump_voltage_b' THEN 'voltage_b'
           WHEN 'pump_voltage_c' THEN 'voltage_c'
           WHEN 'pump_current_a' THEN 'current_a'
           WHEN 'pump_current_b' THEN 'current_b'
           WHEN 'pump_current_c' THEN 'current_c'
           WHEN 'pump_active_power' THEN 'power'
           WHEN 'pump_kwh' THEN 'kwh'
           WHEN 'pump_power_factor' THEN 'power_factor'
           WHEN 'pump_frequency' THEN 'frequency'
           ELSE mc.metric_key
         END AS metric_key_norm,
         COUNT(*)::bigint AS present_secs
  FROM public.fact_measurements fm
  JOIN public.dim_metric_config mc ON mc.id = fm.metric_id
  CROSS JOIN seconds_bounds b
  WHERE fm.ts_bucket >= b.start_ts AND fm.ts_bucket <  b.end_ts
  GROUP BY 1,2,3,4,5
),
expected AS (
  SELECT s.id AS station_id, d.id AS device_id, mc.id AS metric_id, mc.metric_key
  FROM public.dim_mapping_items mi
  JOIN public.dim_stations s ON s.name = mi.station_name
  JOIN public.dim_devices d ON d.station_id = s.id AND d.name = mi.device_name
  JOIN public.dim_metric_config mc ON mc.metric_key = mi.metric_key
),
base AS (
  SELECT e.station_id, e.device_id, e.metric_id, e.metric_key,
         b.start_ts, b.end_ts,
         COALESCE(p.present_secs, 0) AS present_secs,
         (EXTRACT(EPOCH FROM (b.end_ts - b.start_ts))::bigint) AS total_secs
  FROM expected e
  CROSS JOIN seconds_bounds b
  LEFT JOIN present p ON p.station_id=e.station_id
                     AND p.device_id=e.device_id
                     AND p.metric_key_norm=e.metric_key
)
SELECT b.station_id, b.device_id, b.metric_id, b.metric_key,
       b.start_ts, b.end_ts, b.present_secs, b.total_secs,
       CASE WHEN b.total_secs>0 THEN b.present_secs::double precision/b.total_secs ELSE 0 END AS coverage_rate,
       COALESCE(mcp.acquisition_status,'可以') AS acquisition_status,
       COALESCE(mcp.compute_flag,'不需要')     AS compute_flag,
       CASE
         WHEN COALESCE(mcp.acquisition_status,'可以')='不能' AND COALESCE(mcp.compute_flag,'不需要')='需要' THEN 'compute_required'
         WHEN COALESCE(mcp.acquisition_status,'可以')='不能' AND COALESCE(mcp.compute_flag,'不需要')='不需要' THEN 'not_computable'
         WHEN COALESCE(mcp.acquisition_status,'可以') IN ('可以','可能') AND
              (CASE WHEN b.total_secs>0 THEN b.present_secs::double precision/b.total_secs ELSE 0 END) >= 0.99 THEN 'available'
         ELSE 'missing_raw'
       END AS status,
       CASE
         WHEN COALESCE(mcp.acquisition_status,'可以')='不能' AND COALESCE(mcp.compute_flag,'不需要')='需要' THEN 'compute'
         WHEN COALESCE(mcp.acquisition_status,'可以') IN ('可以','可能') AND
              (CASE WHEN b.total_secs>0 THEN b.present_secs::double precision/b.total_secs ELSE 0 END) < 0.99 THEN 'acquire'
         ELSE NULL
       END AS method_hint
FROM base b
LEFT JOIN public.metric_capability_policy mcp ON mcp.metric_key = b.metric_key;
$$;

COMMENT ON FUNCTION public.metrics_availability_window(timestamptz, timestamptz) IS '按任意开始/结束时间窗口计算设备×指标的覆盖率与分类（阈值0.99；结合策略表返回 status 与 method_hint）。\n使用示例：\nSELECT * FROM public.metrics_availability_window(''2025-02-27 00:00:00+00'',''2025-02-28 00:00:00+00'')\nORDER BY station_id, device_id, metric_id LIMIT 100;';

