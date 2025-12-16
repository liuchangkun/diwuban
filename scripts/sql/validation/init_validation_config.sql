-- ============================================================================
-- 初始化验证配置数据
-- ============================================================================
-- 目的：为所有指标添加验证配置
-- 作者：AI Assistant
-- 日期：2025-10-05
-- ============================================================================

BEGIN;

-- 清空现有配置（如果需要重新初始化）
-- TRUNCATE TABLE calculation_validation_config;

-- ============================================================================
-- 1. pump_efficiency（泵效率）
-- ============================================================================
INSERT INTO calculation_validation_config (
    station_id, device_id, metric_key, validator_type, params, is_enabled, priority
) VALUES
    -- 基本验证
    (NULL, NULL, 'pump_efficiency', 'not_nan', '{}', TRUE, 10),
    (NULL, NULL, 'pump_efficiency', 'not_inf', '{}', TRUE, 10),
    -- 效率验证
    (NULL, NULL, 'pump_efficiency', 'efficiency', '{"strict_mode": false}', TRUE, 20),
    -- 范围验证（作为备用）
    (NULL, NULL, 'pump_efficiency', 'range', '{"min": 0, "max": 100}', TRUE, 30)
ON CONFLICT (COALESCE(station_id, 0), COALESCE(device_id, 0), metric_key, validator_type) 
DO UPDATE SET 
    params = EXCLUDED.params,
    is_enabled = EXCLUDED.is_enabled,
    priority = EXCLUDED.priority,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- 2. pump_flow_rate（泵流量）
-- ============================================================================
INSERT INTO calculation_validation_config (
    station_id, device_id, metric_key, validator_type, params, is_enabled, priority
) VALUES
    (NULL, NULL, 'pump_flow_rate', 'not_nan', '{}', TRUE, 10),
    (NULL, NULL, 'pump_flow_rate', 'not_inf', '{}', TRUE, 10),
    (NULL, NULL, 'pump_flow_rate', 'non_negative', '{}', TRUE, 20),
    (NULL, NULL, 'pump_flow_rate', 'range', '{"min": 0, "max": 10000}', TRUE, 30)
ON CONFLICT (COALESCE(station_id, 0), COALESCE(device_id, 0), metric_key, validator_type) 
DO UPDATE SET 
    params = EXCLUDED.params,
    is_enabled = EXCLUDED.is_enabled,
    priority = EXCLUDED.priority,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- 3. pump_head（泵扬程）
-- ============================================================================
INSERT INTO calculation_validation_config (
    station_id, device_id, metric_key, validator_type, params, is_enabled, priority
) VALUES
    (NULL, NULL, 'pump_head', 'not_nan', '{}', TRUE, 10),
    (NULL, NULL, 'pump_head', 'not_inf', '{}', TRUE, 10),
    (NULL, NULL, 'pump_head', 'non_negative', '{}', TRUE, 20),
    (NULL, NULL, 'pump_head', 'range', '{"min": 0, "max": 500}', TRUE, 30)
ON CONFLICT (COALESCE(station_id, 0), COALESCE(device_id, 0), metric_key, validator_type) 
DO UPDATE SET 
    params = EXCLUDED.params,
    is_enabled = EXCLUDED.is_enabled,
    priority = EXCLUDED.priority,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- 4. pump_outlet_pressure（泵出口压力）
-- ============================================================================
INSERT INTO calculation_validation_config (
    station_id, device_id, metric_key, validator_type, params, is_enabled, priority
) VALUES
    (NULL, NULL, 'pump_outlet_pressure', 'not_nan', '{}', TRUE, 10),
    (NULL, NULL, 'pump_outlet_pressure', 'not_inf', '{}', TRUE, 10),
    (NULL, NULL, 'pump_outlet_pressure', 'pressure', '{"pressure_type": "outlet", "tolerance": 0.2}', TRUE, 20),
    (NULL, NULL, 'pump_outlet_pressure', 'range', '{"min": 0, "max": 2.0}', TRUE, 30)
ON CONFLICT (COALESCE(station_id, 0), COALESCE(device_id, 0), metric_key, validator_type) 
DO UPDATE SET 
    params = EXCLUDED.params,
    is_enabled = EXCLUDED.is_enabled,
    priority = EXCLUDED.priority,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- 5. pump_inlet_pressure（泵进口压力）
