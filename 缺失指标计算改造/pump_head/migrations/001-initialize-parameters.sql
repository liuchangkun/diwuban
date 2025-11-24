-- =====================================================
-- pump_head 参数初始化脚本
-- =====================================================
-- 文件: 001-initialize-parameters.sql
-- 创建日期: 2025-11-17
-- 描述: 初始化 pump_head 计算所需的参数
-- =====================================================

-- 1. 全局参数（所有设备共享）
-- =====================================================

INSERT INTO calculation_parameters (
    metric_key,
    param_name,
    param_value,
    param_type,
    station_id,
    device_id,
    is_optimizable
) VALUES
    ('pump_head', 'rho', 1000.0, 'float', NULL, NULL, FALSE),
    ('pump_head', 'g', 9.81, 'float', NULL, NULL, FALSE)
ON CONFLICT (metric_key, param_name, COALESCE(station_id, -1), COALESCE(device_id, -1)) DO NOTHING;

-- 2. 泵站级参数（泵站16）
-- =====================================================

INSERT INTO calculation_parameters (
    metric_key,
    param_name,
    param_value,
    param_type,
    station_id,
    device_id,
    is_optimizable
) VALUES
    ('pump_head', 'N_total_pumps', 6, 'int', 16, NULL, FALSE)
ON CONFLICT (metric_key, param_name, COALESCE(station_id, -1), COALESCE(device_id, -1)) DO NOTHING;

-- 3. 设备级参数（设备1-6）
-- =====================================================

-- 设备1
INSERT INTO calculation_parameters (
    metric_key,
    param_name,
    param_value,
    param_type,
    station_id,
    device_id,
    is_optimizable
) VALUES
    ('pump_head', 'K_pipe_loss', 0.00001, 'float', 16, 1, TRUE),
    ('pump_head', 'alpha_multi_pump', 0.02, 'float', 16, 1, TRUE)
ON CONFLICT (metric_key, param_name, COALESCE(station_id, -1), COALESCE(device_id, -1)) DO NOTHING;

-- 设备2
INSERT INTO calculation_parameters (
    metric_key,
    param_name,
    param_value,
    param_type,
    station_id,
    device_id,
    is_optimizable
) VALUES
    ('pump_head', 'K_pipe_loss', 0.00001, 'float', 16, 2, TRUE),
    ('pump_head', 'alpha_multi_pump', 0.02, 'float', 16, 2, TRUE)
ON CONFLICT (metric_key, param_name, COALESCE(station_id, -1), COALESCE(device_id, -1)) DO NOTHING;

-- 设备3
INSERT INTO calculation_parameters (
    metric_key,
    param_name,
    param_value,
    param_type,
    station_id,
    device_id,
    is_optimizable
) VALUES
    ('pump_head', 'K_pipe_loss', 0.00001, 'float', 16, 3, TRUE),
    ('pump_head', 'alpha_multi_pump', 0.02, 'float', 16, 3, TRUE)
ON CONFLICT (metric_key, param_name, COALESCE(station_id, -1), COALESCE(device_id, -1)) DO NOTHING;

-- 设备4
INSERT INTO calculation_parameters (
    metric_key,
    param_name,
    param_value,
    param_type,
    station_id,
    device_id,
    is_optimizable
) VALUES
    ('pump_head', 'K_pipe_loss', 0.00001, 'float', 16, 4, TRUE),
    ('pump_head', 'alpha_multi_pump', 0.02, 'float', 16, 4, TRUE)
ON CONFLICT (metric_key, param_name, COALESCE(station_id, -1), COALESCE(device_id, -1)) DO NOTHING;

-- 设备5
INSERT INTO calculation_parameters (
    metric_key,
    param_name,
    param_value,
    param_type,
    station_id,
    device_id,
    is_optimizable
) VALUES
    ('pump_head', 'K_pipe_loss', 0.00001, 'float', 16, 5, TRUE),
    ('pump_head', 'alpha_multi_pump', 0.02, 'float', 16, 5, TRUE)
ON CONFLICT (metric_key, param_name, COALESCE(station_id, -1), COALESCE(device_id, -1)) DO NOTHING;

-- 设备6
INSERT INTO calculation_parameters (
    metric_key,
    param_name,
    param_value,
    param_type,
    station_id,
    device_id,
    is_optimizable
) VALUES
    ('pump_head', 'K_pipe_loss', 0.00001, 'float', 16, 6, TRUE),
    ('pump_head', 'alpha_multi_pump', 0.02, 'float', 16, 6, TRUE)
ON CONFLICT (metric_key, param_name, COALESCE(station_id, -1), COALESCE(device_id, -1)) DO NOTHING;

-- =====================================================
-- 验证查询
-- =====================================================

-- 查询所有 pump_head 参数
SELECT
    metric_key,
    param_name,
    param_value,
    param_type,
    station_id,
    device_id,
    is_optimizable
FROM calculation_parameters
WHERE metric_key = 'pump_head'
ORDER BY
    COALESCE(station_id, 999),
    COALESCE(device_id, 999),
    param_name;

-- 预期结果：
-- - 2个全局参数（rho, g）
-- - 1个泵站参数（N_total_pumps）
-- - 12个设备参数（6个设备 × 2个参数）
-- 总计：15条记录

