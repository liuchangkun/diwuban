-- ============================================
-- 自适应SQL脚本：calculation_parameters
-- ============================================
-- 文件：scripts/sql/adaptive/03_calculation_parameters.sql
-- 用途：生成 calculation_parameters（集中处理所有类型）
-- 依赖：dim_stations, dim_devices, dim_metric_config, calculation_method_registry
-- 特性：自适应关联，支持全局默认参数、站点级参数、设备级参数
-- ============================================

BEGIN;

-- ============================================
-- calculation_parameters（计算参数）
-- ============================================

-- 清空表（完全重建）
TRUNCATE TABLE calculation_parameters CASCADE;

-- ============================================
-- 类型0：全局物理常数和高级方法参数（零硬编码）
-- ============================================

-- HEAD_COEF_V1 方法的物理常数和参数
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value,
    param_type, is_optimizable, param_min, param_max, updated_by, confidence_score
)
SELECT
    NULL, NULL, 'pump_head', 'HEAD_COEF_V1',
    unnest(ARRAY['rho', 'g', 'a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'H_min', 'H_max']),
    unnest(ARRAY[1000.0, 9.80665, 50.0, -0.01, -0.0001, 0.0, 0.0, 0.0, 0.0, 100.0]),
    'float',
    unnest(ARRAY[false, false, true, true, true, true, true, true, false, false]),
    unnest(ARRAY[NULL, NULL, 0.0, -1.0, -0.01, -10.0, -10.0, -1.0, NULL, NULL]),
    unnest(ARRAY[NULL, NULL, 100.0, 1.0, 0.01, 10.0, 10.0, 1.0, NULL, NULL]),
    'adaptive_sql',
    unnest(ARRAY[1.0, 1.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 1.0, 1.0])
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_head';

-- PIN_COEF_V1 方法的物理常数和参数
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value,
    param_type, is_optimizable, param_min, param_max, updated_by, confidence_score
)
SELECT
    NULL, NULL, 'main_pipeline_inlet_pressure', 'PIN_COEF_V1',
    unnest(ARRAY['rho', 'g', 'b0', 'b1', 'b2', 'b3', 'P_in_min', 'P_in_max']),
    unnest(ARRAY[1000.0, 9.80665, 101325.0, 1.0, 0.0, 0.0, -0.1, 1.0]),
    'float',
    unnest(ARRAY[false, false, true, true, true, true, false, false]),
    unnest(ARRAY[NULL, NULL, 50000.0, 0.5, 0.0, 0.0, NULL, NULL]),
    unnest(ARRAY[NULL, NULL, 200000.0, 1.5, 100.0, 1000.0, NULL, NULL]),
    'adaptive_sql',
    unnest(ARRAY[1.0, 1.0, 0.5, 0.5, 0.5, 0.5, 1.0, 1.0])
FROM dim_metric_config mc
WHERE mc.metric_key = 'main_pipeline_inlet_pressure';

-- pump_inlet_pressure 方法B - 从水池液位推算参数
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value,
    param_type, is_optimizable, param_min, param_max, updated_by, confidence_score
)
SELECT
    NULL, NULL, 'pump_inlet_pressure', 'pump_inlet_pressure_method_b',
    unnest(ARRAY['P_atm', 'rho', 'g']),
    unnest(ARRAY[0.101325, 1000.0, 9.80665]),
    'float',
    unnest(ARRAY[false, false, false]),
    unnest(ARRAY[NULL::numeric, NULL::numeric, NULL::numeric]),
    unnest(ARRAY[NULL::numeric, NULL::numeric, NULL::numeric]),
    'adaptive_sql',
    unnest(ARRAY[1.0, 1.0, 1.0])
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_inlet_pressure';

-- main_pipeline_inlet_pressure 方法B - 从水池液位推算参数
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value,
    param_type, is_optimizable, param_min, param_max, updated_by, confidence_score
)
SELECT
    NULL, NULL, 'main_pipeline_inlet_pressure', 'main_pipeline_inlet_pressure_method_b',
    unnest(ARRAY['P_atm', 'rho', 'g']),
    unnest(ARRAY[0.101325, 1000.0, 9.80665]),
    'float',
    unnest(ARRAY[false, false, false]),
    unnest(ARRAY[NULL::numeric, NULL::numeric, NULL::numeric]),
    unnest(ARRAY[NULL::numeric, NULL::numeric, NULL::numeric]),
    'adaptive_sql',
    unnest(ARRAY[1.0, 1.0, 1.0])
