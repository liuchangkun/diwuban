-- ============================================================================
-- 回滚脚本 #001: 删除 calculation_logs 表
-- ============================================================================
-- 创建时间: 2025-01-14
-- 作者: AI
-- 目的: 回滚 001_create_calculation_logs.sql 的所有更改
-- 警告: 此操作将删除所有日志数据，请谨慎执行！
-- ============================================================================

-- 1. 删除分区维护函数
DROP FUNCTION IF EXISTS maintain_calculation_logs_partitions();

-- 2. 删除 calculation_logs 表（包括所有分区）
DROP TABLE IF EXISTS calculation_logs CASCADE;

-- 3. 验证删除成功
DO $$
DECLARE
    table_count INT;
    partition_count INT;
BEGIN
    -- 验证表已删除
    SELECT COUNT(*) INTO table_count
    FROM pg_tables
    WHERE tablename = 'calculation_logs';
    
    IF table_count > 0 THEN
        RAISE EXCEPTION '表 calculation_logs 删除失败';
    END IF;
    
    -- 验证分区已删除
    SELECT COUNT(*) INTO partition_count
    FROM pg_tables
    WHERE tablename LIKE 'calculation_logs_%';
    
    IF partition_count > 0 THEN
        RAISE WARNING '仍有 % 个分区未删除', partition_count;
    ELSE
        RAISE NOTICE '✅ 回滚成功！所有表和分区已删除';
    END IF;
END;
$$;

-- ============================================================================
-- 回滚完成
-- ============================================================================

