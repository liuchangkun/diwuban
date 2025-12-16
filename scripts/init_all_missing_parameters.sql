-- ============================================================================
-- 初始化所有缺失指标的参数
-- ============================================================================
-- 
-- 目标：为所有9个指标添加缺失的参数到 calculation_parameters 表
-- 
-- 参数来源：
-- 1. 物理常量：基于标准值（rho=1000.0, g=9.81, P_atm=0.101325）
-- 2. 设备参数：基于实际数据分析和工程经验
-- 3. 阈值参数：基于实际数据范围 + 安全余量
-- 
-- ============================================================================

-- ============================================================================
-- 1. 全局物理常量（适用于多个指标）
-- ============================================================================

-- 水的密度（kg/m³）
INSERT INTO calculation_parameters (station_id, device_id, metric_key, param_name, param_value, param_type)
VALUES 
  (1, NULL, 'pump_inlet_pressure', 'rho', '1000.0', 'float'),
  (1, NULL, 'pump_head', 'rho', '1000.0', 'float'),
  (1, NULL, 'pump_torque', 'rho', '1000.0', 'float'),
  (1, NULL, 'pump_hydraulic_power', 'rho', '1000.0', 'float'),
  (1, NULL, 'main_pipeline_inlet_pressure', 'rho', '1000.0', 'float');

-- 重力加速度（m/s²）
INSERT INTO calculation_parameters (station_id, device_id, metric_key, param_name, param_value, param_type)
VALUES 
  (1, NULL, 'pump_inlet_pressure', 'g', '9.81', 'float'),
  (1, NULL, 'pump_head', 'g', '9.81', 'float'),
  (1, NULL, 'pump_torque', 'g', '9.81', 'float'),
  (1, NULL, 'pump_hydraulic_power', 'g', '9.81', 'float'),
  (1, NULL, 'main_pipeline_inlet_pressure', 'g', '9.81', 'float');

-- 大气压（MPa）
INSERT INTO calculation_parameters (station_id, device_id, metric_key, param_name, param_value, param_type)
VALUES 
  (1, NULL, 'main_pipeline_inlet_pressure', 'P_atm', '0.101325', 'float');

-- ============================================================================
-- 2. pump_flow_rate 参数
-- ============================================================================

-- alpha, beta, smooth_window（设备1-6）
INSERT INTO calculation_parameters (station_id, device_id, metric_key, param_name, param_value, param_type)
SELECT 
  1 AS station_id,
  device_id,
  'pump_flow_rate' AS metric_key,
  param_name,
  param_value,
  'float' AS param_type
FROM (
  SELECT device_id, 'alpha' AS param_name, '1.0' AS param_value FROM generate_series(1, 6) AS device_id
  UNION ALL
  SELECT device_id, 'beta' AS param_name, '1.0' AS param_value FROM generate_series(1, 6) AS device_id
  UNION ALL
  SELECT device_id, 'smooth_window' AS param_name, '5' AS param_value FROM generate_series(1, 6) AS device_id
) AS params;

-- ============================================================================
-- 3. pump_inlet_pressure 参数
-- ============================================================================

-- max_liquid_level（设备1-6）
INSERT INTO calculation_parameters (station_id, device_id, metric_key, param_name, param_value, param_type)
SELECT 
  1 AS station_id,
  device_id,
  'pump_inlet_pressure' AS metric_key,
  'max_liquid_level' AS param_name,
  '10.0' AS param_value,
  'float' AS param_type
FROM generate_series(1, 6) AS device_id;

-- ============================================================================
-- 4. pump_head 参数
-- ============================================================================

-- max_pump_inlet_pressure, max_main_pipeline_outlet_pressure, max_n_running（设备1-6）
INSERT INTO calculation_parameters (station_id, device_id, metric_key, param_name, param_value, param_type)
SELECT 
  1 AS station_id,
  device_id,
  'pump_head' AS metric_key,
  param_name,
  param_value,
  'float' AS param_type
FROM (
  SELECT device_id, 'max_pump_inlet_pressure' AS param_name, '2.0' AS param_value FROM generate_series(1, 6) AS device_id
  UNION ALL
  SELECT device_id, 'max_main_pipeline_outlet_pressure' AS param_name, '2.0' AS param_value FROM generate_series(1, 6) AS device_id
  UNION ALL
  SELECT device_id, 'max_n_running' AS param_name, '10' AS param_value FROM generate_series(1, 6) AS device_id
) AS params;

-- ============================================================================
-- 5. pump_efficiency 参数
-- ============================================================================

-- eta_min, eta_max（设备1-6）
INSERT INTO calculation_parameters (station_id, device_id, metric_key, param_name, param_value, param_type)
SELECT 
  1 AS station_id,
  device_id,
  'pump_efficiency' AS metric_key,
  param_name,
  param_value,
  'float' AS param_type
FROM (
  SELECT device_id, 'eta_min' AS param_name, '0.30' AS param_value FROM generate_series(1, 6) AS device_id
  UNION ALL
  SELECT device_id, 'eta_max' AS param_name, '0.95' AS param_value FROM generate_series(1, 6) AS device_id
) AS params;

-- ============================================================================
-- 6. pump_speed 参数
-- ============================================================================

-- min_freq, max_freq, min_speed, max_speed, f_ref, n_ref, pole_pairs, slip, 
-- speed_calibration_k, speed_calibration_b（设备1-6）
INSERT INTO calculation_parameters (station_id, device_id, metric_key, param_name, param_value, param_type)
SELECT 
  1 AS station_id,
  device_id,
  'pump_speed' AS metric_key,
  param_name,
  param_value,
  'float' AS param_type
