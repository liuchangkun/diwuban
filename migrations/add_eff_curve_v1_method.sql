-- 添加 EFF_CURVE_V1 方法到 calculation_method_registry
-- 执行时间：2025-10-26

BEGIN;

-- 插入 EFF_CURVE_V1 方法
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
    allowed_device_types
) VALUES (
    'EFF_CURVE_V1',
    'pump_efficiency',
    '基于特性曲线的效率计算',
    'CURVE',
    110,  -- 最高优先级（比EFF_SIMPLE_V1的100高）
    ARRAY['pump_flow_rate'],
    '{"description": "从泵特性曲线插值获取效率，需要设备有效率曲线数据"}'::jsonb,
    'high',
    true,
    ARRAY['pump']
)
ON CONFLICT (metric_key, method_code) DO UPDATE
SET method_id = EXCLUDED.method_id,
    method_name = EXCLUDED.method_name,
    priority = EXCLUDED.priority,
    dependencies = EXCLUDED.dependencies,
    conditions = EXCLUDED.conditions,
    accuracy_level = EXCLUDED.accuracy_level,
    is_enabled = EXCLUDED.is_enabled,
    allowed_device_types = EXCLUDED.allowed_device_types,
    updated_at = NOW();

COMMIT;

-- 验证插入
SELECT 
    method_id,
    metric_key,
    priority,
    dependencies,
    accuracy_level,
    is_enabled
FROM calculation_method_registry
WHERE metric_key = 'pump_efficiency'
ORDER BY priority DESC;

