-- 添加 pump_speed 缺失的参数
-- 缺失参数: min_speed, max_speed

-- 1. 删除可能存在的旧记录
DELETE FROM calculation_parameters
WHERE metric_key = 'pump_speed'
  AND param_name IN ('min_speed', 'max_speed');

-- 2. 添加 min_speed (全局参数)
-- 泵转速最小值：0 rpm（泵停止时）
INSERT INTO calculation_parameters (station_id, device_id, metric_key, param_name, param_value, param_type)
VALUES (1, NULL, 'pump_speed', 'min_speed', 0.0::numeric, 'float');

-- 3. 添加 max_speed (全局参数)
-- 泵转速最大值：3000 rpm（根据常见离心泵额定转速）
INSERT INTO calculation_parameters (station_id, device_id, metric_key, param_name, param_value, param_type)
VALUES (1, NULL, 'pump_speed', 'max_speed', 3000.0::numeric, 'float');

-- 验证插入结果
SELECT 
    metric_key,
    param_name,
    param_value,
    param_type
FROM calculation_parameters
WHERE metric_key = 'pump_speed'
  AND param_name IN ('min_speed', 'max_speed')
ORDER BY param_name;

