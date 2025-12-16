\encoding UTF8
SET client_encoding = 'UTF8';

-- =====================================================================
-- 存储过程: sp_detect_running_mode_simple
-- 用途: 识别设备运行模式（持续运行 vs 频繁启停 vs 偶尔运行）
-- 创建日期: 2025-10-31
-- 修订说明: 添加数据可用性检查和降级处理
-- 依赖: 060_alter_device_running_thresholds_phase1.sql
-- =====================================================================

CREATE OR REPLACE PROCEDURE api.sp_detect_running_mode_simple(
    p_device_id BIGINT DEFAULT NULL  -- NULL表示处理所有设备
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_device_record RECORD;
    v_running_mode TEXT;
    v_running_time_ratio DOUBLE PRECISION;
    v_threshold_quality TEXT;
    v_data_days_available INTEGER;
    v_min_ts TIMESTAMPTZ;
    v_max_ts TIMESTAMPTZ;
    v_total_seconds BIGINT;
    v_running_seconds BIGINT;
    v_updated_count INTEGER := 0;
BEGIN
    RAISE NOTICE '[存储过程开始] sp_detect_running_mode_simple, device_id=%', COALESCE(p_device_id::TEXT, 'ALL');
    
    -- 遍历设备
    FOR v_device_record IN
        SELECT d.id, d.name
        FROM public.dim_devices d
        WHERE d.type = 'pump'
            AND (p_device_id IS NULL OR d.id = p_device_id)
        ORDER BY d.id
    LOOP
        RAISE NOTICE '[处理设备] device_id=%, name=%', v_device_record.id, v_device_record.name;
        
        -- ========== 步骤1: 计算数据可用天数 ==========
        SELECT
            MIN(ts_bucket) AS min_ts,
            MAX(ts_bucket) AS max_ts
        INTO v_min_ts, v_max_ts
        FROM public.mv_device_running_1s
        WHERE device_id = v_device_record.id
            AND ts_bucket >= NOW() - INTERVAL '7 days';
        
        IF v_min_ts IS NULL THEN
            v_data_days_available := 0;
        ELSE
            v_data_days_available := EXTRACT(EPOCH FROM (v_max_ts - v_min_ts)) / 86400.0;
        END IF;
        
        RAISE NOTICE '[数据可用性] data_days_available=% 天', v_data_days_available;
        
        -- ========== 步骤2: 检查数据是否充足 ==========
        IF v_data_days_available < 1 THEN
            RAISE WARNING '[数据不足] device_id=% 数据不足1天，无法识别运行模式', v_device_record.id;
            v_running_mode := 'unknown';
            v_running_time_ratio := NULL;
            v_threshold_quality := 'insufficient';
        ELSE
            -- ========== 步骤3: 计算运行时长比例 ==========
            SELECT
                COUNT(*) AS total_seconds,
                SUM(CASE WHEN running = 1 THEN 1 ELSE 0 END) AS running_seconds
            INTO v_total_seconds, v_running_seconds
            FROM public.mv_device_running_1s
            WHERE device_id = v_device_record.id
                AND ts_bucket >= NOW() - INTERVAL '7 days';
            
            IF v_total_seconds > 0 THEN
                v_running_time_ratio := v_running_seconds::DOUBLE PRECISION / v_total_seconds::DOUBLE PRECISION;
            ELSE
                v_running_time_ratio := 0;
            END IF;
            
            RAISE NOTICE '[运行统计] total_seconds=%, running_seconds=%, ratio=%', 
                v_total_seconds, v_running_seconds, v_running_time_ratio;
            
            -- ========== 步骤4: 判定运行模式 ==========
            IF v_running_time_ratio > 0.8 THEN
                v_running_mode := 'continuous';
                RAISE NOTICE '[运行模式] 持续运行 (continuous), ratio=% > 0.8', v_running_time_ratio;
            ELSIF v_running_time_ratio < 0.2 THEN
                v_running_mode := 'occasional';
                RAISE NOTICE '[运行模式] 偶尔运行 (occasional), ratio=% < 0.2', v_running_time_ratio;
            ELSE
                v_running_mode := 'frequent';
                RAISE NOTICE '[运行模式] 频繁启停 (frequent), 0.2 <= ratio=% <= 0.8', v_running_time_ratio;
            END IF;
            
            -- ========== 步骤5: 根据data_days_available设置threshold_quality ==========
            IF v_data_days_available >= 7 THEN
                v_threshold_quality := 'high';
            ELSIF v_data_days_available >= 3 THEN
                v_threshold_quality := 'medium';
            ELSE
                v_threshold_quality := 'low';
            END IF;
        END IF;
        
        -- ========== 步骤6: 更新device_running_thresholds表 ==========
        UPDATE public.device_running_thresholds
        SET 
            running_mode = v_running_mode,
            running_time_ratio = v_running_time_ratio,
            threshold_quality = v_threshold_quality,
            data_days_available = v_data_days_available,
            updated_at = NOW(),
            updated_by = 'sp_detect_running_mode_simple'
        WHERE device_id = v_device_record.id;
        
        v_updated_count := v_updated_count + 1;
        
        RAISE NOTICE '[更新完成] device_id=%, running_mode=%, ratio=%, quality=%', 
            v_device_record.id, v_running_mode, v_running_time_ratio, v_threshold_quality;
    END LOOP;
    
    RAISE NOTICE '[存储过程完成] 共更新 % 个设备', v_updated_count;
END;
$$;

COMMENT ON PROCEDURE api.sp_detect_running_mode_simple IS 
'识别设备运行模式（持续运行 vs 频繁启停 vs 偶尔运行）。
参数:
  p_device_id: 设备ID，NULL表示处理所有设备
识别逻辑:
  1. 读取最近7天的运行状态数据（如果不足7天，使用可用天数）
  2. 计算运行时长比例 = 运行秒数 / 总秒数
  3. 判定运行模式:
     - continuous (持续运行): ratio > 0.8
     - occasional (偶尔运行): ratio < 0.2
     - frequent (频繁启停): 0.2 <= ratio <= 0.8
  4. 根据数据可用天数设置threshold_quality:
     - high: >= 7天
     - medium: 3-7天
     - low: 1-3天
     - insufficient: < 1天';

-- =====================================================================
-- 验证脚本
-- =====================================================================

-- 测试存储过程（不实际执行，仅验证语法）
DO $$
BEGIN
    RAISE NOTICE '[验证] sp_detect_running_mode_simple 存储过程已创建';
END $$;

