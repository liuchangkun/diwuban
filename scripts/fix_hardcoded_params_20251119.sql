-- ============================================
-- 消除硬编码：添加缺失的全局级参数
-- 日期: 2025-11-19
-- 说明: 严格遵守三级参数体系（全局级 → 站点级 → 设备级）
-- ============================================

-- pump_flow_rate validator参数（全局级）
-- 注意：validator参数放在data_filter method下（因为validator会从params读取）
INSERT INTO calculation_parameters (metric_key, method_id, param_name, param_value, param_type, is_optimizable, updated_by)
VALUES
  ('pump_flow_rate', 'data_filter', 'min_flow', 0.0, 'float', FALSE, 'system'),
  ('pump_flow_rate', 'data_filter', 'max_ratio', 1.1, 'float', FALSE, 'system')
ON CONFLICT (device_id, metric_key, method_id, param_name)
DO UPDATE SET
  param_value = EXCLUDED.param_value,
  updated_at = CURRENT_TIMESTAMP,
  updated_by = EXCLUDED.updated_by;

-- pump_inlet_pressure validator参数（全局级）
-- 注意：validator参数放在pump_inlet_pressure_method_b下
INSERT INTO calculation_parameters (metric_key, method_id, param_name, param_value, param_type, is_optimizable, updated_by)
VALUES
  ('pump_inlet_pressure', 'pump_inlet_pressure_method_b', 'min_pressure', 0.0, 'float', FALSE, 'system'),
  ('pump_inlet_pressure', 'pump_inlet_pressure_method_b', 'max_pressure', 1.0, 'float', FALSE, 'system')
ON CONFLICT (device_id, metric_key, method_id, param_name)
DO UPDATE SET
  param_value = EXCLUDED.param_value,
  updated_at = CURRENT_TIMESTAMP,
  updated_by = EXCLUDED.updated_by;

-- method_g standby detection参数（全局级）
-- 注意：method_g还未创建，暂时放在data_filter下
INSERT INTO calculation_parameters (metric_key, method_id, param_name, param_value, param_type, is_optimizable, updated_by)
VALUES
  ('pump_flow_rate', 'data_filter', 'standby_power_threshold', 1.0, 'float', FALSE, 'system'),
  ('pump_flow_rate', 'data_filter', 'standby_freq_threshold', 1.0, 'float', FALSE, 'system')
ON CONFLICT (device_id, metric_key, method_id, param_name)
DO UPDATE SET
  param_value = EXCLUDED.param_value,
  updated_at = CURRENT_TIMESTAMP,
  updated_by = EXCLUDED.updated_by;

-- 验证参数已正确插入
SELECT
  metric_key,
  method_id,
  param_name,
  param_value,
  CASE
    WHEN station_id IS NULL AND device_id IS NULL THEN '全局级'
    WHEN station_id IS NOT NULL AND device_id IS NULL THEN '站点级'
    WHEN device_id IS NOT NULL THEN '设备级'
  END as param_level
FROM calculation_parameters
WHERE metric_key IN ('pump_flow_rate', 'pump_inlet_pressure')
  AND param_name IN ('min_flow', 'max_ratio', 'standby_power_threshold', 'standby_freq_threshold', 'min_pressure', 'max_pressure')
ORDER BY metric_key, param_name;

