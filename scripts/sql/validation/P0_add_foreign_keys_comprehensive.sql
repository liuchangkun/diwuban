-- =====================================================
-- P0优先级：为配置表添加缺失的外键约束（综合版）
-- =====================================================
-- 文件：scripts/sql/validation/P0_add_foreign_keys_comprehensive.sql
-- 用途：为缺少外键约束的配置表添加外键，确保数据完整性
-- 优先级：P0（立即执行）
-- 影响表：calculation_validation_config, device_running_thresholds
-- 创建日期：2025-10-27
-- =====================================================

BEGIN;

-- =====================================================
-- 1. calculation_validation_config - 为 metric_key 添加外键
-- =====================================================

-- 步骤1：数据完整性验证
DO $$
DECLARE
    v_orphan_count INTEGER;
    v_orphan_keys TEXT;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE '1. calculation_validation_config';
    RAISE NOTICE '========================================';

    -- 检查是否存在孤立记录（metric_key 不在 dim_metric_config 中）
    SELECT COUNT(*)
    INTO v_orphan_count
    FROM calculation_validation_config cvc
    WHERE NOT EXISTS (
        SELECT 1
        FROM dim_metric_config dmc
        WHERE dmc.metric_key = cvc.metric_key
    );

    IF v_orphan_count > 0 THEN
        RAISE WARNING '发现 % 条孤立记录（metric_key 不在 dim_metric_config 中）', v_orphan_count;

        -- 获取孤立记录的详细信息
        SELECT string_agg(DISTINCT metric_key, ', ')
        INTO v_orphan_keys
        FROM (
            SELECT cvc.metric_key
            FROM calculation_validation_config cvc
            WHERE NOT EXISTS (
                SELECT 1
                FROM dim_metric_config dmc
                WHERE dmc.metric_key = cvc.metric_key
            )
            LIMIT 10
        ) sub;

        RAISE NOTICE '孤立记录详情: %', v_orphan_keys;
        RAISE EXCEPTION '存在孤立记录，无法添加外键约束。请先清理或修复这些记录。';
    ELSE
        RAISE NOTICE '✅ 数据完整性验证通过（无孤立记录）';
    END IF;
END $$;

-- 步骤2：添加外键约束
DO $$
BEGIN
    -- 检查外键是否已存在
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'calculation_validation_config_metric_key_fkey'
            AND table_name = 'calculation_validation_config'
            AND table_schema = 'public'
    ) THEN
        -- 添加外键约束
        ALTER TABLE calculation_validation_config
        ADD CONSTRAINT calculation_validation_config_metric_key_fkey
        FOREIGN KEY (metric_key)
        REFERENCES dim_metric_config(metric_key)
        ON UPDATE CASCADE
        ON DELETE CASCADE;
        
        RAISE NOTICE '✅ 成功为 calculation_validation_config.metric_key 添加外键约束';
    ELSE
        RAISE NOTICE '⚠️ calculation_validation_config.metric_key 的外键约束已存在，跳过';
    END IF;
END $$;

-- 步骤3：验证外键约束
DO $$
DECLARE
    v_constraint_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO v_constraint_count
    FROM information_schema.table_constraints
    WHERE constraint_name = 'calculation_validation_config_metric_key_fkey'
        AND table_name = 'calculation_validation_config'
        AND table_schema = 'public';
    
    IF v_constraint_count = 1 THEN
        RAISE NOTICE '✅ 外键约束验证成功';
    ELSE
        RAISE EXCEPTION '❌ 外键约束验证失败';
    END IF;
END $$;

-- =====================================================
-- 2. device_running_thresholds - 为 device_id 添加外键
-- =====================================================

