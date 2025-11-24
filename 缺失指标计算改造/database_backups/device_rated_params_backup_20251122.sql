-- =====================================================
-- device_rated_params 表参数填充SQL
-- =====================================================
-- 创建时间: 2025-11-22
-- 用途: 为5个新增指标填充设备额定参数
-- 影响设备: 设备1-6（水泵设备）
-- 参数类型: 电机参数、管路参数、校准参数
-- =====================================================

-- 清理旧数据（如果存在）
DELETE FROM device_rated_params 
WHERE device_id IN (1,2,3,4,5,6) 
  AND param_key IN (
    'eta_motor', 'eta_vfd', 'drive_type', 
    'pole_pairs', 'slip',
    'L_offset', 'pipe_diameter'
  );

-- =====================================================
-- 设备1: 二期供水泵房1#泵
-- =====================================================
INSERT INTO device_rated_params (
    device_id, param_key, value_numeric, value_text, unit, source, 
    effective_from, station_id
) VALUES
-- 电机参数（用于pump_shaft_power）
(1, 'eta_motor', 0.92, NULL, '-', '设计参数', NOW(), 1),
(1, 'eta_vfd', 0.97, NULL, '-', '设计参数', NOW(), 1),
(1, 'drive_type', NULL, 'vfd', NULL, '设计参数', NOW(), 1),

-- 转速参数（用于pump_speed）
(1, 'pole_pairs', 2, NULL, '-', '设计参数', NOW(), 1),
(1, 'slip', 0.02, NULL, '-', '设计参数', NOW(), 1),

-- 管路参数（用于pump_inlet_pressure）
(1, 'L_offset', 2.5, NULL, 'm', '现场测量', NOW(), 1),
(1, 'pipe_diameter', 0.3, NULL, 'm', '设计参数', NOW(), 1);

-- =====================================================
-- 设备2: 二期供水泵房2#泵
-- =====================================================
INSERT INTO device_rated_params (
    device_id, param_key, value_numeric, value_text, unit, source, 
    effective_from, station_id
) VALUES
(2, 'eta_motor', 0.92, NULL, '-', '设计参数', NOW(), 1),
(2, 'eta_vfd', 0.97, NULL, '-', '设计参数', NOW(), 1),
(2, 'drive_type', NULL, 'vfd', NULL, '设计参数', NOW(), 1),
(2, 'pole_pairs', 2, NULL, '-', '设计参数', NOW(), 1),
(2, 'slip', 0.02, NULL, '-', '设计参数', NOW(), 1),
(2, 'L_offset', 2.5, NULL, 'm', '现场测量', NOW(), 1),
(2, 'pipe_diameter', 0.3, NULL, 'm', '设计参数', NOW(), 1);

-- =====================================================
-- 设备3: 二期供水泵房3#泵
-- =====================================================
INSERT INTO device_rated_params (
    device_id, param_key, value_numeric, value_text, unit, source, 
    effective_from, station_id
) VALUES
(3, 'eta_motor', 0.92, NULL, '-', '设计参数', NOW(), 1),
(3, 'eta_vfd', 0.97, NULL, '-', '设计参数', NOW(), 1),
(3, 'drive_type', NULL, 'vfd', NULL, '设计参数', NOW(), 1),
(3, 'pole_pairs', 2, NULL, '-', '设计参数', NOW(), 1),
(3, 'slip', 0.02, NULL, '-', '设计参数', NOW(), 1),
(3, 'L_offset', 2.5, NULL, 'm', '现场测量', NOW(), 1),
(3, 'pipe_diameter', 0.3, NULL, 'm', '设计参数', NOW(), 1);

-- =====================================================
-- 设备4: 二期供水泵房4#泵
-- =====================================================
INSERT INTO device_rated_params (
    device_id, param_key, value_numeric, value_text, unit, source, 
    effective_from, station_id
) VALUES
(4, 'eta_motor', 0.92, NULL, '-', '设计参数', NOW(), 1),
(4, 'eta_vfd', 0.97, NULL, '-', '设计参数', NOW(), 1),
(4, 'drive_type', NULL, 'vfd', NULL, '设计参数', NOW(), 1),
(4, 'pole_pairs', 2, NULL, '-', '设计参数', NOW(), 1),
(4, 'slip', 0.02, NULL, '-', '设计参数', NOW(), 1),
(4, 'L_offset', 2.5, NULL, 'm', '现场测量', NOW(), 1),
(4, 'pipe_diameter', 0.3, NULL, 'm', '设计参数', NOW(), 1);

-- =====================================================
-- 设备5: 二期供水泵房5#泵
-- =====================================================
INSERT INTO device_rated_params (
    device_id, param_key, value_numeric, value_text, unit, source, 
    effective_from, station_id
) VALUES
(5, 'eta_motor', 0.92, NULL, '-', '设计参数', NOW(), 1),
(5, 'eta_vfd', 0.97, NULL, '-', '设计参数', NOW(), 1),
(5, 'drive_type', NULL, 'vfd', NULL, '设计参数', NOW(), 1),
(5, 'pole_pairs', 2, NULL, '-', '设计参数', NOW(), 1),
(5, 'slip', 0.02, NULL, '-', '设计参数', NOW(), 1),
(5, 'L_offset', 2.5, NULL, 'm', '现场测量', NOW(), 1),
(5, 'pipe_diameter', 0.3, NULL, 'm', '设计参数', NOW(), 1);

-- =====================================================
-- 设备6: 二期供水泵房6#泵
-- =====================================================
INSERT INTO device_rated_params (
    device_id, param_key, value_numeric, value_text, unit, source, 
    effective_from, station_id
) VALUES
(6, 'eta_motor', 0.92, NULL, '-', '设计参数', NOW(), 1),
(6, 'eta_vfd', 0.97, NULL, '-', '设计参数', NOW(), 1),
(6, 'drive_type', NULL, 'vfd', NULL, '设计参数', NOW(), 1),
(6, 'pole_pairs', 2, NULL, '-', '设计参数', NOW(), 1),
(6, 'slip', 0.02, NULL, '-', '设计参数', NOW(), 1),
(6, 'L_offset', 2.5, NULL, 'm', '现场测量', NOW(), 1),
(6, 'pipe_diameter', 0.3, NULL, 'm', '设计参数', NOW(), 1);

-- =====================================================
-- 验证插入结果
-- =====================================================
SELECT 
    device_id,
    COUNT(*) as param_count,
    STRING_AGG(param_key, ', ' ORDER BY param_key) as params
FROM device_rated_params
WHERE device_id IN (1,2,3,4,5,6)
GROUP BY device_id
ORDER BY device_id;

-- 预期结果: 每个设备7个参数
-- device_id | param_count | params
-- ----------|-------------|-------
-- 1         | 7           | L_offset, drive_type, eta_motor, eta_vfd, pipe_diameter, pole_pairs, slip
-- 2         | 7           | L_offset, drive_type, eta_motor, eta_vfd, pipe_diameter, pole_pairs, slip
-- ...

-- =====================================================
-- 参数说明
-- =====================================================
-- eta_motor: 电机效率（0.92 = 92%）
-- eta_vfd: 变频器效率（0.97 = 97%，软启动为1.0）
-- drive_type: 驱动类型（'vfd' = 变频驱动，'soft_start' = 软启动）
-- pole_pairs: 极对数（2 = 4极电机）
-- slip: 滑差率（0.02 = 2%）
-- L_offset: 水池液位到泵入口的高度差（2.5m）
-- pipe_diameter: 管道直径（0.3m = 300mm）

