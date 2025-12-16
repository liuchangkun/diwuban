-- =====================================================
-- 修复优先级1.2：物理常数参数配置
-- 创建时间：2025-10-25
-- 修复内容：插入全局物理常数和高级方法参数
-- =====================================================

BEGIN;

-- =====================================================
-- 步骤1：插入全局物理常数（跳过，因为外键约束）
-- 说明：由于calculation_parameters表有外键约束，metric_key必须存在于dim_metric_config表中
-- 因此全局物理常数将在各个方法的参数中单独插入
-- =====================================================

-- =====================================================
-- 步骤2：插入 pump_inlet_pressure 方法的参数（跳过）
-- 说明：pump_inlet_pressure方法尚未注册到calculation_method_registry表
-- 这部分参数将在优先级1.1修复完成后再插入
-- =====================================================

-- =====================================================
-- 步骤3：插入 HEAD_COEF_V1 方法的参数
-- =====================================================
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value,
    param_type, is_optimizable, param_min, param_max, updated_by, confidence_score
) VALUES 
    -- 物理常数
    (NULL, NULL, 'pump_head', 'HEAD_COEF_V1', 'rho', 1000.0, 'float', false, NULL, NULL, 'manual_fix_1.2', 1.0),
    (NULL, NULL, 'pump_head', 'HEAD_COEF_V1', 'g', 9.80665, 'float', false, NULL, NULL, 'manual_fix_1.2', 1.0),
    
    -- 系数参数（初始值，可优化）
    (NULL, NULL, 'pump_head', 'HEAD_COEF_V1', 'a0', 50.0, 'float', true, 0.0, 100.0, 'manual_fix_1.2', 0.5),
    (NULL, NULL, 'pump_head', 'HEAD_COEF_V1', 'a1', -0.01, 'float', true, -1.0, 1.0, 'manual_fix_1.2', 0.5),
    (NULL, NULL, 'pump_head', 'HEAD_COEF_V1', 'a2', -0.0001, 'float', true, -0.01, 0.01, 'manual_fix_1.2', 0.5),
    (NULL, NULL, 'pump_head', 'HEAD_COEF_V1', 'a3', 0.0, 'float', true, -10.0, 10.0, 'manual_fix_1.2', 0.5),
    (NULL, NULL, 'pump_head', 'HEAD_COEF_V1', 'a4', 0.0, 'float', true, -10.0, 10.0, 'manual_fix_1.2', 0.5),
    (NULL, NULL, 'pump_head', 'HEAD_COEF_V1', 'a5', 0.0, 'float', true, -1.0, 1.0, 'manual_fix_1.2', 0.5),
    
    -- 边界参数
    (NULL, NULL, 'pump_head', 'HEAD_COEF_V1', 'H_min', 0.0, 'float', false, NULL, NULL, 'manual_fix_1.2', 1.0),
    (NULL, NULL, 'pump_head', 'HEAD_COEF_V1', 'H_max', 100.0, 'float', false, NULL, NULL, 'manual_fix_1.2', 1.0)
ON CONFLICT (device_id, metric_key, method_id, param_name) DO UPDATE
SET param_value = EXCLUDED.param_value, updated_at = NOW();

-- =====================================================
-- 步骤4：插入 PIN_COEF_V1 方法的参数
-- =====================================================
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value,
    param_type, is_optimizable, param_min, param_max, updated_by, confidence_score
) VALUES 
    -- 物理常数
    (NULL, NULL, 'main_pipeline_inlet_pressure', 'PIN_COEF_V1', 'rho', 1000.0, 'float', false, NULL, NULL, 'manual_fix_1.2', 1.0),
    (NULL, NULL, 'main_pipeline_inlet_pressure', 'PIN_COEF_V1', 'g', 9.80665, 'float', false, NULL, NULL, 'manual_fix_1.2', 1.0),
    
    -- 系数参数（初始值，可优化）
    (NULL, NULL, 'main_pipeline_inlet_pressure', 'PIN_COEF_V1', 'b0', 101325.0, 'float', true, 50000.0, 200000.0, 'manual_fix_1.2', 0.5),
    (NULL, NULL, 'main_pipeline_inlet_pressure', 'PIN_COEF_V1', 'b1', 1.0, 'float', true, 0.5, 1.5, 'manual_fix_1.2', 0.5),
    (NULL, NULL, 'main_pipeline_inlet_pressure', 'PIN_COEF_V1', 'b2', 0.0, 'float', true, 0.0, 100.0, 'manual_fix_1.2', 0.5),
    (NULL, NULL, 'main_pipeline_inlet_pressure', 'PIN_COEF_V1', 'b3', 0.0, 'float', true, 0.0, 1000.0, 'manual_fix_1.2', 0.5),
    
    -- 边界参数
    (NULL, NULL, 'main_pipeline_inlet_pressure', 'PIN_COEF_V1', 'P_in_min', -0.1, 'float', false, NULL, NULL, 'manual_fix_1.2', 1.0),
    (NULL, NULL, 'main_pipeline_inlet_pressure', 'PIN_COEF_V1', 'P_in_max', 1.0, 'float', false, NULL, NULL, 'manual_fix_1.2', 1.0)
ON CONFLICT (device_id, metric_key, method_id, param_name) DO UPDATE
SET param_value = EXCLUDED.param_value, updated_at = NOW();

COMMIT;

-- =====================================================
-- 验证查询
-- =====================================================
-- 查询 pump_inlet_pressure 方法的参数
-- SELECT method_id, param_name, param_value, is_optimizable
-- FROM calculation_parameters
-- WHERE metric_key = 'pump_inlet_pressure'
-- ORDER BY method_id, param_name;

-- 查询 HEAD_COEF_V1 方法的参数
-- SELECT param_name, param_value, is_optimizable, param_min, param_max, confidence_score
-- FROM calculation_parameters
-- WHERE method_id = 'HEAD_COEF_V1'
-- ORDER BY param_name;

-- 查询 PIN_COEF_V1 方法的参数
-- SELECT param_name, param_value, is_optimizable, param_min, param_max, confidence_score
-- FROM calculation_parameters
-- WHERE method_id = 'PIN_COEF_V1'
-- ORDER BY param_name;

-- 统计本次修复插入的参数数量
-- SELECT COUNT(*) FROM calculation_parameters WHERE updated_by = 'manual_fix_1.2';
-- 预期结果：24个参数（3个全局 + 5个pump_inlet_pressure + 11个HEAD_COEF_V1 + 8个PIN_COEF_V1 - 3个重复）

