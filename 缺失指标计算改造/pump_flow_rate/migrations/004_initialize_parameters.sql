-- 初始化 pump_flow_rate 参数配置
-- 移除 f_thr 和 p_thr，添加新的参数

BEGIN;

-- 1. 删除旧的全局参数（如果存在）
DELETE FROM calculation_parameters 
WHERE metric_key = 'pump_flow_rate' 
  AND param_name IN ('f_thr', 'p_thr');

-- 2. 初始化全局参数（12个参数）
INSERT INTO calculation_parameters (
    metric_key, 
    param_name, 
    param_value, 
    param_type, 
    description,
    station_id,
    device_id
) VALUES
    -- 方法A参数
    ('pump_flow_rate', 'alpha', '1.0', 'float', '功率指数（方法A）', NULL, NULL),
    ('pump_flow_rate', 'beta', '1.0', 'float', '频率指数（方法A）', NULL, NULL),
    
    -- 方法B参数
    ('pump_flow_rate', 'derivative_window', '5', 'int', '导数计算窗口大小（方法B）', NULL, NULL),
    
    -- 方法F参数
    ('pump_flow_rate', 'model_type', 'linear', 'string', '回归模型类型（方法F）', NULL, NULL),
    ('pump_flow_rate', 'model_path', '/models/pump_flow_rate.pkl', 'string', '模型文件路径（方法F）', NULL, NULL),
    
    -- 数据过滤参数
    ('pump_flow_rate', 'min_data_points', '10', 'int', '最小数据点数', NULL, NULL),
    ('pump_flow_rate', 'max_gap_seconds', '300', 'int', '最大数据间隔（秒）', NULL, NULL),
    
    -- 验证参数
    ('pump_flow_rate', 'min_flow_rate', '0.0', 'float', '最小流量（m³/h）', NULL, NULL),
    ('pump_flow_rate', 'max_flow_rate', '1000.0', 'float', '最大流量（m³/h）', NULL, NULL),
    ('pump_flow_rate', 'quality_threshold', '0.8', 'float', '质量阈值', NULL, NULL),
    
    -- 性能参数
    ('pump_flow_rate', 'batch_size', '1000', 'int', '批量写入大小', NULL, NULL),
    ('pump_flow_rate', 'time_chunk_hours', '1', 'int', '时间分片大小（小时）', NULL, NULL)
ON CONFLICT (metric_key, param_name, COALESCE(station_id, -1), COALESCE(device_id, -1)) 
DO UPDATE SET
    param_value = EXCLUDED.param_value,
    description = EXCLUDED.description;

-- 3. 验证参数初始化
DO $$
DECLARE
    param_count INT;
BEGIN
    SELECT COUNT(*) INTO param_count
    FROM calculation_parameters
    WHERE metric_key = 'pump_flow_rate'
      AND station_id IS NULL
      AND device_id IS NULL;
    
    IF param_count < 12 THEN
        RAISE EXCEPTION '参数初始化失败：期望12个参数，实际%个', param_count;
    END IF;
    
    RAISE NOTICE '✅ 参数初始化成功：%个全局参数', param_count;
END $$;

COMMIT;

-- 4. 查看初始化结果
SELECT 
    param_name,
    param_value,
    param_type,
    description
FROM calculation_parameters
WHERE metric_key = 'pump_flow_rate'
  AND station_id IS NULL
  AND device_id IS NULL
ORDER BY param_name;

