-- ============================================================================
-- P1 优化回滚脚本：优化规则503
-- ============================================================================
-- 创建时间：2025-11-06
-- 用途：回滚 P1 优化（规则503的临时表合并和累积计数优化）
-- 使用方法：psql -U postgres -d your_database -f rollback_p1_optimize_rule_503.sql
-- ============================================================================

-- 说明：本脚本将恢复规则503的原始实现
-- 优化1：t503_keys + t503_total_secs 合并 → 拆分回两个表
-- 优化2：t503_feat + t503_final 合并 → 拆分回两个表
-- 优化3：ROW_NUMBER() → SUM(1) OVER

-- ============================================================================
-- 推荐的完整回滚方法
-- ============================================================================

-- 方法1：使用物理备份文件（推荐）
-- psql -U postgres -d pump_station_optimization -f scripts/sql/migrations/036_create_sp_mark_quality_window_vfast.sql.backup_p1_20251106_114333

-- 方法2：使用 Git 回滚（推荐）
-- git checkout p1_optimization_baseline -- scripts/sql/migrations/036_create_sp_mark_quality_window_vfast.sql
-- psql -U postgres -d pump_station_optimization -f scripts/sql/migrations/036_create_sp_mark_quality_window_vfast.sql

-- ============================================================================
-- 回滚验证
-- ============================================================================

-- 1. 查看存储过程定义
-- \df+ public.sp_mark_quality_window_vfast

-- 2. 执行存储过程测试
-- CALL public.sp_mark_quality_window_vfast(
--     '2025-11-06 14:00:00'::timestamptz,
--     '2025-11-06 16:00:00'::timestamptz,
--     NULL, NULL, NULL
-- );

-- 3. 查询性能数据
-- SELECT stage, duration_ms, rows_affected
-- FROM public.quality_profile_log
-- WHERE window_start = '2025-11-06 14:00:00'
--   AND window_end = '2025-11-06 16:00:00'
-- ORDER BY duration_ms DESC;

-- ============================================================================

