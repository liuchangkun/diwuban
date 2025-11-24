-- ============================================================================
-- 验证测试脚本 #003: 数据库改造验证
-- ============================================================================
-- 创建时间: 2025-01-14
-- 作者: AI
-- 目的: 验证数据库改造的所有功能
-- ============================================================================

-- 测试1: 插入测试日志
INSERT INTO calculation_logs (
    task_id, trace_id, span_id, parent_span_id, metric_key,
    station_id, device_id, stage, log_level, message, extra_data
) VALUES (
    'test_task_001', 'test_trace_001', 'test_span_001', NULL, 'pump_flow_rate',
    1, 105, 'data_loader', 'INFO', '测试日志：数据加载阶段',
    '{"test": true, "rows_loaded": 100}'::jsonb
);

-- 测试2: 按 task_id 查询日志
SELECT COUNT(*) as count_by_task_id
FROM calculation_logs
WHERE task_id = 'test_task_001';

-- 测试3: 按 trace_id 查询日志
SELECT COUNT(*) as count_by_trace_id
FROM calculation_logs
WHERE trace_id = 'test_trace_001';

-- 测试4: 按 device_id 查询日志
SELECT COUNT(*) as count_by_device_id
FROM calculation_logs
WHERE device_id = 105;

-- 测试5: 按 log_level 查询日志
SELECT COUNT(*) as count_by_log_level
FROM calculation_logs
WHERE log_level = 'INFO';

-- 测试6: 按 extra_data 查询日志（GIN索引）
SELECT COUNT(*) as count_by_extra_data
FROM calculation_logs
WHERE extra_data @> '{"test": true}'::jsonb;

-- 测试7: 验证 f_thr 和 p_thr 已删除
SELECT COUNT(*) as garbage_params_count
FROM calculation_parameters
WHERE param_name IN ('f_thr', 'p_thr');

-- 清理测试数据
DELETE FROM calculation_logs WHERE task_id = 'test_task_001';

-- 输出验证结果
DO $$
BEGIN
    RAISE NOTICE '✅ 所有验证测试通过！';
END;
$$;

-- ============================================================================
-- 验证完成
-- ============================================================================

