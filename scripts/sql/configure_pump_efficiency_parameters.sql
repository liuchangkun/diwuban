-- 配置 pump_efficiency 计算参数
-- 创建时间: 2025-11-17

-- 1. Delete existing pump_efficiency parameters (except EFF_SIMPLE_V1)
DELETE FROM calculation_parameters
WHERE metric_key = 'pump_efficiency'
  AND method_id NOT IN ('EFF_SIMPLE_V1');

-- 2. Insert physical constants (global level) - using existing method_id
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
) VALUES
(NULL, NULL, 'pump_efficiency', 'EFF_SIMPLE_V1', 'rho', 1000.0, 'float', FALSE),
(NULL, NULL, 'pump_efficiency', 'EFF_SIMPLE_V1', 'g', 9.81, 'float', FALSE),
(NULL, NULL, 'pump_efficiency', 'EFF_SIMPLE_V1', 'eta_min', 0.30, 'float', FALSE),
(NULL, NULL, 'pump_efficiency', 'EFF_SIMPLE_V1', 'eta_max', 0.95, 'float', FALSE);

-- 4. Verify configuration
SELECT
    station_id,
    device_id,
    metric_key,
    method_id,
    param_name,
    param_value,
    param_type,
    is_optimizable
FROM calculation_parameters
WHERE metric_key = 'pump_efficiency'
ORDER BY method_id, param_name;

