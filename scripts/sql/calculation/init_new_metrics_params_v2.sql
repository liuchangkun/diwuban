-- =====================================================
-- 缺失指标计算功能 - 初始化新增指标的方法参数
-- =====================================================
-- 创建时间: 2025-10-05
-- 用途: 初始化calculation_parameters表，录入新增方法的参数配置
-- 注意: station_id=NULL, device_id=NULL 表示全局默认参数，适用于所有设备
-- =====================================================

-- =====================================================
-- pump_speed - 泵转速方法参数
-- =====================================================

-- 方法A：相对转速法 - 参考频率
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
) VALUES (
    NULL, NULL, 'pump_speed', 'pump_speed_method_a', 'f_ref', 50.0, 'float', false
) ON CONFLICT (device_id, metric_key, method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    is_optimizable = EXCLUDED.is_optimizable,
    updated_at = NOW();

-- 方法B：绝对转速法 - 极对数
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
) VALUES (
    NULL, NULL, 'pump_speed', 'pump_speed_method_b', 'pole_pairs', 2, 'int', false
) ON CONFLICT (device_id, metric_key, method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    is_optimizable = EXCLUDED.is_optimizable,
    updated_at = NOW();

-- 方法B：绝对转速法 - 滑差
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
) VALUES (
    NULL, NULL, 'pump_speed', 'pump_speed_method_b', 'slip', 0.02, 'float', true
) ON CONFLICT (device_id, metric_key, method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    is_optimizable = EXCLUDED.is_optimizable,
    updated_at = NOW();

-- 方法C：标定关系法 - 斜率
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
) VALUES (
    NULL, NULL, 'pump_speed', 'pump_speed_method_c', 'calibration_a', 30.0, 'float', true
) ON CONFLICT (device_id, metric_key, method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    is_optimizable = EXCLUDED.is_optimizable,
    updated_at = NOW();

-- 方法C：标定关系法 - 截距
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
) VALUES (
    NULL, NULL, 'pump_speed', 'pump_speed_method_c', 'calibration_b', 0.0, 'float', true
) ON CONFLICT (device_id, metric_key, method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    is_optimizable = EXCLUDED.is_optimizable,
    updated_at = NOW();

-- =====================================================
-- pump_torque - 泵扭矩方法参数
-- =====================================================

-- 方法A：水力功率与转速法 - 水密度
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
) VALUES (
    NULL, NULL, 'pump_torque', 'pump_torque_method_a', 'rho', 1000.0, 'float', false
) ON CONFLICT (device_id, metric_key, method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    is_optimizable = EXCLUDED.is_optimizable,
    updated_at = NOW();

-- 方法A：水力功率与转速法 - 重力加速度
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
) VALUES (
    NULL, NULL, 'pump_torque', 'pump_torque_method_a', 'g', 9.80665, 'float', false
) ON CONFLICT (device_id, metric_key, method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    is_optimizable = EXCLUDED.is_optimizable,
    updated_at = NOW();

-- 方法B：电功率与频率法 - 极对数
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
) VALUES (
    NULL, NULL, 'pump_torque', 'pump_torque_method_b', 'pole_pairs', 2, 'int', false
) ON CONFLICT (device_id, metric_key, method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    is_optimizable = EXCLUDED.is_optimizable,
    updated_at = NOW();

-- 方法B：电功率与频率法 - 滑差
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
) VALUES (
    NULL, NULL, 'pump_torque', 'pump_torque_method_b', 'slip', 0.02, 'float', true
) ON CONFLICT (device_id, metric_key, method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    is_optimizable = EXCLUDED.is_optimizable,
    updated_at = NOW();

-- =====================================================
-- main_pipeline_outlet_pressure - 总管出口压力方法参数
-- =====================================================

-- 方法B：从泵进口压力和扬程推算 - 水密度
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
) VALUES (
    NULL, NULL, 'main_pipeline_outlet_pressure', 'main_pipeline_outlet_pressure_method_b', 'rho', 1000.0, 'float', false
) ON CONFLICT (device_id, metric_key, method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    is_optimizable = EXCLUDED.is_optimizable,
    updated_at = NOW();

-- 方法B：从泵进口压力和扬程推算 - 重力加速度
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
) VALUES (
    NULL, NULL, 'main_pipeline_outlet_pressure', 'main_pipeline_outlet_pressure_method_b', 'g', 9.80665, 'float', false
) ON CONFLICT (device_id, metric_key, method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    is_optimizable = EXCLUDED.is_optimizable,
    updated_at = NOW();

-- =====================================================
-- main_pipeline_inlet_pressure - 总管进口压力方法参数
-- =====================================================

-- 方法B：从水池液位推算 - 大气压
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
) VALUES (
    NULL, NULL, 'main_pipeline_inlet_pressure', 'main_pipeline_inlet_pressure_method_b', 'P_atm', 0.101325, 'float', false
) ON CONFLICT (device_id, metric_key, method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    is_optimizable = EXCLUDED.is_optimizable,
    updated_at = NOW();

-- 方法B：从水池液位推算 - 水密度
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
) VALUES (
    NULL, NULL, 'main_pipeline_inlet_pressure', 'main_pipeline_inlet_pressure_method_b', 'rho', 1000.0, 'float', false
) ON CONFLICT (device_id, metric_key, method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    is_optimizable = EXCLUDED.is_optimizable,
    updated_at = NOW();

-- 方法B：从水池液位推算 - 重力加速度
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
) VALUES (
    NULL, NULL, 'main_pipeline_inlet_pressure', 'main_pipeline_inlet_pressure_method_b', 'g', 9.80665, 'float', false
) ON CONFLICT (device_id, metric_key, method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    is_optimizable = EXCLUDED.is_optimizable,
    updated_at = NOW();

-- =====================================================
-- pump_cumulative_flow - 泵累计流量方法参数
-- =====================================================

-- 方法A：从瞬时流量积分 - 初始值
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
) VALUES (
    NULL, NULL, 'pump_cumulative_flow', 'pump_cumulative_flow_method_a', 'initial_value', 0.0, 'float', false
) ON CONFLICT (device_id, metric_key, method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    is_optimizable = EXCLUDED.is_optimizable,
    updated_at = NOW();

-- 方法A：从瞬时流量积分 - 时间间隔
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
) VALUES (
    NULL, NULL, 'pump_cumulative_flow', 'pump_cumulative_flow_method_a', 'time_interval', 1.0, 'float', false
) ON CONFLICT (device_id, metric_key, method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    is_optimizable = EXCLUDED.is_optimizable,
    updated_at = NOW();

-- =====================================================
-- 完成提示
-- =====================================================
SELECT '新增指标方法参数初始化完成！' AS message,
       COUNT(*) AS total_params
FROM calculation_parameters
WHERE method_id IN (
    'pump_speed_method_a', 'pump_speed_method_b', 'pump_speed_method_c',
    'pump_torque_method_a', 'pump_torque_method_b',
    'main_pipeline_outlet_pressure_method_b',
    'main_pipeline_inlet_pressure_method_b',
    'pump_cumulative_flow_method_a'
);

