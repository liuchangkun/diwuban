-- ============================================================================
-- 修复 pump_shaft_power 参数缺失问题
-- ============================================================================
-- 
-- 问题：pump_shaft_power 覆盖率只有9.4%，损失了63.5%的有效数据
-- 
-- 根本原因：
-- 1. 数据库中缺失 max_power 和 max_shaft_power 参数
-- 2. ParameterManager 使用了硬编码默认值 max_power=200.0
-- 3. 导致 P_active > 200 kW 的数据全部被过滤（16,284条记录）
-- 
-- 修复方案：
-- 1. 添加 max_power=350.0（基于实际数据最大值323.68 kW + 安全余量）
-- 2. 添加 max_shaft_power=312.0（基于公式 350 × 0.8924）
-- 
-- 预期效果：
-- - 覆盖率从 9.4% 提升到 30.7%（+226%）
-- - 恢复 16,284 条有效数据
-- 
-- ============================================================================

-- 为设备1-6添加 max_power 参数
INSERT INTO calculation_parameters (station_id, device_id, metric_key, param_name, param_value, param_type)
VALUES 
  (1, 1, 'pump_shaft_power', 'max_power', '350.0', 'float'),
  (1, 2, 'pump_shaft_power', 'max_power', '350.0', 'float'),
  (1, 3, 'pump_shaft_power', 'max_power', '350.0', 'float'),
  (1, 4, 'pump_shaft_power', 'max_power', '350.0', 'float'),
  (1, 5, 'pump_shaft_power', 'max_power', '350.0', 'float'),
  (1, 6, 'pump_shaft_power', 'max_power', '350.0', 'float');

-- 为设备1-6添加 max_shaft_power 参数
-- 计算公式：P_shaft = P_active × eta_motor × eta_vfd = P_active × 0.92 × 0.97 = P_active × 0.8924
-- max_shaft_power = 350.0 × 0.8924 = 312.34 ≈ 312.0
INSERT INTO calculation_parameters (station_id, device_id, metric_key, param_name, param_value, param_type)
VALUES 
  (1, 1, 'pump_shaft_power', 'max_shaft_power', '312.0', 'float'),
  (1, 2, 'pump_shaft_power', 'max_shaft_power', '312.0', 'float'),
  (1, 3, 'pump_shaft_power', 'max_shaft_power', '312.0', 'float'),
  (1, 4, 'pump_shaft_power', 'max_shaft_power', '312.0', 'float'),
  (1, 5, 'pump_shaft_power', 'max_shaft_power', '312.0', 'float'),
  (1, 6, 'pump_shaft_power', 'max_shaft_power', '312.0', 'float');

-- 验证参数已正确插入
SELECT 
    device_id,
    param_name,
    param_value,
    param_type
FROM calculation_parameters
WHERE station_id = 1
  AND metric_key = 'pump_shaft_power'
  AND device_id IN (1,2,3,4,5,6)
ORDER BY device_id, param_name;