-- ============================================================================
INSERT INTO calculation_validation_config (
    station_id, device_id, metric_key, validator_type, params, is_enabled, priority
) VALUES
    (NULL, NULL, 'pump_inlet_pressure', 'not_nan', '{}', TRUE, 10),
    (NULL, NULL, 'pump_inlet_pressure', 'not_inf', '{}', TRUE, 10),
    (NULL, NULL, 'pump_inlet_pressure', 'pressure', '{"pressure_type": "inlet", "tolerance": 0.2}', TRUE, 20),
    (NULL, NULL, 'pump_inlet_pressure', 'range', '{"min": -0.1, "max": 1.0}', TRUE, 30)
ON CONFLICT (COALESCE(station_id, 0), COALESCE(device_id, 0), metric_key, validator_type) 
DO UPDATE SET 
    params = EXCLUDED.params,
    is_enabled = EXCLUDED.is_enabled,
    priority = EXCLUDED.priority,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- 6. pump_speed（泵转速）
-- ============================================================================
INSERT INTO calculation_validation_config (
    station_id, device_id, metric_key, validator_type, params, is_enabled, priority
) VALUES
    (NULL, NULL, 'pump_speed', 'not_nan', '{}', TRUE, 10),
    (NULL, NULL, 'pump_speed', 'not_inf', '{}', TRUE, 10),
    (NULL, NULL, 'pump_speed', 'speed', '{"tolerance": 0.2}', TRUE, 20),
    (NULL, NULL, 'pump_speed', 'range', '{"min": 0, "max": 3000}', TRUE, 30)
ON CONFLICT (COALESCE(station_id, 0), COALESCE(device_id, 0), metric_key, validator_type) 
DO UPDATE SET 
    params = EXCLUDED.params,
    is_enabled = EXCLUDED.is_enabled,
    priority = EXCLUDED.priority,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- 7. pump_torque（泵扭矩）
-- ============================================================================
INSERT INTO calculation_validation_config (
    station_id, device_id, metric_key, validator_type, params, is_enabled, priority
) VALUES
    (NULL, NULL, 'pump_torque', 'not_nan', '{}', TRUE, 10),
    (NULL, NULL, 'pump_torque', 'not_inf', '{}', TRUE, 10),
    (NULL, NULL, 'pump_torque', 'torque', '{"tolerance": 0.15}', TRUE, 20),
    (NULL, NULL, 'pump_torque', 'range', '{"min": 0, "max": 10000}', TRUE, 30)
ON CONFLICT (COALESCE(station_id, 0), COALESCE(device_id, 0), metric_key, validator_type) 
DO UPDATE SET 
    params = EXCLUDED.params,
    is_enabled = EXCLUDED.is_enabled,
    priority = EXCLUDED.priority,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- 8. pump_shaft_power（泵轴功率）
-- ============================================================================
INSERT INTO calculation_validation_config (
    station_id, device_id, metric_key, validator_type, params, is_enabled, priority
) VALUES
    (NULL, NULL, 'pump_shaft_power', 'not_nan', '{}', TRUE, 10),
    (NULL, NULL, 'pump_shaft_power', 'not_inf', '{}', TRUE, 10),
    (NULL, NULL, 'pump_shaft_power', 'non_negative', '{}', TRUE, 20),
    (NULL, NULL, 'pump_shaft_power', 'power_consistency', '{"power_type": "shaft", "tolerance": 0.15}', TRUE, 25),
    (NULL, NULL, 'pump_shaft_power', 'range', '{"min": 0, "max": 1000}', TRUE, 30)
ON CONFLICT (COALESCE(station_id, 0), COALESCE(device_id, 0), metric_key, validator_type) 
DO UPDATE SET 
    params = EXCLUDED.params,
    is_enabled = EXCLUDED.is_enabled,
    priority = EXCLUDED.priority,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- 9. pump_hydraulic_power（泵水力功率）
