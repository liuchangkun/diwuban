-- 目的：高性能刷新 device_running_thresholds 的 pf_min/pf_max（按时间窗，可按站/设备过滤）
-- 口径：仅使用质量=0 且稳态数据；稳态=优先使用 device_phase=1；若该秒不存在相位数据，则回退到 device_running=1
-- 注意：仅更新已有行（WHERE a.device_id=t.device_id）；若有缺失行，请先确保表中存在相应设备行

BEGIN;

CREATE OR REPLACE PROCEDURE public.sp_refresh_device_running_thresholds_win(
  IN p_start_ts timestamptz,
  IN p_end_ts   timestamptz,
  IN p_station_id bigint DEFAULT NULL,
  IN p_device_id  bigint DEFAULT NULL
)
LANGUAGE sql
AS $$
WITH ids AS (
  SELECT
    (SELECT id FROM public.dim_metric_config WHERE metric_key='device_phase')     AS phase_id,
    (SELECT id FROM public.dim_metric_config WHERE metric_key='device_running')   AS run_id,
    (SELECT id FROM public.dim_metric_config WHERE metric_key IN ('pump_power_factor','power_factor') LIMIT 1) AS pf_id
), base_pf AS (
  SELECT f.station_id, f.device_id, f.ts_bucket, f.value::float8 AS pf
  FROM public.fact_measurements f
  JOIN ids ON TRUE
  WHERE f.metric_id = ids.pf_id
    AND f.ts_bucket >= p_start_ts AND f.ts_bucket < p_end_ts
    AND (p_station_id IS NULL OR f.station_id = p_station_id)
    AND (p_device_id  IS NULL OR f.device_id  = p_device_id)
    AND COALESCE(f.quality_status,0) = 0 AND f.value IS NOT NULL
    AND (
      EXISTS (
        SELECT 1 FROM public.fact_measurements ph
        WHERE ph.station_id=f.station_id AND ph.device_id=f.device_id AND ph.ts_bucket=f.ts_bucket
          AND ph.metric_id = (SELECT phase_id FROM ids) AND ph.value=1
      )
      OR (
        NOT EXISTS (
          SELECT 1 FROM public.fact_measurements ph2
          WHERE ph2.station_id=f.station_id AND ph2.device_id=f.device_id AND ph2.ts_bucket=f.ts_bucket
            AND ph2.metric_id = (SELECT phase_id FROM ids)
        )
        AND EXISTS (
          SELECT 1 FROM public.fact_measurements fr
          WHERE fr.station_id=f.station_id AND fr.device_id=f.device_id AND fr.ts_bucket=f.ts_bucket
            AND fr.metric_id = (SELECT run_id FROM ids) AND fr.value=1
        )
      )
), agg AS (
  SELECT device_id,
         percentile_cont(0.05) WITHIN GROUP (ORDER BY pf) AS pf_min,
         percentile_cont(0.95) WITHIN GROUP (ORDER BY pf) AS pf_max
  FROM base_pf
  GROUP BY device_id
)
UPDATE public.device_running_thresholds t
SET pf_min = COALESCE(t.pf_min, a.pf_min),
    pf_max = COALESCE(t.pf_max, a.pf_max)
FROM agg a
WHERE a.device_id = t.device_id
  AND (p_device_id IS NULL OR t.device_id = p_device_id);
$$;

COMMENT ON PROCEDURE public.sp_refresh_device_running_thresholds_win(timestamptz, timestamptz, bigint, bigint)
IS '按窗刷新 device_running_thresholds 的 pf_min/pf_max：质量=0 且稳态（phase=1；如该秒无相位数据则回退 running=1）。仅更新已存在的设备行。';

COMMIT;

