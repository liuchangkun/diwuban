-- 040_mv_running_phase.sql
-- 目的：
--   1) 扩展 mv_device_running_1s，合并“运行/相位”到 1s 基准表（新增 phase/phase_type）
--   2) 提供过程 sp_refresh_mv_running_phase（基于阈值与启停窗口，按窗口刷新 running/phase）
--   3) 放宽 completion_steps.metric_id 约束（允许 NULL，去除 FK），以便无“指标行”路径
--   4) 删除 fact_measurements.operation_phase、operation_phase_type 两列
-- 说明：
--   - 本脚本幂等：IF EXISTS / IF NOT EXISTS 保护；重复执行不报错
--   - 仅最小变更，后续可按需要追加索引或过程优化

BEGIN;

-- 1) 扩展 mv_device_running_1s
ALTER TABLE IF EXISTS public.mv_device_running_1s
  ADD COLUMN IF NOT EXISTS phase smallint NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS phase_type text;

COMMENT ON COLUMN public.mv_device_running_1s.phase IS '运行相位：0未知/1稳态/2启动中/3停止中';
COMMENT ON COLUMN public.mv_device_running_1s.phase_type IS '相位类型/原因文本（可选）';

-- 2) 放宽 completion_steps.metric_id 约束（允许 NULL，去除 FK）
DO $$
BEGIN
  -- 删除外键约束（若存在）
  IF EXISTS (
    SELECT 1 FROM pg_constraint c
    JOIN pg_class t ON t.oid = c.conrelid
    WHERE t.relname = 'completion_steps' AND c.conname = 'completion_steps_metric_id_fkey'
  ) THEN
    ALTER TABLE public.completion_steps DROP CONSTRAINT completion_steps_metric_id_fkey;
  END IF;
EXCEPTION WHEN undefined_table THEN
  -- 表不存在则忽略
  NULL;
END$$;

-- 允许 NULL
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='public' AND table_name='completion_steps' AND column_name='metric_id'
  ) THEN
    ALTER TABLE public.completion_steps ALTER COLUMN metric_id DROP NOT NULL;
  END IF;
END$$;

-- 3) 删除 fact.operation_phase* 两列（若存在）
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='public' AND table_name='fact_measurements' AND column_name='operation_phase'
  ) THEN
    ALTER TABLE public.fact_measurements DROP COLUMN IF EXISTS operation_phase;
  END IF;
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='public' AND table_name='fact_measurements' AND column_name='operation_phase_type'
  ) THEN
    ALTER TABLE public.fact_measurements DROP COLUMN IF EXISTS operation_phase_type;
  END IF;
END$$;

-- 4) 刷新过程：按设备+时间窗写入/更新 mv_device_running_1s.running/phase
--    实现要点：
--      - 仍以现有“秒级运行判定序列”为基础（如已有 mv_device_running_1s.running 或 fn_* 函数）；
--      - 启停窗口优先使用 v_startstop_windows（如存在），否则以阈值 pre/post 秒数在边沿处扩展得到 2/3 段；
--      - 幂等：目标窗口内 delete 后再 insert；或使用 upsert。
--    这里给出一个最小可用实现，占位支持，后续可替换为更精细的版本。

CREATE OR REPLACE FUNCTION public.fn_phase_from_running(
  r smallint,
  ts timestamptz,
  did bigint
) RETURNS smallint LANGUAGE plpgsql AS $$
DECLARE p smallint; BEGIN
  -- 简化占位：运行=1 则稳态(1)，否则未知(0)；
  -- 启停中(2/3)后续根据 v_startstop_windows 或阈值窗口优化
  IF r = 1 THEN p := 1; ELSE p := 0; END IF;
  RETURN p;
END$$;

CREATE OR REPLACE PROCEDURE public.sp_refresh_mv_running_phase(
  p_station_id bigint,
  p_device_id  bigint,
  p_start_ts   timestamptz,
  p_end_ts     timestamptz
) LANGUAGE plpgsql AS $$
DECLARE
  v_startup_secs integer := 10;
  v_shutdown_secs integer := 10;
BEGIN
  -- 从阈值表尝试加载启动/停止窗口秒数（若无该列或不存在则使用默认值）
  BEGIN
    SELECT COALESCE(startup_window_secs,10), COALESCE(shutdown_window_secs,10)
      INTO v_startup_secs, v_shutdown_secs
    FROM public.device_running_thresholds
    WHERE device_id = p_device_id
    LIMIT 1;
  EXCEPTION WHEN undefined_column THEN
    NULL; -- 列不存在，使用默认值
  WHEN others THEN
    NULL; -- 其他异常忽略，使用默认值
  END;

  -- 删除目标窗口，避免重复
  DELETE FROM public.mv_device_running_1s m
   WHERE m.station_id = p_station_id
     AND m.device_id  = p_device_id
     AND m.ts_bucket >= p_start_ts
     AND m.ts_bucket <  p_end_ts;

  -- 基于 fn_running_state_1s 计算逐秒，并围绕边沿扩展 2/3（启动中/停止中）
  WITH s AS (
    SELECT * FROM public.fn_running_state_1s(p_station_id, p_device_id, p_start_ts, p_end_ts)
  ), s2 AS (
    SELECT s.ts_bucket,
           s.is_running,
           LAG(s.is_running) OVER (ORDER BY s.ts_bucket) AS prev_running
    FROM s AS s
  ), edges AS (
    SELECT ts_bucket AS ts, 'start'::text AS kind
    FROM s2
    WHERE is_running = TRUE AND COALESCE(prev_running, FALSE) = FALSE
    UNION ALL
    SELECT ts_bucket AS ts, 'stop'::text AS kind
    FROM s2
    WHERE is_running = FALSE AND COALESCE(prev_running, FALSE) = TRUE
  ), mark AS (
    SELECT s2.ts_bucket,
           s2.is_running,
           CASE
             WHEN s2.is_running THEN 1
             WHEN EXISTS (
               SELECT 1 FROM edges e
               WHERE e.kind='start'
                 AND s2.ts_bucket >= e.ts - (v_startup_secs || ' seconds')::interval
                 AND s2.ts_bucket <  e.ts
             ) THEN 2
             WHEN EXISTS (
               SELECT 1 FROM edges e
               WHERE e.kind='stop'
                 AND s2.ts_bucket >= e.ts
                 AND s2.ts_bucket <  e.ts + (v_shutdown_secs || ' seconds')::interval
             ) THEN 3
             ELSE 0
           END AS phase
    FROM s2
  )
  INSERT INTO public.mv_device_running_1s(station_id, device_id, ts_bucket, running, phase, phase_type)
  SELECT p_station_id, p_device_id, m.ts_bucket,
         CASE WHEN m.is_running THEN 1 ELSE 0 END,
         m.phase,
         NULL::text
  FROM mark m
  ON CONFLICT (station_id, device_id, ts_bucket)
  DO UPDATE SET running = EXCLUDED.running,
                phase   = EXCLUDED.phase,
                phase_type = EXCLUDED.phase_type;
END$$;

COMMENT ON PROCEDURE public.sp_refresh_mv_running_phase IS '按设备+时间窗刷新 mv_device_running_1s 的 running/phase（最小占位实现）';

COMMIT;

