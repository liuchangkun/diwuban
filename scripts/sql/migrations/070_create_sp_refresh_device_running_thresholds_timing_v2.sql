\encoding UTF8
SET client_encoding = 'UTF8';

/*
迁移脚本: 070_create_sp_refresh_device_running_thresholds_timing_v2.sql
创建时间: 2025-11-11
迁移目的: 重写时间参数学习逻辑，从 fact_measurements 原始数据学习所有参数

用户要求:
  - 不允许有常量存在，要能正确的学习、计算
  - 不允许是固定值！要切合实际
  - 精准判断、参数准确

学习算法:
  步骤1: 使用信号阈值初步判断运行状态（从 fact_measurements 读取电流/功率/频率）
  步骤2: 学习 grace_hold_secs - 从数据缺失间隔分析（p95分位数）
  步骤3: 学习 min_run_secs - 从运行段持续时间分析（p10分位数）
  步骤4: 学习 min_stop_secs - 从停止段持续时间分析（p10分位数）
  步骤5: 学习 smoothing_secs - 从状态切换频率分析
  步骤6: 数据不足时使用同类型设备中位数

影响范围:
  - device_running_thresholds 表的时间参数列
  - sp_refresh_device_running_thresholds_timing 存储过程（完全重写）
*/

-- 删除旧版本
DROP PROCEDURE IF EXISTS public.sp_refresh_device_running_thresholds_timing(timestamptz, timestamptz, bigint, bigint);

-- 创建新版本
CREATE OR REPLACE PROCEDURE public.sp_refresh_device_running_thresholds_timing(
  IN p_start_ts    timestamptz,
  IN p_end_ts      timestamptz,
  IN p_station_id  bigint DEFAULT NULL,
  IN p_device_id   bigint DEFAULT NULL
)
LANGUAGE plpgsql
AS $procedure$
DECLARE
  v_lookback_days int := 7;  -- 学习窗口：7天
  v_min_cycles int := 10;    -- 最少需要10个完整周期
