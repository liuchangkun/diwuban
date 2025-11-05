\encoding UTF8
SET client_encoding = 'UTF8';

-- =====================================================================
-- 存储过程: sp_detect_device_type_simple
-- 用途: 识别设备类型（变频泵 vs 软启动泵）
-- 创建日期: 2025-10-31
-- 修订说明: 优先使用dim_devices.pump_type，如果为NULL才执行自动识别
-- 依赖: 060_alter_device_running_thresholds_phase1.sql
-- =====================================================================

CREATE OR REPLACE PROCEDURE api.sp_detect_device_type_simple(
    p_device_id BIGINT DEFAULT NULL  -- NULL表示处理所有设备
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_device_record RECORD;
    v_pump_type TEXT;
    v_device_type TEXT;
    v_device_type_source TEXT;
    v_device_type_auto_detected BOOLEAN;
    v_enable_f BOOLEAN;
    v_weight_current DOUBLE PRECISION;
    v_weight_power DOUBLE PRECISION;
    v_weight_frequency DOUBLE PRECISION;
    v_threshold_quality TEXT;
    v_data_days_available INTEGER;
    
    -- 自动识别相关变量
    v_mean_freq DOUBLE PRECISION;
    v_std_freq DOUBLE PRECISION;
    v_freq_cv DOUBLE PRECISION;
    v_freq_range DOUBLE PRECISION;
    v_min_ts TIMESTAMPTZ;
    v_max_ts TIMESTAMPTZ;
    
    v_updated_count INTEGER := 0;
BEGIN
    RAISE NOTICE '[存储过程开始] sp_detect_device_type_simple, device_id=%', COALESCE(p_device_id::TEXT, 'ALL');
    
    -- 遍历设备
    FOR v_device_record IN
        SELECT d.id, d.name, d.pump_type
        FROM public.dim_devices d
        WHERE d.type = 'pump'
            AND (p_device_id IS NULL OR d.id = p_device_id)
        ORDER BY d.id
    LOOP
        RAISE NOTICE '[处理设备] device_id=%, name=%', v_device_record.id, v_device_record.name;
        
        v_pump_type := v_device_record.pump_type;
        
        -- ========== 步骤1: 优先使用dim_devices.pump_type ==========
        IF v_pump_type IS NOT NULL THEN
            RAISE NOTICE '[使用配置] pump_type=%', v_pump_type;
            
            -- 映射pump_type到device_type
            v_device_type := CASE v_pump_type
                WHEN 'variable_frequency' THEN 'vfd'
                WHEN 'soft_start' THEN 'soft_start'
                ELSE 'unknown'
            END;
            
            v_device_type_source := 'config';
            v_device_type_auto_detected := FALSE;
            v_threshold_quality := 'high';  -- 配置文件数据质量高
            v_data_days_available := NULL;  -- 不需要历史数据
            
            -- 根据device_type设置enable_f和权重
            IF v_device_type = 'vfd' THEN
                v_enable_f := TRUE;
                v_weight_current := 0.4;
                v_weight_power := 0.3;
                v_weight_frequency := 0.3;
                RAISE NOTICE '[设备类型] 变频泵 (VFD), 权重=(0.4, 0.3, 0.3)';
            ELSIF v_device_type = 'soft_start' THEN
                v_enable_f := FALSE;
                v_weight_current := 0.6;
                v_weight_power := 0.4;
                v_weight_frequency := 0.0;
                RAISE NOTICE '[设备类型] 软启动泵 (Soft-start), 权重=(0.6, 0.4, 0.0)';
            ELSE
                -- 保持原有配置
                SELECT enable_f INTO v_enable_f
                FROM public.device_running_thresholds
                WHERE device_id = v_device_record.id;
                
                v_weight_current := 0.5;
                v_weight_power := 0.3;
                v_weight_frequency := 0.2;
                RAISE NOTICE '[设备类型] 未知, 保持原有配置';
            END IF;
            
        ELSE
            -- ========== 步骤2: pump_type为NULL，执行自动识别 ==========
            RAISE NOTICE '[自动识别] pump_type为NULL，开始自动识别';
            
            -- 计算数据可用天数
            SELECT 
                MIN(ts) AS min_ts,
                MAX(ts) AS max_ts
            INTO v_min_ts, v_max_ts
            FROM public.fact_measurements
            WHERE device_id = v_device_record.id
                AND ts >= NOW() - INTERVAL '7 days'
                AND frequency IS NOT NULL;
            
            IF v_min_ts IS NULL THEN
                v_data_days_available := 0;
            ELSE
                v_data_days_available := EXTRACT(EPOCH FROM (v_max_ts - v_min_ts)) / 86400.0;
            END IF;
            
            RAISE NOTICE '[数据可用性] data_days_available=% 天', v_data_days_available;
            
            -- 检查数据是否充足
            IF v_data_days_available < 1 THEN
                RAISE WARNING '[数据不足] device_id=% 数据不足1天，无法识别', v_device_record.id;
                v_device_type := 'unknown';
                v_device_type_source := 'unknown';
                v_device_type_auto_detected := FALSE;
                v_threshold_quality := 'insufficient';
                
                -- 保持原有配置
                SELECT enable_f INTO v_enable_f
                FROM public.device_running_thresholds
                WHERE device_id = v_device_record.id;
                
                v_weight_current := 0.5;
                v_weight_power := 0.3;
                v_weight_frequency := 0.2;
            ELSE
                -- 计算频率统计特征
                SELECT 
                    AVG(frequency) AS mean_freq,
                    STDDEV(frequency) AS std_freq,
                    MAX(frequency) - MIN(frequency) AS freq_range
                INTO v_mean_freq, v_std_freq, v_freq_range
                FROM public.fact_measurements
                WHERE device_id = v_device_record.id
                    AND ts >= NOW() - INTERVAL '7 days'
                    AND frequency IS NOT NULL
                    AND frequency > 0;
                
                -- 计算变异系数
                IF v_mean_freq > 0 THEN
                    v_freq_cv := v_std_freq / v_mean_freq;
                ELSE
                    v_freq_cv := 0;
                END IF;
                
                RAISE NOTICE '[频率统计] mean=%, std=%, cv=%, range=%', 
                    v_mean_freq, v_std_freq, v_freq_cv, v_freq_range;
                
                -- 判定设备类型
                IF v_freq_cv > 0.02 AND v_freq_range > 3.0 THEN
                    v_device_type := 'vfd';
                    v_enable_f := TRUE;
                    v_weight_current := 0.4;
                    v_weight_power := 0.3;
                    v_weight_frequency := 0.3;
                    RAISE NOTICE '[自动识别结果] 变频泵 (VFD), cv=% > 0.02, range=% > 3.0', v_freq_cv, v_freq_range;
                ELSIF v_freq_cv < 0.01 AND v_freq_range < 1.0 THEN
                    v_device_type := 'soft_start';
                    v_enable_f := FALSE;
                    v_weight_current := 0.6;
                    v_weight_power := 0.4;
                    v_weight_frequency := 0.0;
                    RAISE NOTICE '[自动识别结果] 软启动泵 (Soft-start), cv=% < 0.01, range=% < 1.0', v_freq_cv, v_freq_range;
                ELSE
                    v_device_type := 'unknown';
                    -- 保持原有配置
                    SELECT enable_f INTO v_enable_f
                    FROM public.device_running_thresholds
                    WHERE device_id = v_device_record.id;
                    
                    v_weight_current := 0.5;
                    v_weight_power := 0.3;
                    v_weight_frequency := 0.2;
                    RAISE NOTICE '[自动识别结果] 未知, cv=%, range=%', v_freq_cv, v_freq_range;
                END IF;
                
                v_device_type_source := 'auto';
                v_device_type_auto_detected := TRUE;
                
                -- 根据data_days_available设置threshold_quality
                IF v_data_days_available >= 7 THEN
                    v_threshold_quality := 'high';
                ELSIF v_data_days_available >= 3 THEN
                    v_threshold_quality := 'medium';
                ELSE
                    v_threshold_quality := 'low';
                END IF;
            END IF;
        END IF;
        
        -- ========== 步骤3: 更新device_running_thresholds表 ==========
        UPDATE public.device_running_thresholds
        SET 
            device_type = v_device_type,
            device_type_source = v_device_type_source,
            device_type_auto_detected = v_device_type_auto_detected,
            enable_f = v_enable_f,
            signal_weight_current = v_weight_current,
            signal_weight_power = v_weight_power,
            signal_weight_frequency = v_weight_frequency,
            threshold_quality = v_threshold_quality,
            data_days_available = v_data_days_available,
            updated_at = NOW(),
            updated_by = 'sp_detect_device_type_simple'
        WHERE device_id = v_device_record.id;
        
        v_updated_count := v_updated_count + 1;
        
        RAISE NOTICE '[更新完成] device_id=%, device_type=%, source=%, quality=%', 
            v_device_record.id, v_device_type, v_device_type_source, v_threshold_quality;
    END LOOP;
    
    RAISE NOTICE '[存储过程完成] 共更新 % 个设备', v_updated_count;
END;
$$;

COMMENT ON PROCEDURE api.sp_detect_device_type_simple IS 
'识别设备类型（变频泵 vs 软启动泵）。优先使用dim_devices.pump_type，如果为NULL才执行自动识别。
参数:
  p_device_id: 设备ID，NULL表示处理所有设备
识别逻辑:
  1. 优先使用dim_devices.pump_type（来自配置文件）
  2. 如果pump_type为NULL，基于频率变异系数(CV)自动识别
  3. VFD泵: CV>0.02 且 频率范围>3Hz
  4. 软启动泵: CV<0.01 且 频率范围<1Hz
  5. 根据设备类型设置enable_f和信号权重';

-- =====================================================================
-- 验证脚本
-- =====================================================================

-- 测试存储过程（不实际执行，仅验证语法）
DO $$
BEGIN
    RAISE NOTICE '[验证] sp_detect_device_type_simple 存储过程已创建';
END $$;

