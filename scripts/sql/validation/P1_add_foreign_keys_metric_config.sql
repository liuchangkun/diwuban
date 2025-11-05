-- =====================================================
-- P1优先级：为 dim_metric_config 相关配置表添加外键约束
-- =====================================================
-- 文件：scripts/sql/validation/P1_add_foreign_keys_metric_config.sql
-- 用途：为缺少外键约束的配置表添加外键，确保数据完整性
-- 优先级：P1（1个月内）
-- 影响表：metric_capability_policy, metric_quality_rules, metric_rule_auto_baseline, metric_anomaly_strategy
-- 创建日期：2025-10-27
-- =====================================================

BEGIN;

-- =====================================================
-- 1. metric_capability_policy
-- =====================================================

-- 步骤1：数据完整性验证
DO $$
DECLARE
    v_orphan_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO v_orphan_count
    FROM metric_capability_policy mcp
    WHERE NOT EXISTS (
        SELECT 1 
        FROM dim_metric_config dmc 
        WHERE dmc.metric_key = mcp.metric_key
    );
    
    IF v_orphan_count > 0 THEN
        RAISE WARNING '发现 % 条孤立记录（metric_key 不在 dim_metric_config 中）', v_orphan_count;
        RAISE EXCEPTION '存在孤立记录，无法添加外键约束。请先清理或修复这些记录。';
    ELSE
        RAISE NOTICE '✅ metric_capability_policy 数据完整性验证通过';
    END IF;
END $$;

-- 步骤2：添加外键约束
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'metric_capability_policy_metric_key_fkey'
            AND table_name = 'metric_capability_policy'
    ) THEN
        ALTER TABLE metric_capability_policy
        ADD CONSTRAINT metric_capability_policy_metric_key_fkey
        FOREIGN KEY (metric_key)
        REFERENCES dim_metric_config(metric_key)
        ON UPDATE CASCADE
        ON DELETE CASCADE;
        
        RAISE NOTICE '✅ 成功为 metric_capability_policy 添加外键约束';
    ELSE
        RAISE NOTICE '⚠️ metric_capability_policy 的外键约束已存在，跳过';
    END IF;
END $$;

-- =====================================================
-- 2. metric_quality_rules
-- =====================================================

-- 步骤1：数据完整性验证
DO $$
DECLARE
    v_orphan_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO v_orphan_count
    FROM metric_quality_rules mqr
    WHERE NOT EXISTS (
        SELECT 1 
        FROM dim_metric_config dmc 
        WHERE dmc.id = mqr.metric_id
    );
    
    IF v_orphan_count > 0 THEN
        RAISE WARNING '发现 % 条孤立记录（metric_id 不在 dim_metric_config 中）', v_orphan_count;
        RAISE EXCEPTION '存在孤立记录，无法添加外键约束。请先清理或修复这些记录。';
    ELSE
        RAISE NOTICE '✅ metric_quality_rules 数据完整性验证通过';
    END IF;
END $$;

