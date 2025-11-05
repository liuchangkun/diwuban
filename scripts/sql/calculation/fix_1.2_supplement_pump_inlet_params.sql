-- =====================================================
-- 优先级1.2修复 - 补充：pump_inlet_pressure 方法参数配置
-- =====================================================
-- 说明：补充之前因外键约束跳过的 pump_inlet_pressure 方法参数
-- 前置条件：pump_inlet_pressure 方法已注册到 calculation_method_registry
-- 执行时间：2025-10-25
-- 执行人员：AI Agent (manual_fix_1.2_supplement)
-- =====================================================

BEGIN;

-- 方法B：从水池液位推导（需要3个物理常数参数）
INSERT INTO calculation_parameters (
    station_id, 
    device_id, 
    metric_key, 
    method_id, 
    param_name, 
    param_value, 
    param_type, 
    is_optimizable,
    param_min,
    param_max,
    created_at,
    updated_at,
    updated_by,
    confidence_score
) VALUES 
    (NULL, NULL, 'pump_inlet_pressure', 'pump_inlet_pressure_method_b', 'P_atm', 0.101325, 'float', false, NULL, NULL, NOW(), NOW(), 'manual_fix_1.2_supplement', 1.0),
    (NULL, NULL, 'pump_inlet_pressure', 'pump_inlet_pressure_method_b', 'rho', 1000.0, 'float', false, NULL, NULL, NOW(), NOW(), 'manual_fix_1.2_supplement', 1.0),
    (NULL, NULL, 'pump_inlet_pressure', 'pump_inlet_pressure_method_b', 'g', 9.80665, 'float', false, NULL, NULL, NOW(), NOW(), 'manual_fix_1.2_supplement', 1.0)
ON CONFLICT (device_id, metric_key, method_id, param_name) DO UPDATE
SET 
    param_value = EXCLUDED.param_value,
    updated_at = NOW(),
    updated_by = 'manual_fix_1.2_supplement';

COMMIT;

-- =====================================================
-- 验证查询
-- =====================================================
-- 验证参数插入成功
-- SELECT method_id, param_name, param_value, is_optimizable, confidence_score
-- FROM calculation_parameters 
-- WHERE method_id = 'pump_inlet_pressure_method_b'
-- ORDER BY param_name;

-- 预期结果：3行
-- P_atm=0.101325, rho=1000.0, g=9.80665
-- 所有参数的 is_optimizable=false, confidence_score=1.0