-- ============================================================================
INSERT INTO calculation_validation_config (
    station_id, device_id, metric_key, validator_type, params, is_enabled, priority
) VALUES
    (NULL, NULL, 'pump_hydraulic_power', 'not_nan', '{}', TRUE, 10),
    (NULL, NULL, 'pump_hydraulic_power', 'not_inf', '{}', TRUE, 10),
    (NULL, NULL, 'pump_hydraulic_power', 'non_negative', '{}', TRUE, 20),
    (NULL, NULL, 'pump_hydraulic_power', 'power_consistency', '{"power_type": "hydraulic", "tolerance": 0.15}', TRUE, 25),
    (NULL, NULL, 'pump_hydraulic_power', 'range', '{"min": 0, "max": 1000}', TRUE, 30)
ON CONFLICT (COALESCE(station_id, 0), COALESCE(device_id, 0), metric_key, validator_type) 
DO UPDATE SET 
    params = EXCLUDED.params,
    is_enabled = EXCLUDED.is_enabled,
    priority = EXCLUDED.priority,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- 10. main_pipeline_outlet_pressure（总管出口压力）
-- ============================================================================
INSERT INTO calculation_validation_config (
    station_id, device_id, metric_key, validator_type, params, is_enabled, priority
) VALUES
    (NULL, NULL, 'main_pipeline_outlet_pressure', 'not_nan', '{}', TRUE, 10),
    (NULL, NULL, 'main_pipeline_outlet_pressure', 'not_inf', '{}', TRUE, 10),
    (NULL, NULL, 'main_pipeline_outlet_pressure', 'pressure', '{"pressure_type": "outlet", "tolerance": 0.2}', TRUE, 20),
    (NULL, NULL, 'main_pipeline_outlet_pressure', 'range', '{"min": 0, "max": 2.0}', TRUE, 30)
ON CONFLICT (COALESCE(station_id, 0), COALESCE(device_id, 0), metric_key, validator_type) 
DO UPDATE SET 
    params = EXCLUDED.params,
    is_enabled = EXCLUDED.is_enabled,
    priority = EXCLUDED.priority,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- 11. main_pipeline_inlet_pressure（总管进口压力）
-- ============================================================================
INSERT INTO calculation_validation_config (
    station_id, device_id, metric_key, validator_type, params, is_enabled, priority
) VALUES
    (NULL, NULL, 'main_pipeline_inlet_pressure', 'not_nan', '{}', TRUE, 10),
    (NULL, NULL, 'main_pipeline_inlet_pressure', 'not_inf', '{}', TRUE, 10),
    (NULL, NULL, 'main_pipeline_inlet_pressure', 'pressure', '{"pressure_type": "inlet", "tolerance": 0.2}', TRUE, 20),
    (NULL, NULL, 'main_pipeline_inlet_pressure', 'range', '{"min": -0.1, "max": 1.0}', TRUE, 30)
ON CONFLICT (COALESCE(station_id, 0), COALESCE(device_id, 0), metric_key, validator_type) 
DO UPDATE SET 
    params = EXCLUDED.params,
    is_enabled = EXCLUDED.is_enabled,
    priority = EXCLUDED.priority,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- 12. pump_cumulative_flow（泵累计流量）
-- ============================================================================
INSERT INTO calculation_validation_config (
    station_id, device_id, metric_key, validator_type, params, is_enabled, priority
) VALUES
    (NULL, NULL, 'pump_cumulative_flow', 'not_nan', '{}', TRUE, 10),
    (NULL, NULL, 'pump_cumulative_flow', 'not_inf', '{}', TRUE, 10),
    (NULL, NULL, 'pump_cumulative_flow', 'non_negative', '{}', TRUE, 20),
    (NULL, NULL, 'pump_cumulative_flow', 'range', '{"min": 0, "max": 1000000000}', TRUE, 30)
ON CONFLICT (COALESCE(station_id, 0), COALESCE(device_id, 0), metric_key, validator_type) 
DO UPDATE SET 
    params = EXCLUDED.params,
    is_enabled = EXCLUDED.is_enabled,
    priority = EXCLUDED.priority,
    updated_at = CURRENT_TIMESTAMP;

COMMIT;

-- 显示初始化结果
SELECT '========================================' as separator;
SELECT '验证配置初始化完成！' as result;
SELECT '========================================' as separator;

SELECT 
    metric_key,
    COUNT(*) as validator_count,
    STRING_AGG(validator_type, ', ' ORDER BY priority) as validators
FROM calculation_validation_config
WHERE station_id IS NULL AND device_id IS NULL
GROUP BY metric_key
ORDER BY metric_key;

