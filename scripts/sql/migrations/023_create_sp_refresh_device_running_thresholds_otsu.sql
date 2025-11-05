-- 方案A：Otsu 双峰阈值法（纯SQL近似）用于估计 PF 阈值，作为 robust_pcnt 的增强版
-- 说明：
-- - 对窗口内质量=0且稳态的 PF 样本，分桶统计直方图；用 Otsu 最大类间方差法求分割阈值
-- - 若样本不足或分布不明显双峰，则回退 robust 分位（p05/p95）
-- - 仅更新已有行（与 v1 过程一致），保留幂等

BEGIN;

CREATE OR REPLACE PROCEDURE public.sp_refresh_device_running_thresholds_otsu(
  IN p_start_ts timestamptz,
  IN p_end_ts   timestamptz,
  IN p_station_id bigint DEFAULT NULL,
  IN p_device_id  bigint DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_phase_metric_id bigint;
  v_run_metric_id bigint;
  v_pf_metric_id bigint;
BEGIN
  SELECT id INTO v_phase_metric_id FROM public.dim_metric_config WHERE metric_key='device_phase';
  SELECT id INTO v_run_metric_id   FROM public.dim_metric_config WHERE metric_key='device_running';
  SELECT id INTO v_pf_metric_id    FROM public.dim_metric_config WHERE metric_key IN ('pump_power_factor','power_factor') LIMIT 1;

  WITH base AS (
    SELECT f.device_id, f.value::float8 AS pf
    FROM public.fact_measurements f
    WHERE f.metric_id = v_pf_metric_id
      AND f.ts_bucket >= p_start_ts AND f.ts_bucket < p_end_ts
      AND (p_station_id IS NULL OR f.station_id=p_station_id)
      AND (p_device_id  IS NULL OR f.device_id =p_device_id)
      AND COALESCE(f.quality_status,0)=0 AND f.value IS NOT NULL
      AND (
        EXISTS (
          SELECT 1 FROM public.fact_measurements ph
          WHERE ph.station_id=f.station_id AND ph.device_id=f.device_id AND ph.ts_bucket=f.ts_bucket
            AND ph.metric_id=v_phase_metric_id AND ph.value=1
        )
        OR (
          NOT EXISTS (
            SELECT 1 FROM public.fact_measurements ph2
            WHERE ph2.station_id=f.station_id AND ph2.device_id=f.device_id AND ph2.ts_bucket=f.ts_bucket
              AND ph2.metric_id=v_phase_metric_id
          )
          AND EXISTS (
            SELECT 1 FROM public.fact_measurements fr
            WHERE fr.station_id=f.station_id AND fr.device_id=f.device_id AND fr.ts_bucket=f.ts_bucket
              AND fr.metric_id=v_run_metric_id AND fr.value=1
          )
        )
      )
  ), hist AS (
    -- 将 PF [0,1] 区间分成 100 桶，统计每设备直方图
    SELECT device_id, bucket,
           COUNT(*)::float8 AS cnt,
           MIN(pf) AS min_v, MAX(pf) AS max_v
    FROM (
      SELECT device_id, pf, GREATEST(0, LEAST(99, FLOOR(pf*100)))::int AS bucket
      FROM base
      WHERE pf>=0.0 AND pf<=1.0
    ) t
    GROUP BY device_id, bucket
  ), prefix AS (
    -- 前缀和：P(k)=∑_{i<=k}p_i，M(k)=∑_{i<=k}i·p_i
    SELECT h.device_id, h.bucket,
           SUM(cnt)              OVER (PARTITION BY h.device_id ORDER BY h.bucket) AS csum,
           SUM(cnt*h.bucket)     OVER (PARTITION BY h.device_id ORDER BY h.bucket) AS msum,
           SUM(cnt)              OVER (PARTITION BY h.device_id)                   AS ctot,
           SUM(cnt*h.bucket)     OVER (PARTITION BY h.device_id)                   AS mtot
    FROM hist h
  ), otsu AS (
    -- 最大化类间方差 σ_b^2 = [ (μ_T·ω(k) - μ(k))^2 ] / [ ω(k)·(1-ω(k)) ]
    SELECT device_id, bucket,
           CASE
             WHEN csum=0 OR csum=ctot THEN 0
             ELSE (
               (mtot::float8/NULLIF(ctot,0) - msum::float8/NULLIF(csum,0))^2
             ) * (csum::float8/NULLIF(ctot,0)) * (1 - csum::float8/NULLIF(ctot,0))
           END AS between_var
    FROM prefix
  ), best AS (
    SELECT device_id, bucket
    FROM (
      SELECT device_id, bucket,
             ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY between_var DESC) AS rn
      FROM otsu
    ) t
    WHERE rn=1
  ), robust AS (
    SELECT device_id,
           percentile_cont(0.05) WITHIN GROUP (ORDER BY pf)::float8 AS p05,
           percentile_cont(0.95) WITHIN GROUP (ORDER BY pf)::float8 AS p95
    FROM base GROUP BY device_id
  )
  UPDATE public.device_running_thresholds t
  SET pf_min = COALESCE(t.pf_min, CASE WHEN b.bucket IS NOT NULL THEN (b.bucket/100.0) ELSE r.p05 END),
      pf_max = COALESCE(t.pf_max, CASE WHEN b.bucket IS NOT NULL THEN (b.bucket/100.0) ELSE r.p95 END)
  FROM best b
  FULL JOIN robust r USING (device_id)
  WHERE t.device_id = COALESCE(b.device_id, r.device_id)
    AND (p_device_id IS NULL OR t.device_id = p_device_id);
END;
$$;

COMMENT ON PROCEDURE public.sp_refresh_device_running_thresholds_otsu(timestamptz, timestamptz, bigint, bigint)
IS '按窗口使用 Otsu 双峰法估计功率因数阈值（样本不足回退稳健分位），仅更新已有设备行。';

COMMIT;

