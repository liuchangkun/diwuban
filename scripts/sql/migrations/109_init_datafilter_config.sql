\encoding UTF8
SET client_encoding = 'UTF8';

-- =====================================================================
-- 迁移脚本: 109_init_datafilter_config.sql
-- 用途: 初始化 DataFilter 配置到 calculation_parameters 表
-- 创建日期: 2025-11-14
-- 依赖: calculation_parameters 表、calculation_method_registry 表、dim_metric_config 表已存在
-- 理由: DataFilter 需要从数据库读取配置参数，消除硬编码
-- 修订说明:
--   1. 创建 data_filter 方法记录（如果不存在）
--   2. 插入 DataFilter 所需的3个全局参数：max_flow, max_power, max_freq
--   3. 使用 metric_key='pump_flow_rate', method_id='data_filter'
--   4. 全局参数：station_id=NULL, device_id=NULL
-- =====================================================================

BEGIN;

-- ========== 步骤1: 创建 data_filter 方法记录 ==========

DO $$
BEGIN
    -- 检查 data_filter 方法是否已存在
    IF NOT EXISTS (
        SELECT 1
        FROM calculation_method_registry
        WHERE method_id = 'data_filter'
            AND metric_key = 'pump_flow_rate'
    ) THEN
        -- 插入 data_filter 方法记录
        INSERT INTO calculation_method_registry (
            method_id,
            metric_key,
            method_name,
            method_code,
            priority,
            dependencies,
            conditions,
            formula_ref,
            accuracy_level,
            is_enabled,
            allowed_device_types
        ) VALUES (
            'data_filter',
            'pump_flow_rate',
            '数据过滤',
            'DataFilter',
            0,  -- 最高优先级（在所有计算方法之前执行）
            ARRAY['main_pipeline_flow_rate', 'pump_active_power', 'pump_frequency']::TEXT[],
            '{"description": "过滤无效数据，确保计算输入的质量"}'::JSONB,
            NULL,
            'preprocessing',
            TRUE,
            ARRAY['pump']::TEXT[]
        );
        
        RAISE NOTICE '✅ 成功创建 data_filter 方法记录';
    ELSE
        RAISE NOTICE '⚠️ data_filter 方法记录已存在，跳过创建';
    END IF;
END $$;

-- ========== 步骤2: 插入 DataFilter 配置参数 ==========

DO $$
DECLARE
    v_inserted_count INTEGER := 0;
BEGIN
    -- 插入 max_flow 参数（如果不存在）
    IF NOT EXISTS (
        SELECT 1
        FROM calculation_parameters
        WHERE metric_key = 'pump_flow_rate'
            AND method_id = 'data_filter'
            AND param_name = 'max_flow'
            AND station_id IS NULL
            AND device_id IS NULL
    ) THEN
        INSERT INTO calculation_parameters (
            station_id,
            device_id,
            metric_key,
            method_id,
            param_name,
            param_value,
            param_type,
            is_optimizable,
            updated_by,
            confidence_score
        ) VALUES (
            NULL,  -- 全局参数
            NULL,  -- 全局参数
            'pump_flow_rate',
            'data_filter',
            'max_flow',
            500.0,  -- 流量上限（m³/h）
            'float',
            FALSE,  -- 不可优化（固定阈值）
            'system',
            1.0  -- 高置信度
        );
        v_inserted_count := v_inserted_count + 1;
        RAISE NOTICE '✅ 插入参数: max_flow = 500.0';
    ELSE
        RAISE NOTICE '⚠️ 参数 max_flow 已存在，跳过插入';
    END IF;
    
    -- 插入 max_power 参数（如果不存在）
    IF NOT EXISTS (
        SELECT 1
        FROM calculation_parameters
        WHERE metric_key = 'pump_flow_rate'
            AND method_id = 'data_filter'
            AND param_name = 'max_power'
            AND station_id IS NULL
            AND device_id IS NULL
    ) THEN
        INSERT INTO calculation_parameters (
            station_id,
            device_id,
            metric_key,
            method_id,
            param_name,
            param_value,
            param_type,
            is_optimizable,
            updated_by,
            confidence_score
        ) VALUES (
            NULL,  -- 全局参数
            NULL,  -- 全局参数
            'pump_flow_rate',
            'data_filter',
            'max_power',
            200.0,  -- 功率上限（kW）
            'float',
            FALSE,  -- 不可优化（固定阈值）
            'system',
            1.0  -- 高置信度
        );
        v_inserted_count := v_inserted_count + 1;
        RAISE NOTICE '✅ 插入参数: max_power = 200.0';
    ELSE
        RAISE NOTICE '⚠️ 参数 max_power 已存在，跳过插入';
    END IF;
    
    -- 插入 max_freq 参数（如果不存在）
    IF NOT EXISTS (
        SELECT 1
        FROM calculation_parameters
        WHERE metric_key = 'pump_flow_rate'
            AND method_id = 'data_filter'
            AND param_name = 'max_freq'
            AND station_id IS NULL
            AND device_id IS NULL
    ) THEN
        INSERT INTO calculation_parameters (
            station_id,
            device_id,
            metric_key,
            method_id,
            param_name,
            param_value,
            param_type,
            is_optimizable,
            updated_by,
            confidence_score
        ) VALUES (
            NULL,  -- 全局参数
            NULL,  -- 全局参数
            'pump_flow_rate',
            'data_filter',
            'max_freq',
            50.0,  -- 频率上限（Hz）
            'float',
            FALSE,  -- 不可优化（固定阈值）
            'system',
            1.0  -- 高置信度
        );
        v_inserted_count := v_inserted_count + 1;
        RAISE NOTICE '✅ 插入参数: max_freq = 50.0';
    ELSE
        RAISE NOTICE '⚠️ 参数 max_freq 已存在，跳过插入';
    END IF;
    
    RAISE NOTICE '📊 总计插入 % 个参数', v_inserted_count;
END $$;

COMMIT;

-- ========== 验证插入结果 ==========

-- 显示插入的参数
SELECT 
    id,
    station_id,
    device_id,
    metric_key,
    method_id,
    param_name,
    param_value,
    param_type,
    is_optimizable,
    confidence_score,
    created_at
FROM calculation_parameters
WHERE metric_key = 'pump_flow_rate'
    AND method_id = 'data_filter'
ORDER BY param_name;

