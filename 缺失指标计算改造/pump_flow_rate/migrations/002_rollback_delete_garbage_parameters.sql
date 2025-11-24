-- ============================================================================
-- 回滚脚本 #002: 恢复 f_thr 和 p_thr 参数
-- ============================================================================
-- 创建时间: 2025-01-14
-- 作者: AI
-- 目的: 回滚 002_delete_garbage_parameters.sql 的更改
-- 警告: 仅用于紧急回滚，不建议恢复这些已废弃的参数
-- ============================================================================

-- 1. 恢复 f_thr 参数（全局级别，默认值 3.0）
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value,
    param_type, is_optimizable, created_at, updated_at, updated_by
) VALUES (
    NULL, NULL, 'pump_flow_rate', NULL, 'f_thr', 3.0,
    'float', false, NOW(), NOW(), 'rollback_script'
);

-- 2. 恢复 p_thr 参数（全局级别，默认值 0.5）
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value,
    param_type, is_optimizable, created_at, updated_at, updated_by
) VALUES (
    NULL, NULL, 'pump_flow_rate', NULL, 'p_thr', 0.5,
    'float', false, NOW(), NOW(), 'rollback_script'
);

-- 3. 验证恢复结果
DO $$
DECLARE
    f_thr_count INT;
    p_thr_count INT;
BEGIN
    SELECT COUNT(*) INTO f_thr_count
    FROM calculation_parameters
    WHERE param_name = 'f_thr';
    
    SELECT COUNT(*) INTO p_thr_count
    FROM calculation_parameters
    WHERE param_name = 'p_thr';
    
    IF f_thr_count = 0 OR p_thr_count = 0 THEN
        RAISE EXCEPTION '恢复失败！f_thr=%, p_thr=%', f_thr_count, p_thr_count;
    END IF;
    
    RAISE NOTICE '✅ 回滚成功！f_thr 和 p_thr 参数已恢复';
END;
$$;

-- ============================================================================
-- 回滚完成
-- ============================================================================

