\encoding UTF8
SET client_encoding = 'UTF8';

-- =====================================================================
-- 函数：fn_running_state_1s（修订版）
-- 用途：从 device_running_thresholds 读取阈值，按秒输出 is_running
-- 修订说明：添加加权融合逻辑（通过use_weighted_fusion开关控制）
-- 创建日期：2025-10-31
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
  v_fusion_threshold double precision := 0.6;  -- 融合阈值（60%）
BEGIN
  -- 读取阈值配置（包含新增的加权融合参数）
  SELECT COALESCE(enable_i,false), COALESCE(enable_p,false), COALESCE(enable_f,false),
         i_on, i_off, p_on, p_off, f_on, f_off,
         grace_hold_secs,
         COALESCE(use_weighted_fusion, false),
         COALESCE(signal_weight_current, 0.5),
         COALESCE(signal_weight_power, 0.3),
         COALESCE(signal_weight_frequency, 0.2)
    INTO v_ei, v_ep, v_ef,
         v_i_on, v_i_off, v_p_on, v_p_off, v_f_on, v_f_off,
         v_grace,
         v_use_weighted_fusion,
         v_weight_current,
         v_weight_power,
         v_weight_frequency
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
        v_state := (v_fusion_score >= v_fusion_threshold);
      ELSE
        -- 使用OR逻辑（原算法）
        v_state := ( (v_ei AND r_max_i >= v_i_on)
                  OR (v_ep AND r_p     >= v_p_on)
                  OR (v_ef AND r_f     >= v_f_on) );
      END IF;
      
      v_hold := 0;
      ts_bucket := r_ts; is_running := v_state; max_i := r_max_i; p := r_p; f := r_f;
      source := CASE WHEN NOT r_has_any AND v_grace > 0 THEN 'hold' ELSE 'det' END;
      RETURN NEXT;
      CONTINUE;
    END IF;

    -- 有数据时更新状态
    IF r_has_any THEN
      v_hold := 0;
      
      IF v_use_weighted_fusion THEN
        -- 使用加权融合逻辑（新算法）
        IF v_state THEN
          -- 当前运行，检查是否应该停止（使用off阈值）
          v_fusion_score := 0.0;
          IF v_ei AND v_i_off IS NOT NULL AND v_i_off > 0 THEN
            v_fusion_score := v_fusion_score + v_weight_current * (r_max_i / v_i_off);
          END IF;
          IF v_ep AND v_p_off IS NOT NULL AND v_p_off > 0 THEN
            v_fusion_score := v_fusion_score + v_weight_power * (r_p / v_p_off);
          END IF;
          IF v_ef AND v_f_off IS NOT NULL AND v_f_off > 0 THEN
            v_fusion_score := v_fusion_score + v_weight_frequency * (r_f / v_f_off);
          END IF;
          -- 融合分数低于阈值时停止
          IF v_fusion_score < v_fusion_threshold THEN
            v_state := false;
          END IF;
        ELSE
          -- 当前停止，检查是否应该启动（使用on阈值）
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
          -- 融合分数达到阈值时启动
          IF v_fusion_score >= v_fusion_threshold THEN
            v_state := true;
          END IF;
        END IF;
      ELSE
        -- 使用OR逻辑（原算法）
        IF v_state THEN
          -- 当前运行，检查是否应该停止（所有信号都低于off阈值）
          IF ( (NOT v_ei OR r_max_i <= v_i_off)
               AND (NOT v_ep OR r_p <= v_p_off)
               AND (NOT v_ef OR r_f <= v_f_off) ) THEN
            v_state := false;
          END IF;
        ELSE
          -- 当前停止，检查是否应该启动（任一信号高于on阈值）
          IF ( (v_ei AND r_max_i >= v_i_on)
               OR (v_ep AND r_p >= v_p_on)
               OR (v_ef AND r_f >= v_f_on) ) THEN
            v_state := true;
          END IF;
        END IF;
      END IF;
      
      ts_bucket := r_ts; is_running := v_state; max_i := r_max_i; p := r_p; f := r_f; source := 'det';
      RETURN NEXT;
    ELSE
      -- 无数据时使用grace_hold延续
      IF v_grace > 0 THEN
        IF v_hold < v_grace THEN v_hold := v_hold + 1; END IF;
        ts_bucket := r_ts; is_running := v_state; max_i := r_max_i; p := r_p; f := r_f; source := 'hold';
        RETURN NEXT;
      ELSE
        ts_bucket := r_ts; is_running := v_state; max_i := r_max_i; p := r_p; f := r_f; source := 'det';
        RETURN NEXT;
      END IF;
    END IF;
  END LOOP;
END;
$fn$;

COMMENT ON FUNCTION public.fn_running_state_1s IS $DOC$
用途: 从 device_running_thresholds 读取阈值，按秒输出 is_running（on/off 滞回 + 缺报延续）

修订说明:
- 添加加权融合逻辑（通过use_weighted_fusion开关控制）
- 保留原有OR逻辑作为默认行为（向后兼容）

算法:
1. 原算法（use_weighted_fusion=FALSE）:
   - 启动: 任一信号 >= on阈值
   - 停止: 所有信号 <= off阈值
   
2. 新算法（use_weighted_fusion=TRUE）:
   - 计算融合分数 = Σ(权重 * 信号值/阈值)
   - 启动: 融合分数 >= 0.6
   - 停止: 融合分数 < 0.6
   - 权重来自device_running_thresholds表:
     * signal_weight_current（电流权重）
     * signal_weight_power（功率权重）
     * signal_weight_frequency（频率权重）

参数:
- p_station_id: 泵站ID
- p_device_id: 设备ID
- p_start_ts: 开始时间
- p_end_ts: 结束时间

返回:
- ts_bucket: 时间戳（秒级）
- is_running: 是否运行
- max_i: 最大电流
- p: 功率
- f: 频率
- source: 数据来源（'det'=检测, 'hold'=延续）

示例:
SELECT * FROM fn_running_state_1s(1, 5, '2025-10-31 00:00:00', '2025-10-31 01:00:00');
$DOC$;

-- =====================================================================
-- 验证脚本
-- =====================================================================

DO $$
BEGIN
    RAISE NOTICE '[验证] fn_running_state_1s 函数已更新（添加加权融合逻辑）';
END $$;

