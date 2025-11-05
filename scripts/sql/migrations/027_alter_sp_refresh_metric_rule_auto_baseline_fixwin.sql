-- 修复 sp_refresh_metric_rule_auto_baseline：将窗口函数与聚合分离，避免 PG 错误
-- 关键变更：在 CTE 中先计算差分 dv / 比率 dv_ratio，再在聚合中对 dv/dv_ratio 做分位

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

  WITH base AS (
    SELECT f.station_id, f.device_id, f.metric_id, f.ts_bucket, f.value::float8 AS value,
           meta.resolution, meta.phys_min, meta.phys_max
    FROM public.fact_measurements f
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
      AND (
        EXISTS (
          SELECT 1 FROM public.fact_measurements ph
          WHERE ph.station_id=f.station_id AND ph.device_id=f.device_id AND ph.ts_bucket=f.ts_bucket
            AND v_phase_metric_id IS NOT NULL AND ph.metric_id=v_phase_metric_id AND ph.value=1
        )
        OR (
          NOT EXISTS (
            SELECT 1 FROM public.fact_measurements ph2
            WHERE ph2.station_id=f.station_id AND ph2.device_id=f.device_id AND ph2.ts_bucket=f.ts_bucket
              AND v_phase_metric_id IS NOT NULL AND ph2.metric_id=v_phase_metric_id
          )
          AND EXISTS (
            SELECT 1 FROM public.fact_measurements fr
            WHERE fr.station_id=f.station_id AND fr.device_id=f.device_id AND fr.ts_bucket=f.ts_bucket
              AND v_running_metric_id IS NOT NULL AND fr.metric_id=v_running_metric_id AND fr.value=1
          )
        )
      )
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
         p_lookback_days, 'robust_pcnt+meta',
         a.p05, a.p95, a.median, a.mad,
         g.spike_abs, g.roc_abs, g.roc_ratio,
         -- 平台期阈值加入分辨率保护下限
         GREATEST(0.0, GREATEST(a.mad*0.5, a.max_resolution)) AS flatline_eps,
         GREATEST(0.0, GREATEST(a.mad*1.0, a.max_resolution*2)) AS flatline_delta,
         now(), 'vA1'
  FROM agg a
  LEFT JOIN dv_aggs g ON g.station_id=a.station_id AND g.device_id=a.device_id AND g.metric_id=a.metric_id;
END;
$$;

COMMIT;

