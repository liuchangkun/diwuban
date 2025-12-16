BEGIN;

CREATE TABLE IF NOT EXISTS public.quality_eval_by_device_metric (
  window_start timestamptz NOT NULL,
  window_end   timestamptz NOT NULL,
  station_id   bigint NOT NULL DEFAULT 0,
  device_id    bigint NOT NULL DEFAULT 0,
  metric_id    bigint NOT NULL,
  quality_status int NOT NULL,
  rows_count   bigint NOT NULL,
  total_count  bigint NOT NULL,
  ratio        numeric(9,6) NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (window_start, window_end, station_id, device_id, metric_id, quality_status)
);

COMMENT ON TABLE public.quality_eval_by_device_metric IS '按窗口/设备/指标生成质量码分布统计的报表表（离线统计）';

CREATE OR REPLACE PROCEDURE public.sp_generate_quality_eval_by_device_metric(
  IN p_start timestamptz,
  IN p_end   timestamptz,
  IN p_station_id bigint DEFAULT NULL,
  IN p_device_id  bigint DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
  -- 删除既有窗口统计（避免重复）
  DELETE FROM public.quality_eval_by_device_metric
  WHERE window_start=p_start AND window_end=p_end
    AND (p_station_id IS NULL OR station_id=p_station_id)
    AND (p_device_id  IS NULL OR device_id=p_device_id);

  -- 插入新的统计
  WITH base AS (
    SELECT f.station_id, f.device_id, f.metric_id, COALESCE(f.quality_status,0) AS code
    FROM public.fact_measurements f
    WHERE f.ts_bucket>=p_start AND f.ts_bucket<p_end
      AND (p_station_id IS NULL OR f.station_id=p_station_id)
      AND (p_device_id  IS NULL OR f.device_id=p_device_id)
  ), agg AS (
    SELECT station_id, device_id, metric_id, code AS quality_status,
           COUNT(*) AS rows_count
    FROM base
    GROUP BY station_id, device_id, metric_id, code
  ), tot AS (
    SELECT station_id, device_id, metric_id, SUM(rows_count) AS total_count
    FROM agg
    GROUP BY station_id, device_id, metric_id
  )
  INSERT INTO public.quality_eval_by_device_metric(
    window_start, window_end, station_id, device_id, metric_id,
    quality_status, rows_count, total_count, ratio
  )
  SELECT p_start, p_end, a.station_id, a.device_id, a.metric_id,
         a.quality_status, a.rows_count, t.total_count,
         CASE WHEN t.total_count>0 THEN a.rows_count::numeric/t.total_count ELSE 0 END AS ratio
  FROM agg a JOIN tot t USING (station_id, device_id, metric_id);
END;
$$;

COMMENT ON PROCEDURE public.sp_generate_quality_eval_by_device_metric(timestamptz, timestamptz, bigint, bigint)
IS '生成窗口内 按设备×指标×质量码 的行数分布统计，并写入质量评价报表表';

COMMIT;

