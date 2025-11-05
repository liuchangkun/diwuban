-- 目的：为6台泵补充设备级计算参数（8个方法×每个方法的参数）
-- 策略：复制全局参数作为设备级参数的初始值，后续可手动调整
-- 影响：calculation_parameters 表新增约150行设备级参数

BEGIN;

-- ============================================================================
-- 为设备1-6补充所有方法的设备级参数
-- ============================================================================

-- 方法1: EFF_SIMPLE_V1 (4个参数: rho, g, eta_motor, eta_max)
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable, updated_by
)
SELECT 
    1 as station_id,
    d.id as device_id,
    cp.metric_key,
    cp.method_id,
    cp.param_name,
    cp.param_value,
    cp.param_type,
    cp.is_optimizable,
    'migration:072:device_level' as updated_by
FROM dim_devices d
CROSS JOIN calculation_parameters cp
WHERE d.id BETWEEN 1 AND 6
  AND cp.method_id = 'EFF_SIMPLE_V1'
  AND cp.device_id IS NULL
  AND cp.station_id IS NULL
ON CONFLICT (device_id, metric_key, method_id, param_name)
DO NOTHING;

-- 方法2: pump_flow_rate_method_a (4个参数: alpha, beta, f_thr, p_thr)
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable, updated_by
)
SELECT 
    1 as station_id,
    d.id as device_id,
    cp.metric_key,
    cp.method_id,
    cp.param_name,
    cp.param_value,
    cp.param_type,
    cp.is_optimizable,
    'migration:072:device_level' as updated_by
FROM dim_devices d
CROSS JOIN calculation_parameters cp
WHERE d.id BETWEEN 1 AND 6
  AND cp.method_id = 'pump_flow_rate_method_a'
  AND cp.device_id IS NULL
  AND cp.station_id IS NULL
ON CONFLICT (device_id, metric_key, method_id, param_name)
DO NOTHING;

-- 方法3: pump_head_method_main (3个参数: rho, g, b_H)
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable, updated_by
)
SELECT 
    1 as station_id,
    d.id as device_id,
    cp.metric_key,
    cp.method_id,
    cp.param_name,
    cp.param_value,
    cp.param_type,
    cp.is_optimizable,
    'migration:072:device_level' as updated_by
FROM dim_devices d
CROSS JOIN calculation_parameters cp
WHERE d.id BETWEEN 1 AND 6
  AND cp.method_id = 'pump_head_method_main'
  AND cp.device_id IS NULL
  AND cp.station_id IS NULL
ON CONFLICT (device_id, metric_key, method_id, param_name)
DO NOTHING;

-- 方法4: pump_speed_method_a (2个参数: f_ref, n_ref)
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable, updated_by
)
SELECT 
    1 as station_id,
    d.id as device_id,
    cp.metric_key,
    cp.method_id,
    cp.param_name,
    cp.param_value,
    cp.param_type,
    cp.is_optimizable,
    'migration:072:device_level' as updated_by
FROM dim_devices d
CROSS JOIN calculation_parameters cp
WHERE d.id BETWEEN 1 AND 6
  AND cp.method_id = 'pump_speed_method_a'
  AND cp.device_id IS NULL
  AND cp.station_id IS NULL
ON CONFLICT (device_id, metric_key, method_id, param_name)
DO NOTHING;

-- 方法5: pump_speed_method_b (2个参数: pole_pairs, slip)
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable, updated_by
)
SELECT 
    1 as station_id,
    d.id as device_id,
    cp.metric_key,
    cp.method_id,
    cp.param_name,
    cp.param_value,
    cp.param_type,
    cp.is_optimizable,
    'migration:072:device_level' as updated_by
FROM dim_devices d
CROSS JOIN calculation_parameters cp
WHERE d.id BETWEEN 1 AND 6
  AND cp.method_id = 'pump_speed_method_b'
  AND cp.device_id IS NULL
  AND cp.station_id IS NULL
ON CONFLICT (device_id, metric_key, method_id, param_name)
DO NOTHING;

-- 方法6: pump_speed_method_c (2个参数: calibration_a, calibration_b)
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable, updated_by
)
SELECT 
    1 as station_id,
    d.id as device_id,
    cp.metric_key,
    cp.method_id,
    cp.param_name,
    cp.param_value,
    cp.param_type,
    cp.is_optimizable,
    'migration:072:device_level' as updated_by
FROM dim_devices d
CROSS JOIN calculation_parameters cp
WHERE d.id BETWEEN 1 AND 6
  AND cp.method_id = 'pump_speed_method_c'
  AND cp.device_id IS NULL
  AND cp.station_id IS NULL
ON CONFLICT (device_id, metric_key, method_id, param_name)
DO NOTHING;

-- 方法7: pump_torque_method_a (2个参数: rho, g)
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable, updated_by
)
SELECT 
    1 as station_id,
    d.id as device_id,
    cp.metric_key,
    cp.method_id,
    cp.param_name,
    cp.param_value,
    cp.param_type,
    cp.is_optimizable,
    'migration:072:device_level' as updated_by
FROM dim_devices d
CROSS JOIN calculation_parameters cp
WHERE d.id BETWEEN 1 AND 6
  AND cp.method_id = 'pump_torque_method_a'
  AND cp.device_id IS NULL
  AND cp.station_id IS NULL
ON CONFLICT (device_id, metric_key, method_id, param_name)
DO NOTHING;

-- 方法8: pump_torque_method_b (2个参数: pole_pairs, slip)
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable, updated_by
)
SELECT 
    1 as station_id,
    d.id as device_id,
    cp.metric_key,
    cp.method_id,
    cp.param_name,
    cp.param_value,
    cp.param_type,
    cp.is_optimizable,
    'migration:072:device_level' as updated_by
FROM dim_devices d
CROSS JOIN calculation_parameters cp
WHERE d.id BETWEEN 1 AND 6
  AND cp.method_id = 'pump_torque_method_b'
  AND cp.device_id IS NULL
  AND cp.station_id IS NULL
ON CONFLICT (device_id, metric_key, method_id, param_name)
DO NOTHING;

-- ============================================================================
-- 验证插入结果
-- ============================================================================
DO $$
DECLARE
    v_device_count INT;
    v_method_count INT;
    v_total_params INT;
BEGIN
    -- 统计设备级参数
    SELECT COUNT(DISTINCT device_id) INTO v_device_count
    FROM calculation_parameters
    WHERE device_id IS NOT NULL;
    
    SELECT COUNT(DISTINCT method_id) INTO v_method_count
    FROM calculation_parameters
    WHERE device_id IS NOT NULL;
    
    SELECT COUNT(*) INTO v_total_params
    FROM calculation_parameters
    WHERE device_id IS NOT NULL;
    
    RAISE NOTICE '========================================';
    RAISE NOTICE '设备级参数补充完成：';
    RAISE NOTICE '  设备数量：% 台', v_device_count;
    RAISE NOTICE '  方法数量：% 个', v_method_count;
    RAISE NOTICE '  参数总数：% 行', v_total_params;
    RAISE NOTICE '========================================';
END $$;

COMMIT;

-- ============================================================================
-- 迁移完成
-- ============================================================================
-- 版本：v072
-- 日期：2025-11-02
-- 说明：为6台泵补充了8个方法的设备级参数（约150行）
-- 参数值：复制自全局参数，后续可手动调整优化
-- ============================================================================

