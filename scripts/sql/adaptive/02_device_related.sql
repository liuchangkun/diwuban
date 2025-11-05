-- ============================================
-- 自适应SQL脚本：依赖 device_id 的表
-- ============================================
-- 文件：scripts/sql/adaptive/02_device_related.sql
-- 用途：生成 device_rated_params 和 dim_device_capabilities
-- 依赖：dim_stations 和 dim_devices 表必须已存在且包含数据
-- 特性：自适应关联，使用 station_name + device_name 定位设备，能够适应设备ID变化和设备增减
-- ============================================

BEGIN;

-- ============================================
-- 表1：device_rated_params（设备额定参数）
-- ============================================

-- 清空表（完全重建）
TRUNCATE TABLE device_rated_params CASCADE;

-- ============================================
-- 站点1：二期供水泵房（6台变频泵 + 1台总管）
-- ============================================

-- 1号泵（变频泵）
INSERT INTO device_rated_params (device_id, param_key, value_numeric, unit, source)
SELECT 
    d.id,
    unnest(ARRAY['rated_frequency', 'poles_pair', 'rated_efficiency', 'rated_flow', 'rated_head', 'eta_motor', 'eta_vfd']),
    unnest(ARRAY[50, 2, 0.78, 400, 25, 0.93, 0.97]),
    unnest(ARRAY['Hz', NULL, NULL, 'm3/h', 'm', NULL, NULL]),
    '自适应SQL脚本生成'
FROM dim_devices d
JOIN dim_stations s ON d.station_id = s.id
WHERE s.name = '二期供水泵房' AND d.name = '二期供水泵房1#泵';

-- 2号泵（变频泵）
INSERT INTO device_rated_params (device_id, param_key, value_numeric, unit, source)
SELECT 
    d.id,
    unnest(ARRAY['rated_frequency', 'poles_pair', 'rated_efficiency', 'rated_flow', 'rated_head', 'eta_motor', 'eta_vfd']),
    unnest(ARRAY[50, 2, 0.78, 400, 25, 0.93, 0.97]),
    unnest(ARRAY['Hz', NULL, NULL, 'm3/h', 'm', NULL, NULL]),
    '自适应SQL脚本生成'
FROM dim_devices d
JOIN dim_stations s ON d.station_id = s.id
WHERE s.name = '二期供水泵房' AND d.name = '二期供水泵房2#泵';

-- 3号泵（变频泵）
INSERT INTO device_rated_params (device_id, param_key, value_numeric, unit, source)
SELECT 
    d.id,
    unnest(ARRAY['rated_frequency', 'poles_pair', 'rated_efficiency', 'rated_flow', 'rated_head', 'eta_motor', 'eta_vfd']),
    unnest(ARRAY[50, 2, 0.78, 400, 25, 0.93, 0.97]),
    unnest(ARRAY['Hz', NULL, NULL, 'm3/h', 'm', NULL, NULL]),
    '自适应SQL脚本生成'
FROM dim_devices d
JOIN dim_stations s ON d.station_id = s.id
WHERE s.name = '二期供水泵房' AND d.name = '二期供水泵房3#泵';

-- 4号泵（变频泵）
INSERT INTO device_rated_params (device_id, param_key, value_numeric, unit, source)
SELECT 
    d.id,
    unnest(ARRAY['rated_frequency', 'poles_pair', 'rated_efficiency', 'rated_flow', 'rated_head', 'eta_motor', 'eta_vfd']),
    unnest(ARRAY[50, 2, 0.78, 400, 25, 0.93, 0.97]),
    unnest(ARRAY['Hz', NULL, NULL, 'm3/h', 'm', NULL, NULL]),
    '自适应SQL脚本生成'
FROM dim_devices d
JOIN dim_stations s ON d.station_id = s.id
WHERE s.name = '二期供水泵房' AND d.name = '二期供水泵房4#泵';

-- 5号泵（变频泵）
INSERT INTO device_rated_params (device_id, param_key, value_numeric, unit, source)
SELECT 
    d.id,
    unnest(ARRAY['rated_frequency', 'poles_pair', 'rated_efficiency', 'rated_flow', 'rated_head', 'eta_motor', 'eta_vfd']),
    unnest(ARRAY[50, 2, 0.78, 400, 25, 0.93, 0.97]),
    unnest(ARRAY['Hz', NULL, NULL, 'm3/h', 'm', NULL, NULL]),
    '自适应SQL脚本生成'
FROM dim_devices d
JOIN dim_stations s ON d.station_id = s.id
WHERE s.name = '二期供水泵房' AND d.name = '二期供水泵房5#泵';

-- 6号泵（变频泵）
INSERT INTO device_rated_params (device_id, param_key, value_numeric, unit, source)
SELECT 
    d.id,
    unnest(ARRAY['rated_frequency', 'poles_pair', 'rated_efficiency', 'rated_flow', 'rated_head', 'eta_motor', 'eta_vfd']),
    unnest(ARRAY[50, 2, 0.78, 400, 25, 0.93, 0.97]),
    unnest(ARRAY['Hz', NULL, NULL, 'm3/h', 'm', NULL, NULL]),
    '自适应SQL脚本生成'
FROM dim_devices d
JOIN dim_stations s ON d.station_id = s.id
WHERE s.name = '二期供水泵房' AND d.name = '二期供水泵房6#泵';

-- 总管（main_pipeline）
INSERT INTO device_rated_params (device_id, param_key, value_numeric, unit, source)
SELECT 
    d.id,
    unnest(ARRAY['pipe_diameter', 'pipe_length', 'roughness_rel', 'C_hazen']),
    unnest(ARRAY[0.40, 150.0, 0.0005, 120]),
    unnest(ARRAY['m', 'm', NULL, NULL]),
    '自适应SQL脚本生成'
