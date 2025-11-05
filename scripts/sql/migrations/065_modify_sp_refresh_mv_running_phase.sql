\encoding UTF8
SET client_encoding = 'UTF8';

-- =====================================================================
-- 存储过程：sp_refresh_mv_running_phase（修订版）
-- 用途：按设备+时间窗刷新 mv_device_running_1s 的 running/phase
-- 修订说明：使用自适应窗口（startup_window_secs_effective, shutdown_window_secs_effective）
-- 创建日期：2025-10-31
-- =====================================================================

CREATE OR REPLACE PROCEDURE public.sp_refresh_mv_running_phase(
  p_station_id bigint,
  p_device_id  bigint,
  p_start_ts   timestamptz,
  p_end_ts     timestamptz
) LANGUAGE plpgsql AS $$
DECLARE
  v_startup_secs integer := 30;   -- 默认值（如果表中没有配置）
  v_shutdown_secs integer := 20;  -- 默认值（如果表中没有配置）
BEGIN
  -- 从阈值表读取自适应窗口秒数（优先使用effective字段）
  BEGIN
    SELECT 
      COALESCE(startup_window_secs_effective, 30),
      COALESCE(shutdown_window_secs_effective, 20)
    INTO v_startup_secs, v_shutdown_secs
    FROM public.device_running_thresholds
    WHERE device_id = p_device_id
    LIMIT 1;
    
    RAISE NOTICE '[sp_refresh_mv_running_phase] device_id=%, startup_window=% 秒, shutdown_window=% 秒',
      p_device_id, v_startup_secs, v_shutdown_secs;
  EXCEPTION 
    WHEN undefined_column THEN
      RAISE NOTICE '[sp_refresh_mv_running_phase] 列不存在，使用默认值: startup=30秒, shutdown=20秒';
    WHEN others THEN
      RAISE NOTICE '[sp_refresh_mv_running_phase] 读取配置失败，使用默认值: startup=30秒, shutdown=20秒';
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
                
  RAISE NOTICE '[sp_refresh_mv_running_phase] 完成: device_id=%, 时间窗口: % 到 %',
    p_device_id, p_start_ts, p_end_ts;
END$$;

COMMENT ON PROCEDURE public.sp_refresh_mv_running_phase IS $DOC$
用途: 按设备+时间窗刷新 mv_device_running_1s 的 running/phase

修订说明:
- 使用自适应窗口（startup_window_secs_effective, shutdown_window_secs_effective）
- 如果表中没有配置，使用默认值（startup=30秒, shutdown=20秒）

算法:
1. 调用 fn_running_state_1s 计算逐秒运行状态
2. 识别启动边沿（从停止到运行）和停止边沿（从运行到停止）
3. 围绕边沿扩展phase标记:
   - phase=0: 停止状态
   - phase=1: 运行状态
   - phase=2: 启动中（启动边沿前 startup_window_secs_effective 秒）
   - phase=3: 停止中（停止边沿后 shutdown_window_secs_effective 秒）

参数:
- p_station_id: 泵站ID
- p_device_id: 设备ID
- p_start_ts: 开始时间
- p_end_ts: 结束时间

示例:
CALL sp_refresh_mv_running_phase(1, 5, '2025-10-31 00:00:00', '2025-10-31 01:00:00');
$DOC$;

-- =====================================================================
-- 验证脚本
-- =====================================================================

DO $$
BEGIN
    RAISE NOTICE '[验证] sp_refresh_mv_running_phase 存储过程已更新（使用自适应窗口）';
END $$;

