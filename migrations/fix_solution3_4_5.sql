-- ============================================
-- 方案3-5：计算方法注册、计算顺序、数据验证修复
-- 执行时间：2025-10-26
-- ============================================

BEGIN;

-- ============================================
-- 问题2.1：main_pipeline_inlet_pressure 优先级调整
-- ============================================

-- 恢复最终优先级（pump_inlet_pressure已修复）
UPDATE calculation_method_registry
SET priority = 100
WHERE method_id = 'main_pipeline_inlet_pressure_method_a'
  AND metric_key = 'main_pipeline_inlet_pressure';

UPDATE calculation_method_registry
SET priority = 90
WHERE method_id = 'main_pipeline_inlet_pressure_method_b'
  AND metric_key = 'main_pipeline_inlet_pressure';

UPDATE calculation_method_registry
SET priority = 80
WHERE method_id = 'main_pipeline_inlet_pressure_method_c'
  AND metric_key = 'main_pipeline_inlet_pressure';

UPDATE calculation_method_registry
SET priority = 70
WHERE method_id = 'PIN_COEF_V1'
  AND metric_key = 'main_pipeline_inlet_pressure';

-- ============================================
-- 问题2.2：pump_outlet_pressure 条件检查修复
-- ============================================

-- 移除 has_sensor 条件
UPDATE calculation_method_registry
SET conditions = '{"description": "直接从传感器读取（如果数据可用）"}'::jsonb
WHERE method_id = 'pump_outlet_pressure_method_a'
  AND metric_key = 'pump_outlet_pressure';

-- ============================================
-- 问题3.1：pump_flow_rate 条件字段统一
-- ============================================

-- 统一 min_running_pumps 为 running_count
UPDATE calculation_method_registry
SET conditions = jsonb_set(
    conditions - 'min_running_pumps',
    '{running_count}',
    conditions->'min_running_pumps'
)
WHERE method_id = 'pump_flow_rate_method_d'
  AND conditions ? 'min_running_pumps';

-- ============================================
-- 问题3.2：设备参数硬编码修复
-- ============================================

-- 移除 pump_speed_method_b 的 slip 和 pole_pairs
UPDATE calculation_method_registry
SET conditions = conditions - 'slip' - 'pole_pairs'
WHERE method_id = 'pump_speed_method_b';

COMMIT;

-- ============================================
-- 验证修改
-- ============================================

-- 验证1：main_pipeline_inlet_pressure 优先级
SELECT method_id, priority, dependencies
FROM calculation_method_registry
WHERE metric_key = 'main_pipeline_inlet_pressure'
ORDER BY priority DESC;

-- 验证2：pump_outlet_pressure_method_a 条件
SELECT method_id, conditions
FROM calculation_method_registry
WHERE method_id = 'pump_outlet_pressure_method_a';

-- 验证3：pump_flow_rate 条件字段
SELECT method_id, conditions
FROM calculation_method_registry
WHERE method_id IN ('pump_flow_rate_method_d', 'pump_flow_rate_method_e');

-- 验证4：pump_speed_method_b 条件
SELECT method_id, conditions
FROM calculation_method_registry
WHERE method_id = 'pump_speed_method_b';

