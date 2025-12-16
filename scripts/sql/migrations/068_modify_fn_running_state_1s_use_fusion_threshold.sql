\encoding UTF8
SET client_encoding = 'UTF8';

-- =====================================================================
-- 函数：fn_running_state_1s（修订版2）
-- 用途：从 device_running_thresholds 读取 fusion_threshold，替代硬编码
-- 修订说明：从表中读取 fusion_threshold 字段，支持每个设备独立配置
-- 修订日期：2025-11-01
-- 依赖：067_add_fusion_threshold_field.sql
-- =====================================================================

CREATE OR REPLACE FUNCTION public.fn_running_state_1s(
  p_station_id  bigint,
  p_device_id   bigint,
  p_start_ts    timestamptz,
  p_end_ts      timestamptz
)
RETURNS TABLE (
  ts_bucket  timestamptz,
  is_running boolean,
  max_i      double precision,
  p          double precision,
  f          double precision,
  source     text
)
LANGUAGE plpgsql
STABLE
AS $fn$
DECLARE
  v_ei boolean; v_ep boolean; v_ef boolean;
  v_i_on double precision; v_i_off double precision;
  v_p_on double precision; v_p_off double precision;
  v_f_on double precision; v_f_off double precision;
  v_grace integer;
  v_state boolean := NULL;
  v_hold integer := 0;
  r_ts timestamptz; r_max_i double precision; r_p double precision; r_f double precision; r_has_any boolean;
  
  -- 新增：加权融合相关变量
  v_use_weighted_fusion boolean;
  v_weight_current double precision;
  v_weight_power double precision;
  v_weight_frequency double precision;
  v_fusion_score double precision;
  v_fusion_threshold double precision;  -- 从表中读取（不再硬编码）