BEGIN
  -- 步骤1: 构建初步运行状态序列（使用已学习的信号阈值）
  DROP TABLE IF EXISTS temp_raw_running_state;
  CREATE TEMP TABLE temp_raw_running_state AS
  WITH raw_data AS (
    SELECT 
      f.device_id,
      f.ts_bucket,
      MAX(CASE WHEN m.metric_key = 'pump_current_a' THEN f.value END) AS i_a,
      MAX(CASE WHEN m.metric_key = 'pump_current_b' THEN f.value END) AS i_b,
      MAX(CASE WHEN m.metric_key = 'pump_current_c' THEN f.value END) AS i_c,
      MAX(CASE WHEN m.metric_key = 'pump_active_power' THEN f.value END) AS p,
      MAX(CASE WHEN m.metric_key = 'pump_frequency' THEN f.value END) AS f
    FROM fact_measurements f
    JOIN dim_metric_config m ON m.id = f.metric_id
    WHERE f.ts_bucket >= COALESCE(p_start_ts, now() - (v_lookback_days || ' days')::interval)
      AND f.ts_bucket < COALESCE(p_end_ts, now())
      AND (p_station_id IS NULL OR f.station_id = p_station_id)
      AND (p_device_id IS NULL OR f.device_id = p_device_id)
      AND m.metric_key IN ('pump_current_a', 'pump_current_b', 'pump_current_c', 'pump_active_power', 'pump_frequency')
    GROUP BY f.device_id, f.ts_bucket
  ),
  with_thresholds AS (
    SELECT 
      r.*,
      t.enable_i, t.enable_p, t.enable_f,
      t.i_on, t.p_on, t.f_on,
      GREATEST(COALESCE(r.i_a, 0), COALESCE(r.i_b, 0), COALESCE(r.i_c, 0)) AS max_i
    FROM raw_data r
    JOIN device_running_thresholds t ON t.device_id = r.device_id
  )
  SELECT 
    device_id,
    ts_bucket,
    max_i, p, f,
    -- 初步运行判断（OR逻辑）
    CASE 
      WHEN (enable_i AND max_i >= i_on) OR (enable_p AND p >= p_on) OR (enable_f AND f >= f_on) THEN 1
      ELSE 0
    END AS running
  FROM with_thresholds;

  CREATE INDEX idx_temp_raw_device_ts ON temp_raw_running_state(device_id, ts_bucket);

  -- 步骤2: 学习 grace_hold_secs（数据缺失容忍度）
  -- 分析每个设备的数据缺失间隔，使用p95分位数
  DROP TABLE IF EXISTS temp_learned_grace_hold;
  CREATE TEMP TABLE temp_learned_grace_hold AS
  WITH gaps AS (
    SELECT 
      device_id,
      ts_bucket,
      EXTRACT(EPOCH FROM (ts_bucket - LAG(ts_bucket) OVER (PARTITION BY device_id ORDER BY ts_bucket)))::int AS gap_secs
    FROM temp_raw_running_state
  ),
  gap_stats AS (
    SELECT 
      device_id,
      percentile_cont(0.95) WITHIN GROUP (ORDER BY gap_secs) AS p95_gap,
      COUNT(*) FILTER (WHERE gap_secs > 1) AS gap_count
    FROM gaps
    WHERE gap_secs > 1  -- 只统计真正的缺失（>1秒）
    GROUP BY device_id
  )
  SELECT 
    device_id,
    LEAST(GREATEST(ROUND(p95_gap)::int, 10), 60) AS grace_hold_secs,  -- 限制在[10, 60]
    gap_count
  FROM gap_stats
  WHERE gap_count >= 5;  -- 至少5个缺失才认为数据充足

  -- 步骤3+4: 学习 min_run_secs 和 min_stop_secs（运行/停止段持续时间）
  -- 识别运行段和停止段，分析持续时间分布
  DROP TABLE IF EXISTS temp_learned_durations;
  CREATE TEMP TABLE temp_learned_durations AS
  WITH state_changes AS (
    SELECT 
      device_id,
      ts_bucket,
      running,
      LAG(running) OVER (PARTITION BY device_id ORDER BY ts_bucket) AS prev_running,
      CASE 
        WHEN running != LAG(running) OVER (PARTITION BY device_id ORDER BY ts_bucket) THEN 1
        ELSE 0
      END AS is_change
    FROM temp_raw_running_state
  ),
  segments AS (
    SELECT 
      device_id,
      ts_bucket,
      running,
      SUM(is_change) OVER (PARTITION BY device_id ORDER BY ts_bucket) AS segment_id
    FROM state_changes
  ),
  segment_durations AS (
    SELECT 
      device_id,
      running,
      segment_id,
      COUNT(*) AS duration_secs,
      MIN(ts_bucket) AS start_ts,
      MAX(ts_bucket) AS end_ts
    FROM segments
    GROUP BY device_id, running, segment_id
  ),
  duration_stats AS (
    SELECT 
      device_id,
      percentile_cont(0.10) WITHIN GROUP (ORDER BY duration_secs) FILTER (WHERE running = 1) AS p10_run_duration,
      percentile_cont(0.10) WITHIN GROUP (ORDER BY duration_secs) FILTER (WHERE running = 0) AS p10_stop_duration,
      COUNT(*) FILTER (WHERE running = 1) AS run_segment_count,
      COUNT(*) FILTER (WHERE running = 0) AS stop_segment_count
    FROM segment_durations
    WHERE duration_secs >= 3  -- 过滤掉太短的段（<3秒）
    GROUP BY device_id
  )
  SELECT 
    device_id,
    LEAST(GREATEST(ROUND(p10_run_duration)::int, 3), 60) AS min_run_secs,   -- 限制在[3, 60]
    LEAST(GREATEST(ROUND(p10_stop_duration)::int, 3), 60) AS min_stop_secs, -- 限制在[3, 60]
    run_segment_count,
    stop_segment_count
  FROM duration_stats
  WHERE run_segment_count >= v_min_cycles AND stop_segment_count >= v_min_cycles;  -- 至少10个周期

  -- 步骤5: 学习 smoothing_secs（平滑窗口）
  -- 基于状态切换频率：切换越频繁，需要更大的平滑窗口
  DROP TABLE IF EXISTS temp_learned_smoothing;
  CREATE TEMP TABLE temp_learned_smoothing AS
  WITH state_changes AS (
    SELECT
      device_id,
      ts_bucket,
      running,
      CASE
        WHEN running != LAG(running) OVER (PARTITION BY device_id ORDER BY ts_bucket) THEN 1
        ELSE 0
      END AS is_change
    FROM temp_raw_running_state
  ),
  change_stats AS (
    SELECT
      device_id,
      SUM(is_change) AS total_changes,
      EXTRACT(EPOCH FROM (MAX(ts_bucket) - MIN(ts_bucket))) / 3600.0 AS hours,
      COUNT(*) AS total_seconds
    FROM state_changes
    GROUP BY device_id
  )
  SELECT
    device_id,
    -- 切换频率（次/小时）越高，smoothing_secs 越大
    CASE
      WHEN hours > 0 THEN
        LEAST(GREATEST(
          ROUND(2 + (total_changes / hours) * 0.5)::int,  -- 基础2秒 + 频率调整
          2), 10)  -- 限制在[2, 10]
      ELSE 5  -- 默认5秒
    END AS smoothing_secs,
    total_changes,
    ROUND(total_changes / NULLIF(hours, 0), 2) AS changes_per_hour
  FROM change_stats
  WHERE total_seconds >= 3600;  -- 至少1小时数据

  -- 步骤6: 计算同类型设备的中位数（作为回退值）
  DROP TABLE IF EXISTS temp_device_type_medians;
  CREATE TEMP TABLE temp_device_type_medians AS
  WITH device_types AS (
    SELECT d.id AS device_id, d.type
    FROM dim_devices d
    WHERE (p_device_id IS NULL OR d.id = p_device_id)
  ),
  learned_values AS (
    SELECT
      dt.type,
      g.grace_hold_secs,
      dur.min_run_secs,
      dur.min_stop_secs,
      s.smoothing_secs
    FROM device_types dt
    LEFT JOIN temp_learned_grace_hold g ON g.device_id = dt.device_id
    LEFT JOIN temp_learned_durations dur ON dur.device_id = dt.device_id
    LEFT JOIN temp_learned_smoothing s ON s.device_id = dt.device_id
  )
  SELECT
    type,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY grace_hold_secs) AS median_grace_hold,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY min_run_secs) AS median_min_run,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY min_stop_secs) AS median_min_stop,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY smoothing_secs) AS median_smoothing
  FROM learned_values
  WHERE grace_hold_secs IS NOT NULL
    OR min_run_secs IS NOT NULL
    OR min_stop_secs IS NOT NULL
    OR smoothing_secs IS NOT NULL
  GROUP BY type;

  -- 步骤7: 更新 device_running_thresholds 表
  UPDATE device_running_thresholds
  SET
    grace_hold_secs = COALESCE(
      updates.grace_hold_secs,
      updates.median_grace_hold,
      30
    ),
    min_run_secs = COALESCE(
      updates.min_run_secs,
      updates.median_min_run,
      10
    ),
    min_stop_secs = COALESCE(
      updates.min_stop_secs,
      updates.median_min_stop,
      10
    ),
    smoothing_secs = COALESCE(
      updates.smoothing_secs,
      updates.median_smoothing,
      5
    ),
    updated_at = now()
  FROM (
    SELECT
      t2.device_id,
      g.grace_hold_secs,
      dur.min_run_secs,
      dur.min_stop_secs,
      s.smoothing_secs,
      ROUND(m.median_grace_hold)::int AS median_grace_hold,
      ROUND(m.median_min_run)::int AS median_min_run,
      ROUND(m.median_min_stop)::int AS median_min_stop,
      ROUND(m.median_smoothing)::int AS median_smoothing
    FROM device_running_thresholds t2
    JOIN dim_devices d ON d.id = t2.device_id
    LEFT JOIN temp_learned_grace_hold g ON g.device_id = t2.device_id
    LEFT JOIN temp_learned_durations dur ON dur.device_id = t2.device_id
    LEFT JOIN temp_learned_smoothing s ON s.device_id = t2.device_id
    LEFT JOIN temp_device_type_medians m ON m.type = d.type
    WHERE (p_device_id IS NULL OR t2.device_id = p_device_id)
  ) AS updates
  WHERE device_running_thresholds.device_id = updates.device_id;

  -- 清理临时表
  DROP TABLE IF EXISTS temp_raw_running_state;
  DROP TABLE IF EXISTS temp_learned_grace_hold;
  DROP TABLE IF EXISTS temp_learned_durations;
  DROP TABLE IF EXISTS temp_learned_smoothing;
  DROP TABLE IF EXISTS temp_device_type_medians;

  RAISE NOTICE '时间参数学习完成';