FROM dim_metric_config mc
WHERE mc.metric_key = 'main_pipeline_inlet_pressure';

-- pump_outlet_pressure 方法C - 由进口压力与扬程回推参数
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value,
    param_type, is_optimizable, param_min, param_max, updated_by, confidence_score
)
SELECT
    NULL, NULL, 'pump_outlet_pressure', 'pump_outlet_pressure_method_c',
    unnest(ARRAY['rho', 'g']),
    unnest(ARRAY[1000.0, 9.80665]),
    'float',
    unnest(ARRAY[false, false]),
    unnest(ARRAY[NULL::numeric, NULL::numeric]),
    unnest(ARRAY[NULL::numeric, NULL::numeric]),
    'adaptive_sql',
    unnest(ARRAY[1.0, 1.0])
FROM dim_metric_config mc
WHERE mc.metric_key = 'pump_outlet_pressure';

-- main_pipeline_outlet_pressure 方法B - 从泵进口压力和扬程推算参数
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value,
    param_type, is_optimizable, param_min, param_max, updated_by, confidence_score
)
SELECT
    NULL, NULL, 'main_pipeline_outlet_pressure', 'main_pipeline_outlet_pressure_method_b',
    unnest(ARRAY['rho', 'g']),
    unnest(ARRAY[1000.0, 9.80665]),
    'float',
    unnest(ARRAY[false, false]),
    unnest(ARRAY[NULL::numeric, NULL::numeric]),
    unnest(ARRAY[NULL::numeric, NULL::numeric]),
    'adaptive_sql',
    unnest(ARRAY[1.0, 1.0])
FROM dim_metric_config mc
WHERE mc.metric_key = 'main_pipeline_outlet_pressure';

-- ============================================
-- 类型1：全局默认参数（station_id = NULL, device_id = NULL）
-- ============================================

-- pump_flow_rate 方案A - 功率×频率分摊参数
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
)
SELECT
    NULL,
    NULL,
    mc.metric_key,
    cmr.method_id,
    unnest(ARRAY['alpha', 'beta', 'f_thr', 'p_thr']),
    unnest(ARRAY[1.0, 1.0, 3.0, 0.5]),
    'float',
    TRUE
FROM dim_metric_config mc
JOIN calculation_method_registry cmr ON mc.metric_key = cmr.metric_key
WHERE mc.metric_key = 'pump_flow_rate' AND cmr.method_code = 'A';

-- pump_head - 泵扬程参数（MAIN方法）
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
)
SELECT
    NULL,
    NULL,
    mc.metric_key,
    cmr.method_id,
    unnest(ARRAY['rho', 'g', 'P_atm', 'b_H']),
    unnest(ARRAY[1000.0, 9.80665, 0.101325, 0.0]),
    'float',
    unnest(ARRAY[FALSE, FALSE, FALSE, TRUE])
FROM dim_metric_config mc
JOIN calculation_method_registry cmr ON mc.metric_key = cmr.metric_key
WHERE mc.metric_key = 'pump_head' AND cmr.method_code = 'MAIN';

-- pump_speed 方案A - 频率比例法参数
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
)
SELECT
    NULL,
    NULL,
    mc.metric_key,
    cmr.method_id,
    unnest(ARRAY['f_ref', 'n_ref']),
    unnest(ARRAY[50.0, 1500.0]),
    'float',
    FALSE
FROM dim_metric_config mc
JOIN calculation_method_registry cmr ON mc.metric_key = cmr.metric_key
WHERE mc.metric_key = 'pump_speed' AND cmr.method_code = 'A';

-- pump_speed 方案B - 绝对转速法（电机学）参数
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
)
SELECT
    NULL,
    NULL,
    mc.metric_key,
    cmr.method_id,
    unnest(ARRAY['slip', 'pole_pairs']),
    unnest(ARRAY[0.02, 2.0]),
    'float',
    unnest(ARRAY[TRUE, FALSE])
