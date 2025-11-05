-- 修复 main_pipeline_inlet_pressure_method_c 的精度等级
-- 执行时间：2025-10-26

BEGIN;

-- 提升 method_c 的精度等级从 medium 到 high
-- 理由：method_c 使用多个泵的平均值，精度应该高于 method_a（单个泵的值）
UPDATE calculation_method_registry
SET accuracy_level = 'high',
    updated_at = NOW()
WHERE method_id = 'main_pipeline_inlet_pressure_method_c'
  AND metric_key = 'main_pipeline_inlet_pressure';

COMMIT;

-- 验证修改
SELECT 
    method_id,
    metric_key,
    accuracy_level,
    priority,
    updated_at
FROM calculation_method_registry
WHERE metric_key = 'main_pipeline_inlet_pressure'
ORDER BY priority DESC;

