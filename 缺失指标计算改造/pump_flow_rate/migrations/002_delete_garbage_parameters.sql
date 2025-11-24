-- ============================================================================
-- 数据库迁移脚本 #002: 删除垃圾参数 f_thr 和 p_thr
-- ============================================================================
-- 创建时间: 2025-01-14
-- 作者: AI
-- 目的: 删除硬编码阈值参数 f_thr 和 p_thr（已移除硬编码逻辑）
-- 依赖: 无
-- 回滚: 见 002_rollback_delete_garbage_parameters.sql
-- ============================================================================

-- 1. 查询删除前的参数数量
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
    
    RAISE NOTICE '删除前参数数量: f_thr = %, p_thr = %', f_thr_count, p_thr_count;
END;
$$;

-- 2. 删除 f_thr 参数（所有级别：全局/泵站/设备）
DELETE FROM calculation_parameters
WHERE param_name = 'f_thr';

-- 3. 删除 p_thr 参数（所有级别：全局/泵站/设备）
DELETE FROM calculation_parameters
WHERE param_name = 'p_thr';

-- 4. 验证删除结果
DO $$
DECLARE
    f_thr_count INT;
    p_thr_count INT;
    total_count INT;
BEGIN
    SELECT COUNT(*) INTO f_thr_count
    FROM calculation_parameters
    WHERE param_name = 'f_thr';
    
    SELECT COUNT(*) INTO p_thr_count
    FROM calculation_parameters
    WHERE param_name = 'p_thr';
    
    total_count := f_thr_count + p_thr_count;
    
    IF total_count > 0 THEN
        RAISE EXCEPTION '删除失败！仍有 % 个参数未删除 (f_thr=%, p_thr=%)', 
            total_count, f_thr_count, p_thr_count;
    END IF;
    
    RAISE NOTICE '✅ 删除成功！f_thr 和 p_thr 参数已全部删除';
END;
$$;

-- ============================================================================
-- 迁移完成
-- ============================================================================

