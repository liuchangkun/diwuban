-- ============================================================================
-- Migration: 999_drop_baseline_tables.sql
-- Description: 删除基线表和相关存储过程
-- Date: 2025-11-07
-- Reason: 质量检查功能已删除，基线表不再使用
-- Archive: _archive/baseline_feature_20251107/
-- ============================================================================

-- 设置客户端编码
SET client_encoding = 'UTF8';

-- 开始事务
BEGIN;

-- ============================================================================
-- 1. 删除存储过程
-- ============================================================================

-- 1.1 删除 sp_refresh_metric_rule_auto_baseline 存储过程
DO $$
BEGIN
    DROP PROCEDURE IF EXISTS api.sp_refresh_metric_rule_auto_baseline(
        p_start TIMESTAMPTZ,
        p_end TIMESTAMPTZ,
        p_station_id TEXT,
        p_device_id TEXT,
        p_ensure_rows BOOLEAN,
        p_method TEXT
    ) CASCADE;
    RAISE NOTICE '✓ 已删除存储过程: api.sp_refresh_metric_rule_auto_baseline';
END $$;

-- 1.2 删除 sp_refresh_metric_rule_auto_baseline_win 存储过程
DO $$
BEGIN
    DROP PROCEDURE IF EXISTS api.sp_refresh_metric_rule_auto_baseline_win(
        p_start TIMESTAMPTZ,
        p_end TIMESTAMPTZ,
        p_station_id TEXT,
        p_device_id TEXT,
        p_ensure_rows BOOLEAN,
        p_method TEXT
    ) CASCADE;
    RAISE NOTICE '✓ 已删除存储过程: api.sp_refresh_metric_rule_auto_baseline_win';
END $$;

-- ============================================================================
-- 2. 删除表
-- ============================================================================

-- 2.1 删除 metric_rule_auto_baseline_shadow 表
DO $$
BEGIN
    DROP TABLE IF EXISTS public.metric_rule_auto_baseline_shadow CASCADE;
    RAISE NOTICE '✓ 已删除表: public.metric_rule_auto_baseline_shadow';
END $$;

-- 2.2 删除 metric_rule_auto_baseline 表
DO $$
BEGIN
    DROP TABLE IF EXISTS public.metric_rule_auto_baseline CASCADE;
    RAISE NOTICE '✓ 已删除表: public.metric_rule_auto_baseline';
END $$;

-- ============================================================================
-- 3. 验证删除结果
-- ============================================================================

-- 3.1 验证表已删除
DO $$
DECLARE
    v_table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_name IN ('metric_rule_auto_baseline', 'metric_rule_auto_baseline_shadow');
    
    IF v_table_count > 0 THEN
        RAISE EXCEPTION '❌ 表删除失败：仍有 % 个表存在', v_table_count;
    ELSE
        RAISE NOTICE '✓ 验证通过：所有表已删除';
    END IF;
END $$;

-- 3.2 验证存储过程已删除
DO $$
DECLARE
    v_proc_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_proc_count
    FROM information_schema.routines
    WHERE routine_schema = 'api'
      AND routine_name IN ('sp_refresh_metric_rule_auto_baseline', 'sp_refresh_metric_rule_auto_baseline_win');
    
    IF v_proc_count > 0 THEN
        RAISE EXCEPTION '❌ 存储过程删除失败：仍有 % 个存储过程存在', v_proc_count;
    ELSE
        RAISE NOTICE '✓ 验证通过：所有存储过程已删除';
    END IF;
END $$;

-- ============================================================================
-- 4. 提交事务
-- ============================================================================

COMMIT;

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE '✓ 基线表删除完成';
    RAISE NOTICE '  - 已删除 2 个表';
    RAISE NOTICE '  - 已删除 2 个存储过程';
    RAISE NOTICE '  - 归档位置: _archive/baseline_feature_20251107/';
    RAISE NOTICE '========================================';
END $$;

