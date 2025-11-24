-- =====================================================
-- calculation_parameters 表参数填充SQL
-- =====================================================
-- 创建时间: 2025-11-22
-- 用途: 为5个新增指标填充计算参数
-- 指标: pump_speed, main_pipeline_inlet_pressure, pump_shaft_power, 
--       pump_hydraulic_power, pump_torque
-- =====================================================

-- =====================================================
-- 1. pump_speed (泵转速)
-- =====================================================

-- Method A: 频率比例法
INSERT INTO calculation_parameters (metric_key, method_id, param_key, param_value, description)
VALUES
('pump_speed', 'method_a', 'f_ref', '50.0', '额定频率(Hz)'),
('pump_speed', 'method_a', 'n_ref', '1500.0', '额定转速(rpm)'),
('pump_speed', 'method_a', 'priority', '100', '方法优先级');

-- Method B: 极对数法
INSERT INTO calculation_parameters (metric_key, method_id, param_key, param_value, description)
VALUES
('pump_speed', 'method_b', 'priority', '90', '方法优先级');
-- 注意: pole_pairs和slip从device_rated_params表获取

-- Method C: 校准系数法
INSERT INTO calculation_parameters (metric_key, method_id, param_key, param_value, description)
VALUES
('pump_speed', 'method_c', 'calibration_a', '30.0', '校准系数a（默认值，需现场校准）'),
('pump_speed', 'method_c', 'calibration_b', '0.0', '校准系数b（默认值，需现场校准）'),
('pump_speed', 'method_c', 'calibration_quality', 'low', '校准质量(low/medium/high)'),
('pump_speed', 'method_c', 'priority', '80', '方法优先级');

-- 验证阈值
INSERT INTO calculation_parameters (metric_key, method_id, param_key, param_value, description)
VALUES
('pump_speed', 'validation', 'min_speed', '0.0', '最小转速(rpm)'),
('pump_speed', 'validation', 'max_speed', '3000.0', '最大转速(rpm)'),
('pump_speed', 'validation', 'max_speed_change_rate', '100.0', '最大转速变化率(rpm/s)');

-- =====================================================
-- 2. main_pipeline_inlet_pressure (总管进口压力)
-- =====================================================

-- Method B: 静压法
INSERT INTO calculation_parameters (metric_key, method_id, param_key, param_value, description)
VALUES
('main_pipeline_inlet_pressure', 'method_b', 'P_atm', '0.101325', '大气压(MPa)'),
('main_pipeline_inlet_pressure', 'method_b', 'rho', '1000.0', '水密度(kg/m³)'),
('main_pipeline_inlet_pressure', 'method_b', 'g', '9.80665', '重力加速度(m/s²)'),
('main_pipeline_inlet_pressure', 'method_b', 'priority', '100', '方法优先级');

-- PIN_COEF_V1: 等效系数法
INSERT INTO calculation_parameters (metric_key, method_id, param_key, param_value, description)
VALUES
('main_pipeline_inlet_pressure', 'PIN_COEF_V1', 'b0', '101325.0', '常数项(Pa)'),
('main_pipeline_inlet_pressure', 'PIN_COEF_V1', 'b1', '9806.65', '一次项系数（默认值，需现场校准）'),
('main_pipeline_inlet_pressure', 'PIN_COEF_V1', 'b2', '0.0', '二次项系数（默认值，需现场校准）'),
('main_pipeline_inlet_pressure', 'PIN_COEF_V1', 'b3', '0.0', '三次项系数（默认值，需现场校准）'),
('main_pipeline_inlet_pressure', 'PIN_COEF_V1', 'calibration_quality', 'low', '校准质量(low/medium/high)'),
('main_pipeline_inlet_pressure', 'PIN_COEF_V1', 'priority', '90', '方法优先级');

-- 验证阈值
INSERT INTO calculation_parameters (metric_key, method_id, param_key, param_value, description)
VALUES
('main_pipeline_inlet_pressure', 'validation', 'min_pressure', '-0.1', '最小压力(MPa)'),
('main_pipeline_inlet_pressure', 'validation', 'max_pressure', '1.0', '最大压力(MPa)'),
('main_pipeline_inlet_pressure', 'validation', 'max_pressure_change_rate', '0.05', '最大压力变化率(MPa/s)');

