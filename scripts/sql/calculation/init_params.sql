-- =====================================================
-- 缺失指标计算功能 - 初始化计算参数表
-- =====================================================
-- 创建时间: 2025-09-30
-- 用途: 初始化calculation_parameters表，录入默认参数
-- 参数列表:
--   pump_flow_rate_method_a: alpha, beta, f_thr, p_thr (4个)
--   pump_head: rho, g, b_H (3个)
-- 总计: 7个参数
-- 注意: device_id=NULL 表示全局默认参数，适用于所有设备
-- =====================================================

-- =====================================================
-- pump_flow_rate 方案A - 功率×频率分摊参数
-- =====================================================

-- 参数: alpha - 功率权重指数
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
) VALUES (
    NULL, NULL, 'pump_flow_rate', 'pump_flow_rate_method_a', 'alpha', 1.0, 'float', true
) ON CONFLICT (device_id, metric_key, method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    is_optimizable = EXCLUDED.is_optimizable,
    updated_at = NOW();

-- 参数: beta - 频率权重指数
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
) VALUES (
    NULL, NULL, 'pump_flow_rate', 'pump_flow_rate_method_a', 'beta', 1.0, 'float', true
) ON CONFLICT (device_id, metric_key, method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    is_optimizable = EXCLUDED.is_optimizable,
    updated_at = NOW();

-- 参数: f_thr - 频率阈值（Hz）
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
) VALUES (
    NULL, NULL, 'pump_flow_rate', 'pump_flow_rate_method_a', 'f_thr', 3.0, 'float', true
) ON CONFLICT (device_id, metric_key, method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    is_optimizable = EXCLUDED.is_optimizable,
    updated_at = NOW();

-- 参数: p_thr - 功率阈值（kW）
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
) VALUES (
    NULL, NULL, 'pump_flow_rate', 'pump_flow_rate_method_a', 'p_thr', 0.5, 'float', true
) ON CONFLICT (device_id, metric_key, method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    is_optimizable = EXCLUDED.is_optimizable,
    updated_at = NOW();

-- =====================================================
-- pump_head - 泵扬程参数
-- =====================================================

-- 参数: rho - 水密度（kg/m³）
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
) VALUES (
    NULL, NULL, 'pump_head', 'pump_head_method_main', 'rho', 1000.0, 'float', false
) ON CONFLICT (device_id, metric_key, method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    is_optimizable = EXCLUDED.is_optimizable,
    updated_at = NOW();

-- 参数: g - 重力加速度（m/s²）
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
) VALUES (
    NULL, NULL, 'pump_head', 'pump_head_method_main', 'g', 9.80665, 'float', false
) ON CONFLICT (device_id, metric_key, method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    is_optimizable = EXCLUDED.is_optimizable,
    updated_at = NOW();

-- 参数: b_H - 扬程偏置项（m）
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
) VALUES (
    NULL, NULL, 'pump_head', 'pump_head_method_main', 'b_H', 0.0, 'float', true
) ON CONFLICT (device_id, metric_key, method_id, param_name) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    param_type = EXCLUDED.param_type,
    is_optimizable = EXCLUDED.is_optimizable,
    updated_at = NOW();

-- =====================================================
-- 验证查询
-- =====================================================
-- SELECT COUNT(*) FROM calculation_parameters WHERE device_id IS NULL;
-- 预期结果: 7
--
-- SELECT metric_key, method_id, param_name, param_value, is_optimizable
-- FROM calculation_parameters
-- WHERE device_id IS NULL
-- ORDER BY metric_key, method_id, param_name;
-- =====================================================