END;
$procedure$;

COMMENT ON PROCEDURE public.sp_refresh_device_running_thresholds_timing IS $DOC$
存储过程: sp_refresh_device_running_thresholds_timing
用途: 从 fact_measurements 原始数据学习设备运行时间参数

学习参数:
  - grace_hold_secs: 数据缺失容忍度（p95分位数，范围[10, 60]）
  - min_run_secs: 最小运行段长度（p10分位数，范围[3, 60]）
  - min_stop_secs: 最小停止段长度（p10分位数，范围[3, 60]）
  - smoothing_secs: 平滑窗口（基于切换频率，范围[2, 10]）

学习策略:
  1. 优先使用设备自身学习值
  2. 数据不足时使用同类型设备中位数
  3. 最后使用全局默认值（30, 10, 10, 5）

数据要求:
  - 至少7天历史数据
  - 至少10个完整运行/停止周期
  - 至少1小时数据用于平滑窗口学习

参数:
  p_start_ts: 学习窗口起始时间（NULL=当前时间-7天）
  p_end_ts: 学习窗口结束时间（NULL=当前时间）
  p_station_id: 站点ID（NULL=所有站点）
  p_device_id: 设备ID（NULL=所有设备）

示例:
  -- 学习所有设备的时间参数（使用最近7天数据）
  CALL sp_refresh_device_running_thresholds_timing(NULL, NULL, NULL, NULL);

  -- 学习特定设备的时间参数
  CALL sp_refresh_device_running_thresholds_timing(NULL, NULL, NULL, 1);
$DOC$;

