-- =====================================================================
-- ⚠️ 部分废弃警告
-- 本迁移脚本创建的 mv_presence_1s 表已于 2025-11-04 废弃并删除
-- 原因：该表已被 metrics_presence_per_second_device 表完全替代
-- 详见迁移脚本：074_drop_mv_presence_1s.sql
--
-- 仍然有效的部分：
-- - mv_device_running_1s 表（仍在使用）
-- - sp_refresh_mv_running_presence 存储过程（已修改，仅刷新 mv_device_running_1s）
-- =====================================================================

BEGIN;

-- 运行态与存在性物化表
CREATE TABLE IF NOT EXISTS public.mv_device_running_1s (
  station_id bigint NOT NULL,
  device_id  bigint NOT NULL,
  ts_bucket  timestamptz NOT NULL,
  running    smallint NOT NULL,
  PRIMARY KEY (station_id, device_id, ts_bucket)
);

CREATE TABLE IF NOT EXISTS public.mv_presence_1s (
  station_id bigint NOT NULL,
  device_id  bigint NOT NULL,
  metric_id  bigint NOT NULL,
  ts_bucket  timestamptz NOT NULL,
  present    smallint NOT NULL,
  PRIMARY KEY (station_id, device_id, metric_id, ts_bucket)
);

-- 统计片段：60s窗口原子统计（可用于 stddev/span 推导）
CREATE TABLE IF NOT EXISTS public.mv_metric_60s_stats (
  station_id bigint NOT NULL,
  device_id  bigint NOT NULL,
  metric_id  bigint NOT NULL,
  ts_bucket  timestamptz NOT NULL,
  count      integer NOT NULL,
  sum        double precision NOT NULL,
  sumsq      double precision NOT NULL,
  v_min      double precision NOT NULL,
  v_max      double precision NOT NULL,
  PRIMARY KEY (station_id, device_id, metric_id, ts_bucket)
);

-- 索引
CREATE INDEX IF NOT EXISTS ix_mv_run_sd_t ON public.mv_device_running_1s(station_id, device_id, ts_bucket);
CREATE INDEX IF NOT EXISTS ix_mv_pres_sdm_t ON public.mv_presence_1s(station_id, device_id, metric_id, ts_bucket);
CREATE INDEX IF NOT EXISTS ix_mv_stats_sdm_t ON public.mv_metric_60s_stats(station_id, device_id, metric_id, ts_bucket);

-- 刷新过程：运行态/存在性 1s
CREATE OR REPLACE PROCEDURE public.sp_refresh_mv_running_presence(
  IN p_start timestamptz,
  IN p_end   timestamptz,
  IN p_station_id bigint DEFAULT NULL,
  IN p_device_id  bigint DEFAULT NULL
)
LANGUAGE sql
AS $$
  -- 运行态（device_running==1）
  INSERT INTO public.mv_device_running_1s(station_id, device_id, ts_bucket, running)
  SELECT f.station_id, f.device_id, f.ts_bucket, 1
  FROM public.fact_measurements f
  JOIN public.dim_metric_config mc ON mc.id=f.metric_id AND mc.metric_key='device_running'
  WHERE f.ts_bucket>=p_start AND f.ts_bucket<p_end
    AND (p_station_id IS NULL OR f.station_id=p_station_id)
    AND (p_device_id  IS NULL OR f.device_id=p_device_id)
    AND f.value=1
  ON CONFLICT DO NOTHING;

  -- 存在性
  INSERT INTO public.mv_presence_1s(station_id, device_id, metric_id, ts_bucket, present)
  SELECT f.station_id, f.device_id, f.metric_id, f.ts_bucket, 1
  FROM public.fact_measurements f
  WHERE f.ts_bucket>=p_start AND f.ts_bucket<p_end
    AND (p_station_id IS NULL OR f.station_id=p_station_id)
    AND (p_device_id  IS NULL OR f.device_id=p_device_id)
  ON CONFLICT DO NOTHING;
$$;

-- 刷新过程：60s 统计
CREATE OR REPLACE PROCEDURE public.sp_refresh_mv_metric_60s_stats(
  IN p_start timestamptz,
  IN p_end   timestamptz,
  IN p_station_id bigint DEFAULT NULL,
  IN p_device_id  bigint DEFAULT NULL
)
LANGUAGE sql
AS $$
  WITH src AS (
    SELECT f.station_id, f.device_id, f.metric_id, f.ts_bucket, f.value::double precision AS v
    FROM public.fact_measurements f
    WHERE f.ts_bucket>=p_start AND f.ts_bucket<p_end
      AND (p_station_id IS NULL OR f.station_id=p_station_id)
      AND (p_device_id  IS NULL OR f.device_id=p_device_id)
  ), win AS (
    SELECT station_id, device_id, metric_id, ts_bucket,
           COUNT(v) OVER w AS count,
           SUM(v)   OVER w AS sum,
           SUM(v*v) OVER w AS sumsq,
           MIN(v)   OVER w AS v_min,
           MAX(v)   OVER w AS v_max
    FROM src
    WINDOW w AS (
      PARTITION BY station_id, device_id, metric_id
      ORDER BY ts_bucket
      RANGE BETWEEN INTERVAL '59 seconds' PRECEDING AND CURRENT ROW
    )
  )
  INSERT INTO public.mv_metric_60s_stats(station_id, device_id, metric_id, ts_bucket, count, sum, sumsq, v_min, v_max)
  SELECT station_id, device_id, metric_id, ts_bucket, count, sum, sumsq, v_min, v_max
  FROM win
  ON CONFLICT DO NOTHING;
$$;

COMMIT;