FROM dim_devices d
JOIN dim_stations s ON d.station_id = s.id
WHERE s.name = '二期供水泵房' AND d.type = 'main_pipeline';

-- ============================================
-- 站点2：二期取水泵房（2台变频泵 + 3台软启泵 + 1台总管）
-- ============================================

-- 1号泵（软启泵）
INSERT INTO device_rated_params (device_id, param_key, value_numeric, unit, source)
SELECT 
    d.id,
    unnest(ARRAY['rated_frequency', 'poles_pair', 'rated_efficiency', 'rated_flow', 'rated_head', 'eta_motor', 'eta_vfd']),
    unnest(ARRAY[50, 2, 0.74, 350, 22, 0.90, 1.00]),
    unnest(ARRAY['Hz', NULL, NULL, 'm3/h', 'm', NULL, NULL]),
    '自适应SQL脚本生成'
FROM dim_devices d
JOIN dim_stations s ON d.station_id = s.id
WHERE s.name = '二期取水泵房' AND d.name = '二期取水泵房1#泵';

-- 2号泵（变频泵）
INSERT INTO device_rated_params (device_id, param_key, value_numeric, unit, source)
SELECT 
    d.id,
    unnest(ARRAY['rated_frequency', 'poles_pair', 'rated_efficiency', 'rated_flow', 'rated_head', 'eta_motor', 'eta_vfd']),
    unnest(ARRAY[50, 2, 0.76, 350, 22, 0.92, 0.97]),
    unnest(ARRAY['Hz', NULL, NULL, 'm3/h', 'm', NULL, NULL]),
    '自适应SQL脚本生成'
FROM dim_devices d
JOIN dim_stations s ON d.station_id = s.id
WHERE s.name = '二期取水泵房' AND d.name = '二期取水泵房2#泵';

-- 3号泵（软启泵）
INSERT INTO device_rated_params (device_id, param_key, value_numeric, unit, source)
SELECT 
    d.id,
    unnest(ARRAY['rated_frequency', 'poles_pair', 'rated_efficiency', 'rated_flow', 'rated_head', 'eta_motor', 'eta_vfd']),
    unnest(ARRAY[50, 2, 0.74, 350, 22, 0.90, 1.00]),
    unnest(ARRAY['Hz', NULL, NULL, 'm3/h', 'm', NULL, NULL]),
    '自适应SQL脚本生成'
FROM dim_devices d
JOIN dim_stations s ON d.station_id = s.id
WHERE s.name = '二期取水泵房' AND d.name = '二期取水泵房3#泵';

-- 4号泵（软启泵）
INSERT INTO device_rated_params (device_id, param_key, value_numeric, unit, source)
SELECT 
    d.id,
    unnest(ARRAY['rated_frequency', 'poles_pair', 'rated_efficiency', 'rated_flow', 'rated_head', 'eta_motor', 'eta_vfd']),
    unnest(ARRAY[50, 2, 0.74, 350, 22, 0.90, 1.00]),
    unnest(ARRAY['Hz', NULL, NULL, 'm3/h', 'm', NULL, NULL]),
    '自适应SQL脚本生成'
FROM dim_devices d
JOIN dim_stations s ON d.station_id = s.id
WHERE s.name = '二期取水泵房' AND d.name = '二期取水泵房4#泵';

-- 5号泵（变频泵）
INSERT INTO device_rated_params (device_id, param_key, value_numeric, unit, source)
SELECT 
    d.id,
    unnest(ARRAY['rated_frequency', 'poles_pair', 'rated_efficiency', 'rated_flow', 'rated_head', 'eta_motor', 'eta_vfd']),
    unnest(ARRAY[50, 2, 0.76, 350, 22, 0.92, 0.97]),
    unnest(ARRAY['Hz', NULL, NULL, 'm3/h', 'm', NULL, NULL]),
    '自适应SQL脚本生成'
FROM dim_devices d
JOIN dim_stations s ON d.station_id = s.id
WHERE s.name = '二期取水泵房' AND d.name = '二期取水泵房5#泵';

-- 总管（main_pipeline）
INSERT INTO device_rated_params (device_id, param_key, value_numeric, unit, source)
SELECT 
    d.id,
    unnest(ARRAY['pipe_diameter', 'pipe_length', 'roughness_rel', 'C_hazen']),
    unnest(ARRAY[0.50, 200.0, 0.0005, 120]),
    unnest(ARRAY['m', 'm', NULL, NULL]),
    '自适应SQL脚本生成'
FROM dim_devices d
JOIN dim_stations s ON d.station_id = s.id
WHERE s.name = '二期取水泵房' AND d.type = 'main_pipeline';

-- ============================================
-- 表2：dim_device_capabilities（设备能力配置）
-- ============================================

-- 清空表（完全重建）
TRUNCATE TABLE dim_device_capabilities CASCADE;

-- 插入所有变频泵的能力配置
INSERT INTO dim_device_capabilities (
    device_id, vfd_enabled, freq_min, freq_max, rated_power_kw, rated_current_a, remark
)
SELECT 
    d.id,
    TRUE,
    25.0,
    50.0,
    75.0,
    150.0,
    '自适应SQL脚本生成 - 变频泵'
FROM dim_devices d
WHERE d.pump_type = 'variable_frequency';

-- 插入所有软启泵的能力配置
INSERT INTO dim_device_capabilities (
    device_id, vfd_enabled, freq_min, freq_max, rated_power_kw, rated_current_a, remark
)
SELECT 
    d.id,
    FALSE,
    50.0,
    50.0,
    55.0,
    110.0,
    '自适应SQL脚本生成 - 软启泵'
FROM dim_devices d
WHERE d.pump_type = 'soft_start';

COMMIT;

