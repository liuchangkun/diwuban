-- 修复 sp_refresh_metric_rule_auto_baseline：从 mv_device_running_1s 读取 phase 数据
-- 问题：原存储过程从 fact_measurements 表查找 device_phase 指标，但该数据实际在 mv_device_running_1s.phase 列中
-- 解决：修改 base CTE，INNER JOIN mv_device_running_1s 表，使用 phase=1 过滤稳态数据
-- 兼容：如果 phase 为 NULL，回退到 running=1 判断

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
BEGIN
  -- 删除同范围的旧基线，避免重复累积
  DELETE FROM public.metric_rule_auto_baseline b
  WHERE b.lookback_days = p_lookback_days
    AND (p_station_id IS NULL OR b.station_id = p_station_id)
    AND (p_device_id  IS NULL OR b.device_id  = p_device_id);

  WITH base AS (
    SELECT f.station_id, f.device_id, f.metric_id, f.ts_bucket, f.value::float8 AS value,
           meta.resolution, meta.phys_min, meta.phys_max
    FROM public.fact_measurements f
    -- 关键修改：从 mv_device_running_1s 获取 phase 数据，替代原来从 fact_measurements 查找 device_phase 指标
    INNER JOIN public.mv_device_running_1s mvr
      ON mvr.station_id = f.station_id 
     AND mvr.device_id = f.device_id 
     AND mvr.ts_bucket = f.ts_bucket
     AND (mvr.phase = 1 OR (mvr.phase IS NULL AND mvr.running = 1))  -- 稳态数据或运行数据（兼容）
    -- 元数据（设备>站点>全局优先级）
    LEFT JOIN LATERAL (
      SELECT resolution, phys_min, phys_max
      FROM public.v_effective_metric_metadata vm
      WHERE vm.metric_id = f.metric_id
        AND (vm.device_id = f.device_id OR vm.device_id IS NULL)
        AND (vm.station_id = f.station_id OR vm.station_id IS NULL)
      ORDER BY (vm.device_id IS NOT NULL) DESC, (vm.station_id IS NOT NULL) DESC
      LIMIT 1
    ) meta ON TRUE
    WHERE f.ts_bucket >= v_start AND f.ts_bucket < v_end
      AND (p_station_id IS NULL OR f.station_id = p_station_id)
      AND (p_device_id  IS NULL OR f.device_id  = p_device_id)
      AND COALESCE(f.quality_status,0) = 0 AND f.value IS NOT NULL
      -- 物理边界裁剪/过滤（存在才应用）
      AND (meta.phys_min IS NULL OR f.value >= meta.phys_min)
      AND (meta.phys_max IS NULL OR f.value <= meta.phys_max)
  ), med AS (
    SELECT station_id, device_id, metric_id,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY value)::float8 AS median
    FROM base
    GROUP BY station_id, device_id, metric_id
  ), dif AS (
    SELECT b.station_id, b.device_id, b.metric_id, b.ts_bucket, b.value,
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
           percentile_cont(0.5) WITHIN GROUP (ORDER BY ABS(b.value - m.median))::float8 AS mad,
           max(COALESCE(b.resolution,0.0)) AS max_resolution
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
         p_lookback_days, 'robust_pcnt+meta+mv',
         a.p05, a.p95, a.median, a.mad,
         g.spike_abs, g.roc_abs, g.roc_ratio,
         -- 平台期阈值加入分辨率保护下限
         GREATEST(0.0, GREATEST(a.mad*0.5, a.max_resolution)) AS flatline_eps,
         GREATEST(0.0, GREATEST(a.mad*1.0, a.max_resolution*2)) AS flatline_delta,
         now(), 'v069'
  FROM agg a
  LEFT JOIN dv_aggs g ON g.station_id=a.station_id AND g.device_id=a.device_id AND g.metric_id=a.metric_id;
END;
$$;

COMMENT ON PROCEDURE public.sp_refresh_metric_rule_auto_baseline(int, bigint, bigint)
IS '自动基线过程：近N天有效(quality=0)且稳态(从mv_device_running_1s.phase=1判定)数据，计算分位数/MAD/差分分布，写入 metric_rule_auto_baseline。v069: 修复从mv读取phase。';

COMMIT;

