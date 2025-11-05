-- 目的：带窗口版本的自动基线过程，使用给定时间窗计算各设备×指标基线
-- 用法：CALL public.sp_refresh_metric_rule_auto_baseline_win('2025-02-27T18:00:00Z','2025-02-27T20:00:00Z', NULL, NULL);

BEGIN;

CREATE OR REPLACE PROCEDURE public.sp_refresh_metric_rule_auto_baseline_win(
  IN p_start_ts timestamptz,
  IN p_end_ts   timestamptz,
  IN p_station_id bigint DEFAULT NULL,
  IN p_device_id  bigint DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_phase_metric_id bigint;
  v_running_metric_id bigint;
BEGIN
  SELECT id INTO v_phase_metric_id FROM public.dim_metric_config WHERE metric_key='device_phase';
  SELECT id INTO v_running_metric_id FROM public.dim_metric_config WHERE metric_key='device_running';

  -- 清理同范围（按 station/device 粗略筛选；为幂等可直接删除 station/device 维度匹配行）
  DELETE FROM public.metric_rule_auto_baseline b
  WHERE (p_station_id IS NULL OR b.station_id = p_station_id)
    AND (p_device_id  IS NULL OR b.device_id  = p_device_id);

  WITH base AS (
    SELECT fm.station_id, fm.device_id, fm.metric_id, fm.ts_bucket, fm.value
    FROM public.fact_measurements fm
    LEFT JOIN public.fact_measurements ph
      ON ph.station_id=fm.station_id AND ph.device_id=fm.device_id AND ph.ts_bucket=fm.ts_bucket
     AND v_phase_metric_id IS NOT NULL AND ph.metric_id=v_phase_metric_id AND ph.value=1
    LEFT JOIN public.fact_measurements frun
      ON frun.station_id=fm.station_id AND frun.device_id=fm.device_id AND frun.ts_bucket=fm.ts_bucket
     AND v_running_metric_id IS NOT NULL AND frun.metric_id=v_running_metric_id AND frun.value=1
    WHERE fm.ts_bucket >= p_start_ts AND fm.ts_bucket < p_end_ts
      AND (p_station_id IS NULL OR fm.station_id = p_station_id)
      AND (p_device_id  IS NULL OR fm.device_id  = p_device_id)
      AND COALESCE(fm.quality_status,0) = 0
      AND fm.value IS NOT NULL
      AND (ph.ts_bucket IS NOT NULL OR frun.ts_bucket IS NOT NULL)
  ), med AS (
    SELECT station_id, device_id, metric_id,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY value)::float8 AS median
    FROM base
    GROUP BY station_id, device_id, metric_id
  ), dif AS (
    SELECT b.station_id, b.device_id, b.metric_id,
           b.value,
           LAG(b.value) OVER (PARTITION BY b.station_id,b.device_id,b.metric_id ORDER BY b.ts_bucket) AS prev_val,
           ABS(b.value - LAG(b.value) OVER (PARTITION BY b.station_id,b.device_id,b.metric_id ORDER BY b.ts_bucket)) AS dv,
           CASE WHEN ABS(LAG(b.value) OVER (PARTITION BY b.station_id,b.device_id,b.metric_id ORDER BY b.ts_bucket)) > 0
                THEN ABS(b.value - LAG(b.value) OVER (PARTITION BY b.station_id,b.device_id,b.metric_id ORDER BY b.ts_bucket))
                     / ABS(LAG(b.value) OVER (PARTITION BY b.station_id,b.device_id,b.metric_id ORDER BY b.ts_bucket))
                ELSE NULL END AS dv_ratio
    FROM base b
  ), dv_aggs AS (
    SELECT station_id, device_id, metric_id,
           percentile_cont(0.99) WITHIN GROUP (ORDER BY dv) FILTER (WHERE dv IS NOT NULL)::float8 AS spike_abs,
           percentile_cont(0.99) WITHIN GROUP (ORDER BY dv) FILTER (WHERE dv IS NOT NULL)::float8 AS roc_abs,
           percentile_cont(0.99) WITHIN GROUP (ORDER BY dv_ratio) FILTER (WHERE dv_ratio IS NOT NULL)::float8 AS roc_ratio
    FROM dif
    GROUP BY station_id, device_id, metric_id
  ), agg AS (
    SELECT m.station_id, m.device_id, m.metric_id,
           percentile_cont(0.05) WITHIN GROUP (ORDER BY b.value)::float8 AS p05,
           percentile_cont(0.95) WITHIN GROUP (ORDER BY b.value)::float8 AS p95,
           m.median,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY ABS(b.value - m.median))::float8 AS mad
    FROM med m
    JOIN base b ON b.station_id=m.station_id AND b.device_id=m.device_id AND b.metric_id=m.metric_id
    GROUP BY m.station_id, m.device_id, m.metric_id, m.median
  )
  INSERT INTO public.metric_rule_auto_baseline(
    station_id, device_id, metric_id,
    lookback_days, method,
    p05, p95, median, mad,
    spike_abs, roc_abs, roc_ratio,
    flatline_eps, flatline_delta,
    computed_at, version
  )
  SELECT a.station_id, a.device_id, a.metric_id,
         GREATEST(1, EXTRACT(EPOCH FROM (p_end_ts - p_start_ts))/86400)::int AS lookback_days,
         'win:robust_pcnt',
         a.p05, a.p95, a.median, a.mad,
         NULL::float8 AS spike_abs, NULL::float8 AS roc_abs, NULL::float8 AS roc_ratio,
         GREATEST(0.0, a.mad*0.5) AS flatline_eps,
         GREATEST(0.0, a.mad*1.0) AS flatline_delta,
         now(), 'v1'
  FROM agg a;
END;
$$;

COMMENT ON PROCEDURE public.sp_refresh_metric_rule_auto_baseline_win(timestamptz, timestamptz, bigint, bigint)
IS '带时间窗的自动基线过程：使用 [p_start_ts,p_end_ts) 内质量=0且稳态(phase=1或running=1)的数据计算参数。';

COMMIT;