FROM (
  SELECT device_id, 'min_freq' AS param_name, '0.0' AS param_value FROM generate_series(1, 6) AS device_id
  UNION ALL
  SELECT device_id, 'max_freq' AS param_name, '60.0' AS param_value FROM generate_series(1, 6) AS device_id
  UNION ALL
  SELECT device_id, 'min_speed' AS param_name, '0.0' AS param_value FROM generate_series(1, 6) AS device_id
  UNION ALL
  SELECT device_id, 'max_speed' AS param_name, '2000.0' AS param_value FROM generate_series(1, 6) AS device_id
  UNION ALL
  SELECT device_id, 'f_ref' AS param_name, '50.0' AS param_value FROM generate_series(1, 6) AS device_id
  UNION ALL
  SELECT device_id, 'n_ref' AS param_name, '1500.0' AS param_value FROM generate_series(1, 6) AS device_id
  UNION ALL
  SELECT device_id, 'pole_pairs' AS param_name, '2' AS param_value FROM generate_series(1, 6) AS device_id
  UNION ALL
  SELECT device_id, 'slip' AS param_name, '0.02' AS param_value FROM generate_series(1, 6) AS device_id
  UNION ALL
  SELECT device_id, 'speed_calibration_k' AS param_name, '30.0' AS param_value FROM generate_series(1, 6) AS device_id
  UNION ALL
  SELECT device_id, 'speed_calibration_b' AS param_name, '0.0' AS param_value FROM generate_series(1, 6) AS device_id
) AS params;

-- ============================================================================
-- 7. pump_torque 参数
-- ============================================================================

-- max_torque（设备1-6）
INSERT INTO calculation_parameters (station_id, device_id, metric_key, param_name, param_value, param_type)
SELECT
  1 AS station_id,
  device_id,
  'pump_torque' AS metric_key,
  'max_torque' AS param_name,
  '10000.0' AS param_value,
  'float' AS param_type
FROM generate_series(1, 6) AS device_id;

-- ============================================================================
-- 8. pump_hydraulic_power 参数
-- ============================================================================

-- min_power, max_power（设备1-6）
INSERT INTO calculation_parameters (station_id, device_id, metric_key, param_name, param_value, param_type)
SELECT
  1 AS station_id,
  device_id,
  'pump_hydraulic_power' AS metric_key,
  param_name,
  param_value,
  'float' AS param_type
FROM (
  SELECT device_id, 'min_power' AS param_name, '0.0' AS param_value FROM generate_series(1, 6) AS device_id
  UNION ALL
  SELECT device_id, 'max_power' AS param_name, '500.0' AS param_value FROM generate_series(1, 6) AS device_id
) AS params;

-- ============================================================================
-- 9. pump_shaft_power 参数（⚠️ 高优先级修复）
-- ============================================================================

-- max_power（设备1-6）
-- 基于实际数据：最大值323.68 kW，设置为350.0 kW（含安全余量）
INSERT INTO calculation_parameters (station_id, device_id, metric_key, param_name, param_value, param_type)
SELECT
  1 AS station_id,
  device_id,
  'pump_shaft_power' AS metric_key,
  'max_power' AS param_name,
  '350.0' AS param_value,
  'float' AS param_type
FROM generate_series(1, 6) AS device_id;

-- max_shaft_power（设备1-6）
-- 计算公式：P_shaft = P_active × eta_motor × eta_vfd = P_active × 0.8924
-- max_shaft_power = 350.0 × 0.8924 = 312.34 ≈ 312.0
INSERT INTO calculation_parameters (station_id, device_id, metric_key, param_name, param_value, param_type)
SELECT
  1 AS station_id,
  device_id,
  'pump_shaft_power' AS metric_key,
  'max_shaft_power' AS param_name,
  '312.0' AS param_value,
  'float' AS param_type
FROM generate_series(1, 6) AS device_id;

-- ============================================================================
-- 10. main_pipeline_inlet_pressure 参数
-- ============================================================================

-- min_level, max_level, min_pressure, max_pressure, max_deviation, max_change_rate（设备7）
INSERT INTO calculation_parameters (station_id, device_id, metric_key, param_name, param_value, param_type)
VALUES
  (1, 7, 'main_pipeline_inlet_pressure', 'min_level', '0.0', 'float'),
  (1, 7, 'main_pipeline_inlet_pressure', 'max_level', '10.0', 'float'),
  (1, 7, 'main_pipeline_inlet_pressure', 'min_pressure', '0.05', 'float'),
  (1, 7, 'main_pipeline_inlet_pressure', 'max_pressure', '1.0', 'float'),
  (1, 7, 'main_pipeline_inlet_pressure', 'max_deviation', '0.20', 'float'),
  (1, 7, 'main_pipeline_inlet_pressure', 'max_change_rate', '0.05', 'float');

-- ============================================================================
-- 验证参数已正确插入
-- ============================================================================

-- 统计每个指标的参数数量
SELECT
    metric_key,
    COUNT(*) AS param_count,
    COUNT(DISTINCT device_id) AS device_count
FROM calculation_parameters
WHERE station_id = 1
GROUP BY metric_key
ORDER BY metric_key;

-- 查看所有参数
SELECT
    metric_key,
    device_id,
    param_name,
    param_value,
    param_type
FROM calculation_parameters
WHERE station_id = 1
ORDER BY metric_key, device_id, param_name;

