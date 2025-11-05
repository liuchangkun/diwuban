-- 修复 sp_refresh_metric_rule_auto_baseline_win：从 mv_device_running_1s 读取 phase 数据
-- 问题：原存储过程从 fact_measurements 表查找 device_phase 和 device_running 指标，但该数据实际在 mv_device_running_1s 中
-- 解决：修改 base CTE，INNER JOIN mv_device_running_1s 表，使用 phase=1 过滤稳态数据
-- 兼容：如果 phase 为 NULL，回退到 running=1 判断

BEGIN;

CREATE OR REPLACE PROCEDURE public.sp_refresh_metric_rule_auto_baseline_win(
  IN p_start_ts timestamptz,
  IN p_end_ts   timestamptz,
  IN p_station_id bigint DEFAULT NULL,
  IN p_device_id  bigint DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
  -- 清理同范围（按 station/device 粗略筛选；为幂等可直接删除 station/device 维度匹配行）
  DELETE FROM public.metric_rule_auto_baseline b
  WHERE (p_station_id IS NULL OR b.station_id = p_station_id)
    AND (p_device_id  IS NULL OR b.device_id  = p_device_id);

  WITH base AS (
    SELECT fm.station_id, fm.device_id, fm.metric_id, fm.ts_bucket, fm.value
    FROM public.fact_measurements fm
    -- 关键修改：从 mv_device_running_1s 获取 phase 数据，替代原来从 fact_measurements 查找 device_phase/device_running 指标
    INNER JOIN public.mv_device_running_1s mvr
      ON mvr.station_id = fm.station_id 
     AND mvr.device_id = fm.device_id 
     AND mvr.ts_bucket = fm.ts_bucket
     AND (mvr.phase = 1 OR (mvr.phase IS NULL AND mvr.running = 1))  -- 稳态数据或运行数据（兼容）
    WHERE fm.ts_bucket >= p_start_ts AND fm.ts_bucket < p_end_ts
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
         'win:robust_pcnt+mv',
         a.p05, a.p95, a.median, a.mad,
         g.spike_abs, g.roc_abs, g.roc_ratio,
         GREATEST(0.0, a.mad*0.5) AS flatline_eps,
         GREATEST(0.0, a.mad*1.0) AS flatline_delta,
         now(), 'v070'
  FROM agg a
  LEFT JOIN dv_aggs g ON g.station_id=a.station_id AND g.device_id=a.device_id AND g.metric_id=a.metric_id;
END;
$$;

COMMENT ON PROCEDURE public.sp_refresh_metric_rule_auto_baseline_win(timestamptz, timestamptz, bigint, bigint)
IS '带时间窗的自动基线过程：使用 [p_start_ts,p_end_ts) 内质量=0且稳态(从mv_device_running_1s.phase=1判定)的数据计算参数。v070: 修复从mv读取phase。';

COMMIT;

