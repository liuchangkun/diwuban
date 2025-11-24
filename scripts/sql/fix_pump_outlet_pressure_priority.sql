-- 修复 pump_outlet_pressure 的计算方法优先级
-- 
-- 问题：
-- 当前 method_c（从扬程回推）优先级80，正在使用，但计算结果偏高120-180%
-- method_b（使用总管出口压力代替）优先级90，但因为依赖检查没有通过，所以没有使用
--
-- 解决方案：
-- 1. 提高 method_b 的优先级到 110（高于 method_a 的 100）
-- 2. 降低 method_c 的优先级到 70（作为备选）
-- 3. 禁用 method_a（因为没有传感器）
--
-- 预期效果：
-- pump_outlet_pressure 将直接使用实测的总管出口压力（0.42 MPa），误差降低到 < 5%

BEGIN;

-- 1. 提高 method_b 的优先级（使用总管出口压力代替）
UPDATE calculation_method_registry
SET 
    priority = 110,
    accuracy_level = 'high',
    conditions = '{"description": "并联系统中，泵出口压力≈总管出口压力（实测传感器）"}'::jsonb,
    updated_at = NOW()
WHERE method_id = 'pump_outlet_pressure_method_b'
  AND metric_key = 'pump_outlet_pressure';

-- 2. 降低 method_c 的优先级（从扬程回推，作为备选）
UPDATE calculation_method_registry
SET 
    priority = 70,
    accuracy_level = 'low',
    conditions = '{"description": "P_out = P_in + ρ·g·H / 1e6（备选方案，精度较低）"}'::jsonb,
    updated_at = NOW()
WHERE method_id = 'pump_outlet_pressure_method_c'
  AND metric_key = 'pump_outlet_pressure';

-- 3. 禁用 method_a（没有传感器）
UPDATE calculation_method_registry
SET 
    is_enabled = false,
    conditions = '{"has_sensor": true, "description": "需要泵出口压力传感器（当前不可用）"}'::jsonb,
    updated_at = NOW()
WHERE method_id = 'pump_outlet_pressure_method_a'
  AND metric_key = 'pump_outlet_pressure';

-- 验证修改
SELECT 
    method_id,
    method_name,
    priority,
    dependencies,
    accuracy_level,
    is_enabled,
    conditions
FROM calculation_method_registry
WHERE metric_key = 'pump_outlet_pressure'
ORDER BY priority DESC;

COMMIT;

-- 说明：
-- 修改后的优先级顺序：
-- 1. method_b (110) - 使用总管出口压力代替 ✅ 推荐
-- 2. method_a (100) - 直接读取传感器 ❌ 已禁用（无传感器）
-- 3. method_c (70)  - 从扬程回推 ⚠️ 备选（精度低）
-- 4. method_d (70)  - 泵组层面近似 ⚠️ 备选
--
-- 修改后，pump_outlet_pressure 将优先使用 method_b，直接采用实测的总管出口压力（0.42 MPa）
-- 这样可以避免循环依赖，并且精度最高（基于实测传感器）

