-- 目的：基于近N天“有效且稳态”的历史数据，自动计算各设备×指标的基线阈值，减少人工干预
-- 用法：CALL public.sp_refresh_metric_rule_auto_baseline(30, NULL, NULL);

BEGIN;

CREATE OR REPLACE PROCEDURE public.sp_refresh_metric_rule_auto_baseline(
  IN p_lookback_days int DEFAULT 30,
  IN p_station_id bigint DEFAULT NULL,
  IN p_device_id  bigint DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_start timestamptz := now() - make_interval(days => p_lookback_days);
  v_end   timestamptz := now();
  v_phase_metric_id bigint;
  v_running_metric_id bigint;
BEGIN
  -- 获取相位与运行指标ID
  SELECT id INTO v_phase_metric_id FROM public.dim_metric_config WHERE metric_key='device_phase';
  SELECT id INTO v_running_metric_id FROM public.dim_metric_config WHERE metric_key='device_running';

  -- 删除同范围的旧基线，避免重复累积（也可改为保留多版本）
  DELETE FROM public.metric_rule_auto_baseline b
  WHERE b.lookback_days = p_lookback_days
    AND (p_station_id IS NULL OR b.station_id = p_station_id)
    AND (p_device_id  IS NULL OR b.device_id  = p_device_id);

  -- 计算中位数 per 组（供 MAD 计算使用）
  WITH base AS (
    SELECT fm.station_id, fm.device_id, fm.metric_id, fm.ts_bucket, fm.value
    FROM public.fact_measurements fm
    JOIN public.fact_measurements ph
      ON ph.station_id=fm.station_id AND ph.device_id=fm.device_id AND ph.ts_bucket=fm.ts_bucket
     AND (
       (v_phase_metric_id IS NOT NULL AND ph.metric_id=v_phase_metric_id AND ph.value=1) OR
       (v_phase_metric_id IS NULL AND v_running_metric_id IS NOT NULL AND ph.metric_id=v_running_metric_id AND ph.value=1)
     )
    WHERE fm.ts_bucket >= v_start AND fm.ts_bucket < v_end
      AND (p_station_id IS NULL OR fm.station_id = p_station_id)
      AND (p_device_id  IS NULL OR fm.device_id  = p_device_id)
      AND COALESCE(fm.quality_status,0) = 0
      AND fm.value IS NOT NULL
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
  ), agg AS (
    SELECT m.station_id, m.device_id, m.metric_id,
           /* 分位数 */
           percentile_cont(0.05) WITHIN GROUP (ORDER BY b.value)::float8 AS p05,
           percentile_cont(0.95) WITHIN GROUP (ORDER BY b.value)::float8 AS p95,
           m.median,
           /* MAD 估计：median(|x - median|) */
           percentile_cont(0.5) WITHIN GROUP (ORDER BY ABS(b.value - m.median))::float8 AS mad,
           /* 跳变与速率建议：高分位的差分与相对差分 */
           percentile_cont(0.99) WITHIN GROUP (ORDER BY d.dv) FILTER (WHERE d.dv IS NOT NULL)::float8 AS spike_abs,
           percentile_cont(0.99) WITHIN GROUP (ORDER BY d.dv) FILTER (WHERE d.dv IS NOT NULL)::float8 AS roc_abs,
           percentile_cont(0.99) WITHIN GROUP (ORDER BY d.dv_ratio) FILTER (WHERE d.dv_ratio IS NOT NULL)::float8 AS roc_ratio
    FROM med m
    JOIN base b ON b.station_id=m.station_id AND b.device_id=m.device_id AND b.metric_id=m.metric_id
    LEFT JOIN dif  d ON d.station_id=m.station_id AND d.device_id=m.device_id AND d.metric_id=m.metric_id AND d.value=b.value
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
         p_lookback_days, 'robust_pcnt',
         a.p05, a.p95, a.median, a.mad,
         a.spike_abs, a.roc_abs, a.roc_ratio,
         /* 平台期建议：以 MAD 的倍数给出保守建议（可后续替换为滑窗统计）*/
         GREATEST(0.0, a.mad*0.5) AS flatline_eps,
         GREATEST(0.0, a.mad*1.0) AS flatline_delta,
         now(), 'v1'
  FROM agg a;
END;
$$;

COMMENT ON PROCEDURE public.sp_refresh_metric_rule_auto_baseline(int, bigint, bigint)
IS '自动基线过程：近N天有效(quality=0)且稳态(由 device_phase=1 判定)数据，计算分位数/MAD/差分分布，写入 metric_rule_auto_baseline。';

COMMIT;

