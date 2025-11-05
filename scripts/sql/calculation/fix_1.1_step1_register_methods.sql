-- =====================================================
-- 优先级1.1修复 - 步骤1：注册 pump_inlet_pressure 方法
-- =====================================================
-- 说明：将 pump_inlet_pressure 的计算方法注册到 calculation_method_registry 表
-- 执行时间：2025-10-25
-- 执行人员：AI Agent (manual_fix_1.1_step1)
-- =====================================================

BEGIN;

-- 方法B：从 pool_liquid_level 推导（推荐，优先级最高，避免循环依赖）
INSERT INTO calculation_method_registry (
    method_id,
    metric_key,
    method_name,
    method_code,
    priority,
    dependencies,
    conditions,
    accuracy_level,
    is_enabled,
    allowed_device_types,
    created_at,
    updated_at
) VALUES (
    'pump_inlet_pressure_method_b',
    'pump_inlet_pressure',
    '从水池液位推算',
    'B',
    100,
    ARRAY['pool_liquid_level'],
    '{"description": "P_in = P_atm + ρ × g × L / 1e6"}'::jsonb,
    'high',
    true,
    ARRAY['pump'],
    NOW(),
    NOW()
)
ON CONFLICT (method_id) DO UPDATE
SET
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    updated_at = NOW();

-- 方法A：从 main_pipeline_inlet_pressure 推导（备选，避免循环依赖）
INSERT INTO calculation_method_registry (
    method_id,
    metric_key,
    method_name,
    method_code,
    priority,
    dependencies,
    conditions,
    accuracy_level,
    is_enabled,
    allowed_device_types,
    created_at,
    updated_at
) VALUES (
    'pump_inlet_pressure_method_a',
    'pump_inlet_pressure',
    '使用总管进口压力代替',
    'A',
    90,
    ARRAY['main_pipeline_inlet_pressure'],
    '{"description": "假设泵进口与总管进口压力相近（并联系统）"}'::jsonb,
    'medium',
    true,
    ARRAY['pump'],
    NOW(),
    NOW()
)
ON CONFLICT (method_id) DO UPDATE
SET
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    updated_at = NOW();

COMMIT;

-- =====================================================
-- 验证查询
-- =====================================================
-- 验证插入成功
-- SELECT method_id, metric_key, method_name, priority, dependencies, accuracy_level
-- FROM calculation_method_registry 
-- WHERE metric_key = 'pump_inlet_pressure'
-- ORDER BY priority DESC;

-- 预期结果：2行
-- method_id='pump_inlet_pressure_method_b', priority=100, dependencies=['pool_liquid_level']
-- method_id='pump_inlet_pressure_method_a', priority=90, dependencies=['main_pipeline_inlet_pressure']