-- 步骤1：数据完整性验证
DO $$
DECLARE
    v_orphan_count INTEGER;
    v_orphan_ids TEXT;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE '2. device_running_thresholds';
    RAISE NOTICE '========================================';

    -- 检查是否存在孤立记录（device_id 不在 dim_devices 中）
    SELECT COUNT(*)
    INTO v_orphan_count
    FROM device_running_thresholds drt
    WHERE NOT EXISTS (
        SELECT 1
        FROM dim_devices dd
        WHERE dd.id = drt.device_id
    );

    IF v_orphan_count > 0 THEN
        RAISE WARNING '发现 % 条孤立记录（device_id 不在 dim_devices 中）', v_orphan_count;

        -- 获取孤立记录的详细信息
        SELECT string_agg(DISTINCT device_id::TEXT, ', ')
        INTO v_orphan_ids
        FROM (
            SELECT drt.device_id
            FROM device_running_thresholds drt
            WHERE NOT EXISTS (
                SELECT 1
                FROM dim_devices dd
                WHERE dd.id = drt.device_id
            )
            LIMIT 10
        ) sub;

        RAISE NOTICE '孤立记录详情: %', v_orphan_ids;
        RAISE EXCEPTION '存在孤立记录，无法添加外键约束。请先清理或修复这些记录。';
    ELSE
        RAISE NOTICE '✅ 数据完整性验证通过（无孤立记录）';
    END IF;
END $$;

-- 步骤2：添加外键约束
DO $$
BEGIN
    -- 检查外键是否已存在
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'device_running_thresholds_device_id_fkey'
            AND table_name = 'device_running_thresholds'
            AND table_schema = 'public'
    ) THEN
        -- 添加外键约束
        ALTER TABLE device_running_thresholds
        ADD CONSTRAINT device_running_thresholds_device_id_fkey
        FOREIGN KEY (device_id)
        REFERENCES dim_devices(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE;
        
        RAISE NOTICE '✅ 成功为 device_running_thresholds.device_id 添加外键约束';
    ELSE
        RAISE NOTICE '⚠️ device_running_thresholds.device_id 的外键约束已存在，跳过';
    END IF;
END $$;

-- 步骤3：验证外键约束
DO $$
DECLARE
    v_constraint_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO v_constraint_count
    FROM information_schema.table_constraints
    WHERE constraint_name = 'device_running_thresholds_device_id_fkey'
        AND table_name = 'device_running_thresholds'
        AND table_schema = 'public';
    
    IF v_constraint_count = 1 THEN
        RAISE NOTICE '✅ 外键约束验证成功';
    ELSE
        RAISE EXCEPTION '❌ 外键约束验证失败';
    END IF;
END $$;

-- =====================================================
-- 执行摘要
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'P0优先级外键约束添加完成';
    RAISE NOTICE '========================================';
    RAISE NOTICE '已处理的表：';
    RAISE NOTICE '  1. calculation_validation_config';
    RAISE NOTICE '  2. device_running_thresholds';
    RAISE NOTICE '';
    RAISE NOTICE '外键约束详情：';
    RAISE NOTICE '  - calculation_validation_config.metric_key → dim_metric_config.metric_key';
    RAISE NOTICE '  - device_running_thresholds.device_id → dim_devices.id';
    RAISE NOTICE '  - 级联规则：ON UPDATE CASCADE ON DELETE CASCADE';
    RAISE NOTICE '';
    RAISE NOTICE '下一步：';
    RAISE NOTICE '  1. 执行 P1 优先级脚本（P1_add_foreign_keys_comprehensive.sql）';
    RAISE NOTICE '  2. 验证外键约束是否正常工作';
    RAISE NOTICE '  3. 测试 ID 更新时的级联行为';
    RAISE NOTICE '========================================';
END $$;

COMMIT;

-- =====================================================
-- 验证查询（可选）
-- =====================================================

-- 查询所有外键约束
-- SELECT 
--     tc.table_name AS 源表名,
--     kcu.column_name AS 源列名,
--     ccu.table_name AS 目标表名,
--     ccu.column_name AS 目标列名,
--     rc.update_rule AS UPDATE规则,
--     rc.delete_rule AS DELETE规则
-- FROM information_schema.table_constraints AS tc 
-- JOIN information_schema.key_column_usage AS kcu
--     ON tc.constraint_name = kcu.constraint_name
-- JOIN information_schema.constraint_column_usage AS ccu
--     ON ccu.constraint_name = tc.constraint_name
-- JOIN information_schema.referential_constraints AS rc
--     ON rc.constraint_name = tc.constraint_name
-- WHERE tc.constraint_type = 'FOREIGN KEY'
--     AND tc.table_name IN ('calculation_validation_config', 'device_running_thresholds')
--     AND tc.table_schema = 'public';

-- =====================================================
-- 文档结束
-- =====================================================

