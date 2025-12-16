-- 更新pump_speed_method_a的参数配置
-- 添加n_ref参数（额定转速）

-- 为pump_speed_method_a添加n_ref参数（全局默认值）
INSERT INTO calculation_parameters (
    station_id,
    device_id,
    metric_key,
    method_id,
    param_name,
    param_value,
    param_type,
    is_optimizable,
    updated_by
) VALUES (
    NULL,  -- 全局参数
    NULL,  -- 全局参数
    'pump_speed',
    'pump_speed_method_a',
    'n_ref',
    1500.0,  -- 默认额定转速1500 rpm（对应50Hz，4极电机）
    'float',
    true,  -- 可优化
    'system'
) ON CONFLICT (device_id, metric_key, method_id, param_name) 
DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    is_optimizable = EXCLUDED.is_optimizable,
    updated_at = NOW(),
    updated_by = EXCLUDED.updated_by;

-- 验证更新结果
SELECT 
    method_id,
    param_name,
    param_value,
    param_type,
    is_optimizable
FROM calculation_parameters
WHERE method_id = 'pump_speed_method_a'
ORDER BY param_name;

