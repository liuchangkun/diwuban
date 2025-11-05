-- 优先级2.1：恢复 main_pipeline_inlet_pressure 方法优先级
-- 说明：由于优先级1.1已完成（pump_inlet_pressure已修复），直接恢复最终优先级

-- 恢复依赖 pump_inlet_pressure 的方法优先级
UPDATE calculation_method_registry
SET priority = 100,
    updated_at = NOW()
WHERE method_id = 'main_pipeline_inlet_pressure_method_a'
  AND metric_key = 'main_pipeline_inlet_pressure';

UPDATE calculation_method_registry
SET priority = 80,
    updated_at = NOW()
WHERE method_id = 'main_pipeline_inlet_pressure_method_c'
  AND metric_key = 'main_pipeline_inlet_pressure';

-- 调整不依赖 pump_inlet_pressure 的方法优先级
UPDATE calculation_method_registry
SET priority = 90,
    updated_at = NOW()
WHERE method_id = 'main_pipeline_inlet_pressure_method_b'
  AND metric_key = 'main_pipeline_inlet_pressure';

UPDATE calculation_method_registry
SET priority = 70,
    updated_at = NOW()
WHERE method_id = 'PIN_COEF_V1'
  AND metric_key = 'main_pipeline_inlet_pressure';

-- 验证结果
SELECT method_id, priority, dependencies
FROM calculation_method_registry
WHERE metric_key = 'main_pipeline_inlet_pressure'
ORDER BY priority DESC;

