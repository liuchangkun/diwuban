-- ============================================================================
-- P5 优化回滚脚本：完善日志系统
-- ============================================================================
-- 创建时间：2025-11-06
-- 用途：回滚 P5 优化（索引、查询函数、存储过程扩展）
-- 使用方法：psql -U postgres -d your_database -f rollback_p5_diagnosis_log_system.sql
-- ============================================================================

-- 说明：本脚本将删除 P5 优化添加的所有数据库对象
-- 阶段1：删除 5 个索引
-- 阶段2：删除 3 个查询函数
-- 阶段3：恢复存储过程（删除诊断日志记录）

-- ============================================================================
-- 推荐的完整回滚方法
-- ============================================================================

-- 方法1：使用物理备份文件（推荐）
-- psql -U postgres -d pump_station_optimization -f scripts/sql/migrations/036_create_sp_mark_quality_window_vfast.sql.backup_p5_20251106_115928

-- 方法2：使用 Git 回滚（推荐）
-- git checkout p5_optimization_baseline -- scripts/sql/migrations/036_create_sp_mark_quality_window_vfast.sql
-- psql -U postgres -d pump_station_optimization -f scripts/sql/migrations/036_create_sp_mark_quality_window_vfast.sql

-- ============================================================================
-- 阶段1：删除索引
-- ============================================================================

DROP INDEX IF EXISTS public.idx_qdiag_run_id;
DROP INDEX IF EXISTS public.idx_qdiag_window;
DROP INDEX IF EXISTS public.idx_qdiag_device;
DROP INDEX IF EXISTS public.idx_qdiag_stage_level;
DROP INDEX IF EXISTS public.idx_qdiag_created;

-- 验证索引删除
SELECT 
    indexname
FROM pg_indexes
WHERE schemaname = 'public' 
  AND tablename = 'quality_diagnosis_log'
  AND indexname LIKE 'idx_qdiag%'
ORDER BY indexname;

-- ============================================================================
-- 阶段2：删除查询函数
-- ============================================================================

DROP FUNCTION IF EXISTS public.fn_get_diagnosis_log(text, text, text);
DROP FUNCTION IF EXISTS public.fn_get_diagnosis_log_by_device(bigint, timestamptz, timestamptz, text);
DROP FUNCTION IF EXISTS public.fn_cleanup_diagnosis_log(integer);

-- 验证函数删除
SELECT 
    proname AS function_name
FROM pg_proc
WHERE pronamespace = 'public'::regnamespace
  AND proname LIKE 'fn_%diagnosis_log%'
ORDER BY proname;

-- ============================================================================
-- 阶段3：恢复存储过程
-- ============================================================================

-- 使用物理备份或 Git 回滚恢复存储过程
-- 见上方"推荐的完整回滚方法"

-- ============================================================================
-- 回滚验证
-- ============================================================================

-- 1. 查看存储过程定义（确认诊断日志记录已删除）
-- \df+ public.sp_mark_quality_window_vfast

-- 2. 执行存储过程测试
-- CALL public.sp_mark_quality_window_vfast(
--     '2025-11-06 14:00:00'::timestamptz,
--     '2025-11-06 16:00:00'::timestamptz,
--     NULL, NULL, NULL
-- );

-- 3. 查询诊断日志（应该没有新日志）
-- SELECT COUNT(*) FROM public.quality_diagnosis_log
-- WHERE created_at > now() - interval '1 hour';

-- ============================================================================

