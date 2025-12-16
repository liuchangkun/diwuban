-- =====================================================
-- 缺失指标计算功能 - 初始化新增指标的方法参数
-- =====================================================
-- 创建时间: 2025-10-05
-- 用途: 初始化calculation_parameters表，录入新增方法的参数配置
-- =====================================================

-- =====================================================
-- pump_speed - 泵转速方法参数
-- =====================================================

-- 方法A：相对转速法 - 参考频率
INSERT INTO calculation_parameters (method_id, param_name, param_value, param_type, description)
VALUES ('pump_speed_method_a', 'f_ref', '50.0', 'float', '参考频率（Hz），默认50Hz')
ON CONFLICT (method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    description = EXCLUDED.description,
    updated_at = NOW();

-- 方法B：绝对转速法 - 极对数
INSERT INTO calculation_parameters (method_id, param_name, param_value, param_type, description)
VALUES ('pump_speed_method_b', 'pole_pairs', '2', 'int', '极对数，默认2（4极电机）')
ON CONFLICT (method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    description = EXCLUDED.description,
    updated_at = NOW();

-- 方法B：绝对转速法 - 滑差
INSERT INTO calculation_parameters (method_id, param_name, param_value, param_type, description)
VALUES ('pump_speed_method_b', 'slip', '0.02', 'float', '滑差，默认0.02（2%）')
ON CONFLICT (method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    description = EXCLUDED.description,
    updated_at = NOW();

-- 方法C：标定关系法 - 斜率
INSERT INTO calculation_parameters (method_id, param_name, param_value, param_type, description)
VALUES ('pump_speed_method_c', 'calibration_a', '30.0', 'float', '标定斜率，默认30（对应4极电机）')
ON CONFLICT (method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    description = EXCLUDED.description,
    updated_at = NOW();

-- 方法C：标定关系法 - 截距
INSERT INTO calculation_parameters (method_id, param_name, param_value, param_type, description)
VALUES ('pump_speed_method_c', 'calibration_b', '0.0', 'float', '标定截距，默认0')
ON CONFLICT (method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    description = EXCLUDED.description,
    updated_at = NOW();

-- =====================================================
-- pump_torque - 泵扭矩方法参数
-- =====================================================

-- 方法A：水力功率与转速法 - 水密度
INSERT INTO calculation_parameters (method_id, param_name, param_value, param_type, description)
VALUES ('pump_torque_method_a', 'rho', '1000.0', 'float', '水密度（kg/m³），默认1000')
ON CONFLICT (method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    description = EXCLUDED.description,
    updated_at = NOW();

-- 方法A：水力功率与转速法 - 重力加速度
INSERT INTO calculation_parameters (method_id, param_name, param_value, param_type, description)
VALUES ('pump_torque_method_a', 'g', '9.80665', 'float', '重力加速度（m/s²），默认9.80665')
ON CONFLICT (method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    description = EXCLUDED.description,
    updated_at = NOW();

-- 方法B：电功率与频率法 - 极对数
INSERT INTO calculation_parameters (method_id, param_name, param_value, param_type, description)
VALUES ('pump_torque_method_b', 'pole_pairs', '2', 'int', '极对数，默认2（4极电机）')
ON CONFLICT (method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    description = EXCLUDED.description,
    updated_at = NOW();

-- 方法B：电功率与频率法 - 滑差
INSERT INTO calculation_parameters (method_id, param_name, param_value, param_type, description)
VALUES ('pump_torque_method_b', 'slip', '0.02', 'float', '滑差，默认0.02（2%）')
ON CONFLICT (method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    description = EXCLUDED.description,
    updated_at = NOW();

-- =====================================================
-- main_pipeline_outlet_pressure - 总管出口压力方法参数
-- =====================================================

-- 方法B：从泵进口压力和扬程推算 - 水密度
INSERT INTO calculation_parameters (method_id, param_name, param_value, param_type, description)
VALUES ('main_pipeline_outlet_pressure_method_b', 'rho', '1000.0', 'float', '水密度（kg/m³），默认1000')
ON CONFLICT (method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    description = EXCLUDED.description,
    updated_at = NOW();

-- 方法B：从泵进口压力和扬程推算 - 重力加速度
INSERT INTO calculation_parameters (method_id, param_name, param_value, param_type, description)
VALUES ('main_pipeline_outlet_pressure_method_b', 'g', '9.80665', 'float', '重力加速度（m/s²），默认9.80665')
ON CONFLICT (method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    description = EXCLUDED.description,
    updated_at = NOW();

-- =====================================================
-- main_pipeline_inlet_pressure - 总管进口压力方法参数
-- =====================================================

-- 方法B：从水池液位推算 - 大气压
INSERT INTO calculation_parameters (method_id, param_name, param_value, param_type, description)
VALUES ('main_pipeline_inlet_pressure_method_b', 'P_atm', '0.101325', 'float', '大气压（MPa），默认0.101325')
ON CONFLICT (method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    description = EXCLUDED.description,
    updated_at = NOW();

-- 方法B：从水池液位推算 - 水密度
INSERT INTO calculation_parameters (method_id, param_name, param_value, param_type, description)
VALUES ('main_pipeline_inlet_pressure_method_b', 'rho', '1000.0', 'float', '水密度（kg/m³），默认1000')
ON CONFLICT (method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    description = EXCLUDED.description,
    updated_at = NOW();

-- 方法B：从水池液位推算 - 重力加速度
INSERT INTO calculation_parameters (method_id, param_name, param_value, param_type, description)
VALUES ('main_pipeline_inlet_pressure_method_b', 'g', '9.80665', 'float', '重力加速度（m/s²），默认9.80665')
ON CONFLICT (method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    description = EXCLUDED.description,
    updated_at = NOW();

-- =====================================================
-- pump_cumulative_flow - 泵累计流量方法参数
-- =====================================================

-- 方法A：从瞬时流量积分 - 初始值
INSERT INTO calculation_parameters (method_id, param_name, param_value, param_type, description)
VALUES ('pump_cumulative_flow_method_a', 'initial_value', '0.0', 'float', '初始累计值（m³），默认0')
ON CONFLICT (method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    description = EXCLUDED.description,
    updated_at = NOW();

-- 方法A：从瞬时流量积分 - 时间间隔
INSERT INTO calculation_parameters (method_id, param_name, param_value, param_type, description)
VALUES ('pump_cumulative_flow_method_a', 'time_interval', '1.0', 'float', '时间间隔（秒），默认1秒')
ON CONFLICT (method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    description = EXCLUDED.description,
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

