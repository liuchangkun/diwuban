-- 目的：为7台设备（6台泵+1台总管）补充设备级计算参数
-- 策略：
--   步骤1：复制全局参数作为设备级参数的初始值
--   步骤2：从 device_rated_params 表更新准确的设备级参数（eta_motor, eta_vfd, pole_pairs, f_ref）
-- 影响：calculation_parameters 表新增约175行设备级参数
-- 版本：v072_v2（修订版，使用准确的设备级参数）

BEGIN;

-- ============================================================================
-- 步骤1：为设备1-7复制全局参数到设备级（作为基础）
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
    'migration:072_v2:step1:copy_global' as updated_by
FROM dim_devices d
CROSS JOIN calculation_parameters cp
WHERE d.id BETWEEN 1 AND 7  -- 修改：包含设备7（总管）
  AND d.is_active = true
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
    'migration:072_v2:step1:copy_global' as updated_by
FROM dim_devices d
CROSS JOIN calculation_parameters cp
WHERE d.id BETWEEN 1 AND 7
  AND d.is_active = true
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
    'migration:072_v2:step1:copy_global' as updated_by
FROM dim_devices d
CROSS JOIN calculation_parameters cp
WHERE d.id BETWEEN 1 AND 7
  AND d.is_active = true
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
    'migration:072_v2:step1:copy_global' as updated_by
FROM dim_devices d
CROSS JOIN calculation_parameters cp
WHERE d.id BETWEEN 1 AND 7
  AND d.is_active = true
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
    'migration:072_v2:step1:copy_global' as updated_by
FROM dim_devices d
CROSS JOIN calculation_parameters cp
WHERE d.id BETWEEN 1 AND 7
  AND d.is_active = true
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
    'migration:072_v2:step1:copy_global' as updated_by
FROM dim_devices d
CROSS JOIN calculation_parameters cp
WHERE d.id BETWEEN 1 AND 7
  AND d.is_active = true
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
    'migration:072_v2:step1:copy_global' as updated_by
FROM dim_devices d
CROSS JOIN calculation_parameters cp
WHERE d.id BETWEEN 1 AND 7
  AND d.is_active = true
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
    'migration:072_v2:step1:copy_global' as updated_by
FROM dim_devices d
CROSS JOIN calculation_parameters cp
WHERE d.id BETWEEN 1 AND 7
  AND d.is_active = true
  AND cp.method_id = 'pump_torque_method_b'
  AND cp.device_id IS NULL
  AND cp.station_id IS NULL
ON CONFLICT (device_id, metric_key, method_id, param_name)
DO NOTHING;

-- ============================================================================
-- 步骤2：从 device_rated_params 表更新准确的设备级参数
-- ============================================================================

-- 更新 eta_motor（电机效率）
UPDATE calculation_parameters cp
SET 
    param_value = drp.param_value,
    updated_by = 'migration:072_v2:step2:from_rated_params:eta_motor',
    updated_at = NOW()
FROM device_rated_params drp
WHERE cp.device_id = drp.device_id
  AND cp.device_id BETWEEN 1 AND 7
  AND cp.param_name = 'eta_motor'
  AND drp.param_key = 'eta_motor';

-- 更新 eta_vfd（变频器效率）
UPDATE calculation_parameters cp
SET 
    param_value = drp.param_value,
    updated_by = 'migration:072_v2:step2:from_rated_params:eta_vfd',
    updated_at = NOW()
FROM device_rated_params drp
WHERE cp.device_id = drp.device_id
  AND cp.device_id BETWEEN 1 AND 7
  AND cp.param_name = 'eta_vfd'
  AND drp.param_key = 'eta_vfd';

-- 更新 pole_pairs（极对数）
-- 注意：device_rated_params 中的字段名是 poles_pair（单数），calculation_parameters 中是 pole_pairs（复数）
UPDATE calculation_parameters cp
SET 
    param_value = drp.param_value,
    updated_by = 'migration:072_v2:step2:from_rated_params:pole_pairs',
    updated_at = NOW()
FROM device_rated_params drp
WHERE cp.device_id = drp.device_id
  AND cp.device_id BETWEEN 1 AND 7
  AND cp.param_name = 'pole_pairs'
  AND drp.param_key = 'poles_pair';

-- 更新 f_ref（额定频率）
UPDATE calculation_parameters cp
SET 
    param_value = drp.param_value,
    updated_by = 'migration:072_v2:step2:from_rated_params:f_ref',
    updated_at = NOW()
FROM device_rated_params drp
WHERE cp.device_id = drp.device_id
  AND cp.device_id BETWEEN 1 AND 7
  AND cp.param_name = 'f_ref'
  AND drp.param_key = 'rated_frequency';

-- ============================================================================
-- 验证插入和更新结果
-- ============================================================================
DO $$
DECLARE
    v_device_count INT;
    v_method_count INT;
    v_total_params INT;
    v_updated_from_rated INT;
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
    
    -- 统计从 device_rated_params 更新的参数
    SELECT COUNT(*) INTO v_updated_from_rated
    FROM calculation_parameters
    WHERE updated_by LIKE 'migration:072_v2:step2:from_rated_params:%';
    
    RAISE NOTICE '========================================';
    RAISE NOTICE '设备级参数补充完成（v072_v2）：';
    RAISE NOTICE '  设备数量：% 台', v_device_count;
    RAISE NOTICE '  方法数量：% 个', v_method_count;
    RAISE NOTICE '  参数总数：% 行', v_total_params;
    RAISE NOTICE '  从 device_rated_params 更新：% 行', v_updated_from_rated;
    RAISE NOTICE '========================================';
END $$;

COMMIT;

-- ============================================================================
-- 迁移完成
-- ============================================================================
-- 版本：v072_v2（修订版）
-- 日期：2025-11-04
-- 说明：
--   1. 为7台设备（6台泵+1台总管）补充了8个方法的设备级参数（约175行）
--   2. 步骤1：复制全局参数作为基础
--   3. 步骤2：从 device_rated_params 表更新准确的设备级参数（eta_motor, eta_vfd, pole_pairs, f_ref）
-- 改进：相比 v072，新增设备7（总管），并使用准确的设备级参数
-- ============================================================================

