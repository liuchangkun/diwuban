-- ============================================
-- pump_shaft_power 参数初始化脚本
-- ============================================
-- 用途：初始化pump_shaft_power计算所需的所有参数
-- 创建日期：2025-11-22
-- 协议：RIPER-5 计划模式
-- ============================================

-- ============================================
-- 1. device_rated_params表：设备额定参数
-- ============================================
-- 为设备1-6添加eta_motor和eta_vfd参数

INSERT INTO device_rated_params (
    station_id, 
    device_id, 
    param_key, 
    value_numeric, 
    unit, 
    source,
    effective_from
) VALUES
    -- 设备1
    (1, 1, 'eta_motor', 0.92, '-', 'manual', '2025-10-22 00:00:00+08'),
    (1, 1, 'eta_vfd', 0.97, '-', 'manual', '2025-10-22 00:00:00+08'),
    
    -- 设备2
    (1, 2, 'eta_motor', 0.92, '-', 'manual', '2025-10-22 00:00:00+08'),
    (1, 2, 'eta_vfd', 0.97, '-', 'manual', '2025-10-22 00:00:00+08'),
    
    -- 设备3
    (1, 3, 'eta_motor', 0.92, '-', 'manual', '2025-10-22 00:00:00+08'),
    (1, 3, 'eta_vfd', 0.97, '-', 'manual', '2025-10-22 00:00:00+08'),
    
    -- 设备4
    (1, 4, 'eta_motor', 0.92, '-', 'manual', '2025-10-22 00:00:00+08'),
    (1, 4, 'eta_vfd', 0.97, '-', 'manual', '2025-10-22 00:00:00+08'),
    
    -- 设备5
    (1, 5, 'eta_motor', 0.92, '-', 'manual', '2025-10-22 00:00:00+08'),
    (1, 5, 'eta_vfd', 0.97, '-', 'manual', '2025-10-22 00:00:00+08'),
    
    -- 设备6
    (1, 6, 'eta_motor', 0.92, '-', 'manual', '2025-10-22 00:00:00+08'),
    (1, 6, 'eta_vfd', 0.97, '-', 'manual', '2025-10-22 00:00:00+08')
ON CONFLICT (station_id, device_id, param_key) 
DO UPDATE SET 
    value_numeric = EXCLUDED.value_numeric,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- 2. calculation_parameters表：计算参数
-- ============================================
-- 添加pump_shaft_power的验证参数和过滤参数
-- 注意：不再使用method_id字段（已废弃）

INSERT INTO calculation_parameters (
    station_id,
    device_id,
    metric_key,
    param_name,
    param_value,
    param_type
) VALUES
    -- 过滤参数（全局）
    (NULL, NULL, 'pump_shaft_power', 'max_power', 200.0, 'float'),

    -- 验证参数（全局）
    (NULL, NULL, 'pump_shaft_power', 'min_power', 0.0, 'float'),
    (NULL, NULL, 'pump_shaft_power', 'max_shaft_power', 500.0, 'float'),
    (NULL, NULL, 'pump_shaft_power', 'max_change_rate', 50.0, 'float')
ON CONFLICT (station_id, device_id, metric_key, param_name)
DO UPDATE SET
    param_value = EXCLUDED.param_value,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- 3. 验证参数插入结果
-- ============================================

-- 验证device_rated_params
SELECT 
    device_id,
    param_key,
    value_numeric,
    unit
FROM device_rated_params
WHERE device_id IN (1, 2, 3, 4, 5, 6)
  AND param_key IN ('eta_motor', 'eta_vfd')
ORDER BY device_id, param_key;

-- 验证calculation_parameters
SELECT
    metric_key,
    param_name,
    param_value,
    param_type
FROM calculation_parameters
WHERE metric_key = 'pump_shaft_power'
ORDER BY param_name;

-- ============================================
-- 4. 参数说明
-- ============================================

/*
device_rated_params参数说明：
- eta_motor: 电机效率（无量纲），默认0.92
- eta_vfd: 变频器效率（无量纲），默认0.97

calculation_parameters参数说明：
- max_power: 功率上限（kW），用于过滤异常值，默认200.0
- min_power: 轴功率最小值（kW），默认0.0
- max_shaft_power: 轴功率最大值（kW），默认500.0
- max_change_rate: 最大变化率（kW/s），默认50.0

计算公式：
P_shaft = P_active / (η_motor × η_vfd)

物理约束：
- η_motor × η_vfd < 1，因此 P_shaft > P_active
- 典型值：η_motor = 0.92, η_vfd = 0.97, η_motor × η_vfd ≈ 0.8924
- 示例：P_active = 100 kW → P_shaft ≈ 112.1 kW
*/

-- ============================================
-- 脚本结束
-- ============================================