FROM dim_metric_config mc
JOIN calculation_method_registry cmr ON mc.metric_key = cmr.metric_key
WHERE mc.metric_key = 'pump_speed' AND cmr.method_code = 'B';

-- pump_speed 方案C - 标定关系法参数
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
)
SELECT
    NULL,
    NULL,
    mc.metric_key,
    cmr.method_id,
    unnest(ARRAY['calibration_a', 'calibration_b']),
    unnest(ARRAY[30.0, 0.0]),
    'float',
    TRUE
FROM dim_metric_config mc
JOIN calculation_method_registry cmr ON mc.metric_key = cmr.metric_key
WHERE mc.metric_key = 'pump_speed' AND cmr.method_code = 'C';

-- pump_efficiency - 简化效率估算参数
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
)
SELECT
    NULL,
    NULL,
    mc.metric_key,
    cmr.method_id,
    unnest(ARRAY['rho', 'g', 'eta_motor', 'eta_max']),
    unnest(ARRAY[1000.0, 9.80665, 0.92, 0.85]),
    'float',
    unnest(ARRAY[FALSE, FALSE, TRUE, TRUE])
FROM dim_metric_config mc
JOIN calculation_method_registry cmr ON mc.metric_key = cmr.metric_key
WHERE mc.metric_key = 'pump_efficiency' AND cmr.method_code = 'EFF_SIMPLE_V1';

-- pump_torque 方案A - 水力功率与转速法参数
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
)
SELECT
    NULL,
    NULL,
    mc.metric_key,
    cmr.method_id,
    unnest(ARRAY['rho', 'g']),
    unnest(ARRAY[1000.0, 9.80665]),
    'float',
    FALSE
FROM dim_metric_config mc
JOIN calculation_method_registry cmr ON mc.metric_key = cmr.metric_key
WHERE mc.metric_key = 'pump_torque' AND cmr.method_code = 'A';

-- pump_torque 方案B - 电功率与频率法参数
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
)
SELECT
    NULL,
    NULL,
    mc.metric_key,
    cmr.method_id,
    unnest(ARRAY['slip', 'pole_pairs']),
    unnest(ARRAY[0.02, 2.0]),
    'float',
    unnest(ARRAY[TRUE, FALSE])
FROM dim_metric_config mc
JOIN calculation_method_registry cmr ON mc.metric_key = cmr.metric_key
WHERE mc.metric_key = 'pump_torque' AND cmr.method_code = 'B';

-- ============================================
-- 类型2：站点级参数（station_id != NULL, device_id = NULL）
-- ============================================
-- 注意：当前项目中暂无站点级参数，此部分保留为示例

-- 示例：为特定站点设置 main_pipeline_flow_rate 的参数
-- INSERT INTO calculation_parameters (
--     station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
-- )
-- SELECT
--     s.id,
--     NULL,
--     mc.metric_key,
--     cmr.method_id,
--     'station_factor',
--     1.0,
--     'float',
--     TRUE
-- FROM dim_stations s
-- CROSS JOIN dim_metric_config mc
-- JOIN calculation_method_registry cmr ON mc.metric_key = cmr.metric_key
-- WHERE s.name = '二期供水泵房'
--   AND mc.metric_key = 'main_pipeline_flow_rate'
--   AND cmr.method_code = 'A';

-- ============================================
-- 类型3：设备级参数（device_id != NULL）
-- ============================================
-- 注意：当前项目中暂无设备级参数覆盖，此部分保留为示例

-- 示例：为特定设备设置 pump_flow_rate 方案A 的参数
-- INSERT INTO calculation_parameters (
--     station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
-- )
-- SELECT
--     d.station_id,
--     d.id,
--     mc.metric_key,
--     cmr.method_id,
--     'alpha',
--     1.2,
--     'float',
--     TRUE
-- FROM dim_devices d
-- JOIN dim_stations s ON d.station_id = s.id
-- CROSS JOIN dim_metric_config mc
-- JOIN calculation_method_registry cmr ON mc.metric_key = cmr.metric_key
-- WHERE s.name = '二期供水泵房'
--   AND d.name = '二期供水泵房1#泵'
--   AND mc.metric_key = 'pump_flow_rate'
--   AND cmr.method_code = 'A';

COMMIT;

