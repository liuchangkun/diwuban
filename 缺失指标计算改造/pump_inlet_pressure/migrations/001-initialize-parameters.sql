-- =====================================================
-- pump_inlet_pressure 参数初始化脚本
-- =====================================================
-- 创建时间: 2025-11-16
-- 说明: 初始化 pump_inlet_pressure 计算所需的所有参数
-- 参考: pump_flow_rate/migrations/004_initialize_parameters.sql
-- =====================================================

BEGIN;

-- =====================================================
-- 1. 插入全局物理常数（3个参数）
-- =====================================================

INSERT INTO calculation_parameters (
    station_id,
    device_id,
    metric_key,
    method_id,
    param_name,
    param_value,
    param_type,
    is_optimizable
) VALUES
    -- 大气压
    (NULL, NULL, 'pump_inlet_pressure', 'global_constants', 'P_atm', 0.101325, 'float', FALSE),

    -- 水密度
    (NULL, NULL, 'pump_inlet_pressure', 'global_constants', 'rho', 1000.0, 'float', FALSE),

    -- 重力加速度
    (NULL, NULL, 'pump_inlet_pressure', 'global_constants', 'g', 9.80665, 'float', FALSE)

ON CONFLICT (metric_key, param_name, COALESCE(station_id, -1), COALESCE(device_id, -1))
DO UPDATE SET
    param_value = EXCLUDED.param_value;

-- =====================================================
-- 2. 设备参数配置说明（不自动插入，由用户根据实际情况配置）
-- =====================================================

-- ⚠️ 重要：设备参数（L_offset, pipe_diameter）必须由用户根据实际情况配置！
-- ⚠️ 不要为不存在的设备添加参数！
-- ⚠️ 以下是配置示例，仅供参考，不会自动执行

-- 示例：为设备105配置参数（假设设备105存在）
-- INSERT INTO calculation_parameters (
--     station_id,
--     device_id,
--     metric_key,
--     method_id,
--     param_name,
--     param_value,
--     param_type,
--     is_optimizable
-- ) VALUES
--     -- 水池液位到泵入口的固定高度差（根据现场测量或图纸）
--     (14, 105, 'pump_inlet_pressure', 'pump_inlet_pressure_equiv_coef', 'L_offset', 2.5, 'float', FALSE),
--
--     -- 进水管道直径（根据现场测量或图纸）
--     (14, 105, 'pump_inlet_pressure', 'pump_inlet_pressure_equiv_coef', 'pipe_diameter', 0.3, 'float', FALSE)
-- ON CONFLICT (metric_key, param_name, COALESCE(station_id, -1), COALESCE(device_id, -1))
-- DO UPDATE SET
--     param_value = EXCLUDED.param_value;

-- =====================================================
-- 3. 插入方法参数（2个参数，全局默认）
-- =====================================================

INSERT INTO calculation_parameters (
    station_id,
    device_id,
    metric_key,
    method_id,
    param_name,
    param_value,
    param_type,
    is_optimizable
) VALUES
    -- 等效损失系数
    (NULL, NULL, 'pump_inlet_pressure', 'pump_inlet_pressure_equiv_coef', 'K_eq', 10.0, 'float', TRUE),

    -- 流速警告阈值
    (NULL, NULL, 'pump_inlet_pressure', 'pump_inlet_pressure_equiv_coef', 'v_max_warning', 3.0, 'float', FALSE)

ON CONFLICT (metric_key, param_name, COALESCE(station_id, -1), COALESCE(device_id, -1))
DO UPDATE SET
    param_value = EXCLUDED.param_value;

COMMIT;

-- =====================================================
-- 4. 验证参数插入
-- =====================================================

-- 查询所有 pump_inlet_pressure 参数
SELECT
    station_id,
    device_id,
    method_id,
    param_name,
    param_value,
    param_type,
    is_optimizable
FROM calculation_parameters
WHERE metric_key = 'pump_inlet_pressure'
ORDER BY
    COALESCE(station_id, -1),
    COALESCE(device_id, -1),
    param_name;

-- 预期结果：5条记录（只有全局参数）
-- 3个全局物理常数（P_atm, rho, g）
-- 2个方法参数（K_eq, v_max_warning）
--
-- ⚠️ 设备参数（L_offset, pipe_diameter）需要用户根据实际情况手动配置

-- =====================================================
-- 5. 参数配置说明
-- =====================================================

-- 全局物理常数（3个，已自动插入）：
--   - P_atm: 大气压，固定值 0.101325 MPa
--   - rho: 水密度，固定值 1000.0 kg/m³
--   - g: 重力加速度，固定值 9.80665 m/s²

-- 方法参数（2个，已自动插入）：
--   - K_eq: 等效损失系数（无量纲），可在全局/泵站/设备三级配置，可优化
--   - v_max_warning: 流速警告阈值（m/s），全局配置

-- ⚠️ 设备参数（2个，需要用户手动配置）：
--   - L_offset: 水池液位到泵入口的固定高度差（m），根据现场测量或图纸配置
--   - pipe_diameter: 进水管道直径（m），根据现场测量或图纸配置
--
--   ⚠️ 重要：必须为每个需要计算 pump_inlet_pressure 的设备单独配置这两个参数！
--   ⚠️ 如果设备缺少这两个参数，计算将失败或使用备用方法（静压法）

-- =====================================================
-- 6. 如何为设备配置参数（用户手动操作）
-- =====================================================

-- ⚠️ 步骤1：查询需要配置的设备列表
-- SELECT device_id, device_name, station_id
-- FROM dim_devices
-- WHERE device_type = 'pump'
--   AND is_active = TRUE
-- ORDER BY station_id, device_id;

-- ⚠️ 步骤2：根据现场情况，为每个设备配置参数
-- 示例：为设备106配置参数（假设设备106存在且需要计算 pump_inlet_pressure）
--
-- INSERT INTO calculation_parameters (
--     station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable
-- ) VALUES
--     -- L_offset：根据现场测量或图纸确定
--     (14, 106, 'pump_inlet_pressure', 'pump_inlet_pressure_equiv_coef', 'L_offset', 3.0, 'float', FALSE),
--
--     -- pipe_diameter：根据现场测量或图纸确定
--     (14, 106, 'pump_inlet_pressure', 'pump_inlet_pressure_equiv_coef', 'pipe_diameter', 0.35, 'float', FALSE)
-- ON CONFLICT (metric_key, param_name, COALESCE(station_id, -1), COALESCE(device_id, -1))
-- DO UPDATE SET param_value = EXCLUDED.param_value;

-- ⚠️ 步骤3：验证参数配置
-- SELECT device_id, param_name, param_value
-- FROM calculation_parameters
-- WHERE metric_key = 'pump_inlet_pressure'
--   AND device_id IS NOT NULL
-- ORDER BY device_id, param_name;

-- =====================================================
-- 脚本结束
-- =====================================================

