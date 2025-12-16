-- =====================================================
-- P0优先级：为 dim_metric_config 相关配置表添加外键约束
-- =====================================================
-- 文件：scripts/sql/validation/P0_add_foreign_keys_metric_config.sql
-- 用途：为缺少外键约束的配置表添加外键，确保数据完整性
-- 优先级：P0（立即执行）
-- 影响表：calculation_validation_config
-- 创建日期：2025-10-27
-- =====================================================

BEGIN;

-- =====================================================
-- 1. calculation_validation_config
-- =====================================================

-- 步骤1：数据完整性验证
DO $$
DECLARE
    v_orphan_count INTEGER;
BEGIN
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
        
        -- 显示孤立记录的详细信息
        RAISE NOTICE '孤立记录详情：';
        FOR rec IN (
            SELECT DISTINCT cvc.metric_key
            FROM calculation_validation_config cvc
            WHERE NOT EXISTS (
                SELECT 1 
                FROM dim_metric_config dmc 
                WHERE dmc.metric_key = cvc.metric_key
            )
            LIMIT 10
        ) LOOP
            RAISE NOTICE '  - metric_key: %', rec.metric_key;
        END LOOP;
        
        RAISE EXCEPTION '存在孤立记录，无法添加外键约束。请先清理或修复这些记录。';
    ELSE
        RAISE NOTICE '✅ calculation_validation_config 数据完整性验证通过（无孤立记录）';
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
        
        RAISE NOTICE '✅ 成功为 calculation_validation_config 添加外键约束';
    ELSE
        RAISE NOTICE '⚠️ calculation_validation_config 的外键约束已存在，跳过';
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
    RAISE NOTICE '';
    RAISE NOTICE '外键约束详情：';
    RAISE NOTICE '  - calculation_validation_config.metric_key → dim_metric_config.metric_key';
    RAISE NOTICE '  - 级联规则：ON UPDATE CASCADE ON DELETE CASCADE';
    RAISE NOTICE '';
    RAISE NOTICE '下一步：';
    RAISE NOTICE '  1. 执行 P1 优先级脚本（P1_add_foreign_keys_metric_config.sql）';
    RAISE NOTICE '  2. 验证外键约束是否正常工作';
    RAISE NOTICE '  3. 测试 metric_key 更新时的级联行为';
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
--     AND tc.table_name = 'calculation_validation_config'
--     AND tc.table_schema = 'public';

-- =====================================================
-- 测试级联更新（可选，仅用于测试环境）
-- =====================================================

-- 警告：以下测试仅用于测试环境，不要在生产环境执行！

-- 测试1：验证级联更新
-- BEGIN;
-- 
-- -- 创建测试数据
-- INSERT INTO dim_metric_config (metric_key, unit, description)
-- VALUES ('test_metric_cascade', 'test_unit', 'Test metric for cascade')
-- ON CONFLICT (metric_key) DO NOTHING;
-- 
-- INSERT INTO calculation_validation_config (metric_key, validator_type, params, priority, is_enabled)
-- VALUES ('test_metric_cascade', 'range', '{"min": 0, "max": 100}'::jsonb, 100, TRUE)
-- ON CONFLICT DO NOTHING;
-- 
-- -- 更新 metric_key（测试级联更新）
-- UPDATE dim_metric_config
-- SET metric_key = 'test_metric_cascade_updated'
-- WHERE metric_key = 'test_metric_cascade';
-- 
-- -- 验证级联更新是否成功
-- SELECT 
--     CASE 
--         WHEN EXISTS (
--             SELECT 1 
--             FROM calculation_validation_config 
--             WHERE metric_key = 'test_metric_cascade_updated'
--         ) THEN '✅ 级联更新成功'
--         ELSE '❌ 级联更新失败'
--     END AS 测试结果;
-- 
-- -- 清理测试数据
-- DELETE FROM dim_metric_config WHERE metric_key = 'test_metric_cascade_updated';
-- 
-- ROLLBACK;

-- =====================================================
-- 测试级联删除（可选，仅用于测试环境）
-- =====================================================

-- 测试2：验证级联删除
-- BEGIN;
-- 
-- -- 创建测试数据
-- INSERT INTO dim_metric_config (metric_key, unit, description)
-- VALUES ('test_metric_delete', 'test_unit', 'Test metric for delete')
-- ON CONFLICT (metric_key) DO NOTHING;
-- 
-- INSERT INTO calculation_validation_config (metric_key, validator_type, params, priority, is_enabled)
-- VALUES ('test_metric_delete', 'range', '{"min": 0, "max": 100}'::jsonb, 100, TRUE)
-- ON CONFLICT DO NOTHING;
-- 
-- -- 删除 metric_key（测试级联删除）
-- DELETE FROM dim_metric_config WHERE metric_key = 'test_metric_delete';
-- 
-- -- 验证级联删除是否成功
-- SELECT 
--     CASE 
--         WHEN NOT EXISTS (
--             SELECT 1 
--             FROM calculation_validation_config 
--             WHERE metric_key = 'test_metric_delete'
--         ) THEN '✅ 级联删除成功'
--         ELSE '❌ 级联删除失败'
--     END AS 测试结果;
-- 
-- ROLLBACK;

-- =====================================================
-- 文档结束
-- =====================================================

