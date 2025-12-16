-- 为自动基线过程接入“有效指标元数据”，做边界裁剪与分辨率保护（方案A）
-- 目标：
-- - 使用 v_effective_metric_metadata 获取 phys_min/phys_max/resolution
-- - 在取样阶段过滤出界值；在平台期建议中引入分辨率作为下限

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
  ), agg AS (
    SELECT b.station_id, b.device_id, b.metric_id,
           percentile_cont(0.05) WITHIN GROUP (ORDER BY b.value)::float8 AS p05,
           percentile_cont(0.95) WITHIN GROUP (ORDER BY b.value)::float8 AS p95,
           m.median,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY ABS(b.value - m.median))::float8 AS mad,
           -- 跳变/速率建议（简化：差分绝对值分位；后续可用 Hampel 细化）
           percentile_cont(0.99) WITHIN GROUP (ORDER BY ABS(b.value - lag(b.value) OVER (PARTITION BY b.station_id,b.device_id,b.metric_id ORDER BY b.ts_bucket)))::float8 AS spike_abs,
           percentile_cont(0.99) WITHIN GROUP (ORDER BY ABS(b.value - lag(b.value) OVER (PARTITION BY b.station_id,b.device_id,b.metric_id ORDER BY b.ts_bucket)))::float8 AS roc_abs,
           percentile_cont(0.99) WITHIN GROUP (ORDER BY ABS((b.value - lag(b.value) OVER (PARTITION BY b.station_id,b.device_id,b.metric_id ORDER BY b.ts_bucket)) / NULLIF(lag(b.value) OVER (PARTITION BY b.station_id,b.device_id,b.metric_id ORDER BY b.ts_bucket),0)))::float8 AS roc_ratio,
           max(COALESCE(b.resolution,0.0)) AS max_resolution
    FROM base b
    JOIN med m ON m.station_id=b.station_id AND m.device_id=b.device_id AND m.metric_id=b.metric_id
    GROUP BY b.station_id, b.device_id, b.metric_id, m.median
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
         a.spike_abs, a.roc_abs, a.roc_ratio,
         -- 平台期阈值加入分辨率保护下限
         GREATEST(0.0, GREATEST(a.mad*0.5, a.max_resolution)) AS flatline_eps,
         GREATEST(0.0, GREATEST(a.mad*1.0, a.max_resolution*2)) AS flatline_delta,
         now(), 'vA1'
  FROM agg a;
END;
$$;

COMMIT;