BEGIN
  -- 读取阈值配置（包含新增的 fusion_threshold 字段）
  SELECT COALESCE(enable_i,false), COALESCE(enable_p,false), COALESCE(enable_f,false),
         i_on, i_off, p_on, p_off, f_on, f_off,
         grace_hold_secs,
         COALESCE(use_weighted_fusion, false),
         COALESCE(signal_weight_current, 0.5),
         COALESCE(signal_weight_power, 0.3),
         COALESCE(signal_weight_frequency, 0.2),
         COALESCE(fusion_threshold, 0.6)  -- 新增：从表中读取融合阈值
    INTO v_ei, v_ep, v_ef,
         v_i_on, v_i_off, v_p_on, v_p_off, v_f_on, v_f_off,
         v_grace,
         v_use_weighted_fusion,
         v_weight_current,
         v_weight_power,
         v_weight_frequency,
         v_fusion_threshold  -- 新增：接收融合阈值
  FROM public.device_running_thresholds
  WHERE device_id = p_device_id;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'fn_running_state_1s: 未找到 device_id=% 的阈值配置', p_device_id;
  END IF;

  FOR r_ts, r_max_i, r_p, r_f, r_has_any IN
    WITH series AS (
      SELECT generate_series(p_start_ts, p_end_ts - INTERVAL '1 second', INTERVAL '1 second') AS ts
    ),
    -- 读取原始测量数据（使用 metric_id + value 字段透视）
    cur0 AS (
      SELECT
        f.ts_bucket,
        MAX(CASE WHEN f.metric_id = 3 THEN f.value END) AS ia,  -- pump_current_a
        MAX(CASE WHEN f.metric_id = 5 THEN f.value END) AS ib,  -- pump_current_b
        MAX(CASE WHEN f.metric_id = 7 THEN f.value END) AS ic,  -- pump_current_c
        MAX(CASE WHEN f.metric_id = 8 THEN f.value END) AS p,   -- pump_active_power
        MAX(CASE WHEN f.metric_id = 1 THEN f.value END) AS f    -- pump_frequency
      FROM fact_measurements f
      WHERE f.station_id = p_station_id
        AND f.device_id = p_device_id
        AND f.ts_bucket >= p_start_ts
        AND f.ts_bucket < p_end_ts
        AND f.metric_id IN (1, 3, 5, 7, 8)  -- 只查询需要的指标
        AND f.quality_status = 0  -- 只使用质量正常的数据
      GROUP BY f.ts_bucket
    ),
    cur AS (
      SELECT s.ts AS ts_bucket,
             GREATEST(COALESCE(c0.ia,0), COALESCE(c0.ib,0), COALESCE(c0.ic,0)) AS max_i,
             COALESCE(c0.p,0) AS p,
             COALESCE(c0.f,0) AS f,
             (c0.ts_bucket IS NOT NULL) AS has_any
      FROM series s
      LEFT JOIN cur0 c0 ON c0.ts_bucket = s.ts
      ORDER BY s.ts
    )
    SELECT c.ts_bucket, c.max_i, c.p, c.f, c.has_any FROM cur c
  LOOP
    -- 初始状态判定
    IF v_state IS NULL THEN
      IF v_use_weighted_fusion THEN
        -- 使用加权融合逻辑（新算法）
        v_fusion_score := 0.0;
        IF v_ei AND v_i_on IS NOT NULL AND v_i_on > 0 THEN
          v_fusion_score := v_fusion_score + v_weight_current * (r_max_i / v_i_on);
        END IF;
        IF v_ep AND v_p_on IS NOT NULL AND v_p_on > 0 THEN
          v_fusion_score := v_fusion_score + v_weight_power * (r_p / v_p_on);
        END IF;
        IF v_ef AND v_f_on IS NOT NULL AND v_f_on > 0 THEN
          v_fusion_score := v_fusion_score + v_weight_frequency * (r_f / v_f_on);
        END IF;
        v_state := (v_fusion_score >= v_fusion_threshold);  -- 使用从表中读取的阈值
      ELSE
        -- 使用OR逻辑（原算法）
        v_state := ( (v_ei AND r_max_i >= v_i_on)
                  OR (v_ep AND r_p     >= v_p_on)
                  OR (v_ef AND r_f     >= v_f_on) );
      END IF;
    ELSE
      -- 状态转换判定（带滞回）
      IF v_use_weighted_fusion THEN
        -- 使用加权融合逻辑（新算法）
        v_fusion_score := 0.0;
        IF v_ei AND v_i_on IS NOT NULL AND v_i_on > 0 THEN
          v_fusion_score := v_fusion_score + v_weight_current * (r_max_i / v_i_on);
        END IF;
        IF v_ep AND v_p_on IS NOT NULL AND v_p_on > 0 THEN
          v_fusion_score := v_fusion_score + v_weight_power * (r_p / v_p_on);
        END IF;
        IF v_ef AND v_f_on IS NOT NULL AND v_f_on > 0 THEN
          v_fusion_score := v_fusion_score + v_weight_frequency * (r_f / v_f_on);
        END IF;
        
        -- 计算对应的 off 阈值（假设 off = 0.9 * on）
        DECLARE
          v_fusion_threshold_off double precision := v_fusion_threshold * 0.9;
        BEGIN
          IF v_state THEN
            -- 当前运行，检查是否应该停止
            IF v_fusion_score < v_fusion_threshold_off THEN
              IF v_hold >= v_grace THEN
                v_state := FALSE;
                v_hold := 0;
              ELSE
                v_hold := v_hold + 1;
              END IF;
            ELSE
              v_hold := 0;
            END IF;
          ELSE
            -- 当前停止，检查是否应该启动
            IF v_fusion_score >= v_fusion_threshold THEN
              IF v_hold >= v_grace THEN
                v_state := TRUE;
                v_hold := 0;
              ELSE
                v_hold := v_hold + 1;
              END IF;
            ELSE
              v_hold := 0;
            END IF;
          END IF;
        END;
      ELSE
        -- 使用OR逻辑（原算法）
        IF v_state THEN
          -- 当前运行，检查是否应该停止
          IF NOT ( (v_ei AND r_max_i >= v_i_off)
                OR (v_ep AND r_p     >= v_p_off)
                OR (v_ef AND r_f     >= v_f_off) ) THEN
            IF v_hold >= v_grace THEN
              v_state := FALSE;
              v_hold := 0;
            ELSE
              v_hold := v_hold + 1;
            END IF;
          ELSE
            v_hold := 0;
          END IF;
        ELSE
          -- 当前停止，检查是否应该启动
          IF ( (v_ei AND r_max_i >= v_i_on)
            OR (v_ep AND r_p     >= v_p_on)
            OR (v_ef AND r_f     >= v_f_on) ) THEN
            IF v_hold >= v_grace THEN
              v_state := TRUE;
              v_hold := 0;
            ELSE
              v_hold := v_hold + 1;
            END IF;
          ELSE
            v_hold := 0;
          END IF;
        END IF;
      END IF;
    END IF;

    -- 输出当前秒的状态
    ts_bucket  := r_ts;
    is_running := COALESCE(v_state, FALSE);
    max_i      := r_max_i;
    p          := r_p;
    f          := r_f;
    source     := CASE WHEN r_has_any THEN 'data' ELSE 'fill' END;
    RETURN NEXT;
  END LOOP;
END$fn$;

COMMENT ON FUNCTION public.fn_running_state_1s IS $DOC$
用途: 从 device_running_thresholds 读取阈值，按秒输出 is_running
修订: 
  - v1: 添加加权融合逻辑（use_weighted_fusion开关控制）
  - v2: 从表中读取 fusion_threshold 字段，支持每个设备独立配置融合阈值
输入:
  - p_station_id: 泵站ID
  - p_device_id: 设备ID
  - p_start_ts: 开始时间（包含）
  - p_end_ts: 结束时间（不包含）
输出:
  - ts_bucket: 时间戳（秒级）
  - is_running: 是否运行（TRUE/FALSE）
  - max_i: 三相电流最大值（A）
  - p: 有功功率（kW）
  - f: 频率（Hz）
  - source: 数据来源（'data'=实际数据, 'fill'=填充数据）
$DOC$;

-- =====================================================================
-- 验证脚本
-- =====================================================================

DO $$
BEGIN
    RAISE NOTICE '[验证] fn_running_state_1s 函数已更新（使用 fusion_threshold 字段）';
END$$;