-- =====================================================
-- 3. pump_shaft_power (泵轴功率)
-- =====================================================

-- Method A: 电机效率法
INSERT INTO calculation_parameters (metric_key, method_id, param_key, param_value, description)
VALUES
('pump_shaft_power', 'method_a', 'priority', '100', '方法优先级');
-- 注意: eta_motor和eta_vfd从device_rated_params表获取

-- 验证阈值
INSERT INTO calculation_parameters (metric_key, method_id, param_key, param_value, description)
VALUES
('pump_shaft_power', 'validation', 'min_shaft_power', '0.0', '最小轴功率(kW)'),
('pump_shaft_power', 'validation', 'max_shaft_power', '10000.0', '最大轴功率(kW)'),
('pump_shaft_power', 'validation', 'min_total_efficiency', '0.7', '最小总效率(电机×变频器)'),
('pump_shaft_power', 'validation', 'max_total_efficiency', '1.0', '最大总效率(电机×变频器)');

-- =====================================================
-- 4. pump_hydraulic_power (泵水力功率)
-- =====================================================

-- Method A: 流量-扬程法
INSERT INTO calculation_parameters (metric_key, method_id, param_key, param_value, description)
VALUES
('pump_hydraulic_power', 'method_a', 'rho', '1000.0', '水密度(kg/m³)'),
('pump_hydraulic_power', 'method_a', 'g', '9.81', '重力加速度(m/s²)'),
('pump_hydraulic_power', 'method_a', 'priority', '100', '方法优先级');

-- 验证阈值
INSERT INTO calculation_parameters (metric_key, method_id, param_key, param_value, description)
VALUES
('pump_hydraulic_power', 'validation', 'min_hydraulic_power', '0.0', '最小水力功率(kW)'),
('pump_hydraulic_power', 'validation', 'max_hydraulic_power', '10000.0', '最大水力功率(kW)'),
('pump_hydraulic_power', 'validation', 'max_pump_efficiency', '0.95', '最大泵效率（水力功率/轴功率）');

-- =====================================================
-- 5. pump_torque (泵扭矩)
-- =====================================================

-- Method A: 功率-转速法
INSERT INTO calculation_parameters (metric_key, method_id, param_key, param_value, description)
VALUES
('pump_torque', 'method_a', 'priority', '100', '方法优先级');

-- Method B: 水力功率法
INSERT INTO calculation_parameters (metric_key, method_id, param_key, param_value, description)
VALUES
('pump_torque', 'method_b', 'rho', '1000.0', '水密度(kg/m³)'),
('pump_torque', 'method_b', 'g', '9.80665', '重力加速度(m/s²)'),
('pump_torque', 'method_b', 'priority', '90', '方法优先级');

-- 验证阈值
INSERT INTO calculation_parameters (metric_key, method_id, param_key, param_value, description)
VALUES
('pump_torque', 'validation', 'min_torque', '0.0', '最小扭矩(N·m)'),
('pump_torque', 'validation', 'max_torque', '10000.0', '最大扭矩(N·m)'),
('pump_torque', 'validation', 'max_torque_change_rate', '1000.0', '最大扭矩变化率(N·m/s)'),
('pump_torque', 'validation', 'max_method_diff_ratio', '0.1', '双方法最大差异比例（10%）');

-- =====================================================
-- 验证插入结果
-- =====================================================
SELECT 
    metric_key,
    method_id,
    COUNT(*) as param_count,
    STRING_AGG(param_key, ', ' ORDER BY param_key) as params
FROM calculation_parameters
WHERE metric_key IN (
    'pump_speed', 
    'main_pipeline_inlet_pressure', 
    'pump_shaft_power',
    'pump_hydraulic_power',
    'pump_torque'
)
GROUP BY metric_key, method_id
ORDER BY metric_key, method_id;

-- =====================================================
-- 参数说明
-- =====================================================
-- priority: 方法优先级（100最高，数字越大优先级越高）
-- calibration_quality: 校准质量（low/medium/high，影响方法选择）
-- 物理常数: P_atm, rho, g（全局通用）
-- 验证阈值: min_*, max_*（用于数据质量检查）