-- 步骤2：添加外键约束
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'metric_quality_rules_metric_id_fkey'
            AND table_name = 'metric_quality_rules'
    ) THEN
        ALTER TABLE metric_quality_rules
        ADD CONSTRAINT metric_quality_rules_metric_id_fkey
        FOREIGN KEY (metric_id)
        REFERENCES dim_metric_config(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE;
        
        RAISE NOTICE '✅ 成功为 metric_quality_rules 添加外键约束';
    ELSE
        RAISE NOTICE '⚠️ metric_quality_rules 的外键约束已存在，跳过';
    END IF;
END $$;

-- =====================================================
-- 3. metric_rule_auto_baseline
-- =====================================================

-- 步骤1：数据完整性验证
DO $$
DECLARE
    v_orphan_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO v_orphan_count
    FROM metric_rule_auto_baseline mrab
    WHERE NOT EXISTS (
        SELECT 1 
        FROM dim_metric_config dmc 
        WHERE dmc.id = mrab.metric_id
    );
    
    IF v_orphan_count > 0 THEN
        RAISE WARNING '发现 % 条孤立记录（metric_id 不在 dim_metric_config 中）', v_orphan_count;
        RAISE EXCEPTION '存在孤立记录，无法添加外键约束。请先清理或修复这些记录。';
    ELSE
        RAISE NOTICE '✅ metric_rule_auto_baseline 数据完整性验证通过';
    END IF;
END $$;

-- 步骤2：添加外键约束
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'metric_rule_auto_baseline_metric_id_fkey'
            AND table_name = 'metric_rule_auto_baseline'
    ) THEN
        ALTER TABLE metric_rule_auto_baseline
        ADD CONSTRAINT metric_rule_auto_baseline_metric_id_fkey
        FOREIGN KEY (metric_id)
        REFERENCES dim_metric_config(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE;
        
        RAISE NOTICE '✅ 成功为 metric_rule_auto_baseline 添加外键约束';
    ELSE
        RAISE NOTICE '⚠️ metric_rule_auto_baseline 的外键约束已存在，跳过';
    END IF;
END $$;

-- =====================================================
-- 4. metric_anomaly_strategy
-- =====================================================

-- 步骤1：数据完整性验证
DO $$
DECLARE
    v_orphan_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO v_orphan_count
    FROM metric_anomaly_strategy mas
    WHERE NOT EXISTS (
        SELECT 1 
        FROM dim_metric_config dmc 
        WHERE dmc.id = mas.metric_id
    );
    
    IF v_orphan_count > 0 THEN
        RAISE WARNING '发现 % 条孤立记录（metric_id 不在 dim_metric_config 中）', v_orphan_count;
        RAISE EXCEPTION '存在孤立记录，无法添加外键约束。请先清理或修复这些记录。';
    ELSE
        RAISE NOTICE '✅ metric_anomaly_strategy 数据完整性验证通过';
    END IF;
END $$;

-- 步骤2：添加外键约束
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'metric_anomaly_strategy_metric_id_fkey'
            AND table_name = 'metric_anomaly_strategy'
    ) THEN
        ALTER TABLE metric_anomaly_strategy
        ADD CONSTRAINT metric_anomaly_strategy_metric_id_fkey
        FOREIGN KEY (metric_id)
        REFERENCES dim_metric_config(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE;
        
        RAISE NOTICE '✅ 成功为 metric_anomaly_strategy 添加外键约束';
    ELSE
        RAISE NOTICE '⚠️ metric_anomaly_strategy 的外键约束已存在，跳过';
    END IF;
END $$;

-- =====================================================
-- 执行摘要
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'P1优先级外键约束添加完成';
    RAISE NOTICE '========================================';
    RAISE NOTICE '已处理的表：';
    RAISE NOTICE '  1. metric_capability_policy';
    RAISE NOTICE '  2. metric_quality_rules';
    RAISE NOTICE '  3. metric_rule_auto_baseline';
    RAISE NOTICE '  4. metric_anomaly_strategy';
    RAISE NOTICE '';
    RAISE NOTICE '外键约束详情：';
    RAISE NOTICE '  - metric_capability_policy.metric_key → dim_metric_config.metric_key';
    RAISE NOTICE '  - metric_quality_rules.metric_id → dim_metric_config.id';
    RAISE NOTICE '  - metric_rule_auto_baseline.metric_id → dim_metric_config.id';
    RAISE NOTICE '  - metric_anomaly_strategy.metric_id → dim_metric_config.id';
    RAISE NOTICE '  - 级联规则：ON UPDATE CASCADE ON DELETE CASCADE';
    RAISE NOTICE '';
    RAISE NOTICE '下一步：';
    RAISE NOTICE '  1. 验证外键约束是否正常工作';
    RAISE NOTICE '  2. 测试 metric_id/metric_key 更新时的级联行为';
    RAISE NOTICE '  3. 监控系统运行情况';
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
--     AND tc.table_name IN (
--         'metric_capability_policy',
--         'metric_quality_rules',
--         'metric_rule_auto_baseline',
--         'metric_anomaly_strategy'
--     )
--     AND tc.table_schema = 'public';

-- =====================================================
-- 文档结束
-- =====================================================

