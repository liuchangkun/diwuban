-- =====================================================
-- P1优先级：为配置表添加缺失的外键约束（综合版）
-- =====================================================
-- 文件：scripts/sql/validation/P1_add_foreign_keys_comprehensive.sql
-- 用途：为缺少外键约束的配置表添加外键，确保数据完整性
-- 优先级：P1（1个月内）
-- 影响表：metric_anomaly_strategy, metric_quality_rules, metric_rule_auto_baseline, metric_capability_policy
-- 创建日期：2025-10-27
-- =====================================================

BEGIN;

-- =====================================================
-- 1. metric_anomaly_strategy - 添加3个外键
-- =====================================================

-- 步骤1：数据完整性验证
DO $$
DECLARE
    v_orphan_station INTEGER;
    v_orphan_device INTEGER;
    v_orphan_metric INTEGER;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE '1. metric_anomaly_strategy';
    RAISE NOTICE '========================================';
    
    -- 检查 station_id 孤立记录
    SELECT COUNT(*)
    INTO v_orphan_station
    FROM metric_anomaly_strategy mas
    WHERE mas.station_id IS NOT NULL
      AND NOT EXISTS (
        SELECT 1 FROM dim_stations ds WHERE ds.id = mas.station_id
    );
    
    -- 检查 device_id 孤立记录
    SELECT COUNT(*)
    INTO v_orphan_device
    FROM metric_anomaly_strategy mas
    WHERE mas.device_id IS NOT NULL
      AND NOT EXISTS (
        SELECT 1 FROM dim_devices dd WHERE dd.id = mas.device_id
    );
    
    -- 检查 metric_id 孤立记录
    SELECT COUNT(*)
    INTO v_orphan_metric
    FROM metric_anomaly_strategy mas
    WHERE mas.metric_id IS NOT NULL
      AND NOT EXISTS (
        SELECT 1 FROM dim_metric_config dmc WHERE dmc.id = mas.metric_id
    );
    
    IF v_orphan_station > 0 OR v_orphan_device > 0 OR v_orphan_metric > 0 THEN
        RAISE WARNING '发现孤立记录：station_id=%条, device_id=%条, metric_id=%条', 
            v_orphan_station, v_orphan_device, v_orphan_metric;
        RAISE EXCEPTION '存在孤立记录，无法添加外键约束。请先清理或修复这些记录。';
    ELSE
        RAISE NOTICE '✅ 数据完整性验证通过（无孤立记录）';
    END IF;
END $$;

-- 步骤2：添加外键约束
DO $$
BEGIN
    -- 添加 station_id 外键
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'metric_anomaly_strategy_station_id_fkey'
            AND table_name = 'metric_anomaly_strategy'
    ) THEN
        ALTER TABLE metric_anomaly_strategy
        ADD CONSTRAINT metric_anomaly_strategy_station_id_fkey
        FOREIGN KEY (station_id)
        REFERENCES dim_stations(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE;
        RAISE NOTICE '✅ 成功为 metric_anomaly_strategy.station_id 添加外键约束';
    ELSE
        RAISE NOTICE '⚠️ metric_anomaly_strategy.station_id 的外键约束已存在，跳过';
    END IF;
    
    -- 添加 device_id 外键
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'metric_anomaly_strategy_device_id_fkey'
            AND table_name = 'metric_anomaly_strategy'
    ) THEN
        ALTER TABLE metric_anomaly_strategy
        ADD CONSTRAINT metric_anomaly_strategy_device_id_fkey
        FOREIGN KEY (device_id)
        REFERENCES dim_devices(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE;
        RAISE NOTICE '✅ 成功为 metric_anomaly_strategy.device_id 添加外键约束';
    ELSE
        RAISE NOTICE '⚠️ metric_anomaly_strategy.device_id 的外键约束已存在，跳过';
    END IF;
    
    -- 添加 metric_id 外键
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'metric_anomaly_strategy_metric_id_fkey'
            AND table_name = 'metric_anomaly_strategy'
    ) THEN
        ALTER TABLE metric_anomaly_strategy
        ADD CONSTRAINT metric_anomaly_strategy_metric_id_fkey
        FOREIGN KEY (metric_id)
        REFERENCES dim_metric_config(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE;
        RAISE NOTICE '✅ 成功为 metric_anomaly_strategy.metric_id 添加外键约束';
    ELSE
        RAISE NOTICE '⚠️ metric_anomaly_strategy.metric_id 的外键约束已存在，跳过';
    END IF;
END $$;

-- =====================================================
-- 2. metric_quality_rules - 添加3个外键
-- =====================================================

-- 步骤1：数据完整性验证
DO $$
DECLARE
    v_orphan_station INTEGER;
    v_orphan_device INTEGER;
    v_orphan_metric INTEGER;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE '2. metric_quality_rules';
    RAISE NOTICE '========================================';
    
    -- 检查 station_id 孤立记录
    SELECT COUNT(*)
    INTO v_orphan_station
    FROM metric_quality_rules mqr
    WHERE mqr.station_id IS NOT NULL
      AND NOT EXISTS (
        SELECT 1 FROM dim_stations ds WHERE ds.id = mqr.station_id
    );
    
    -- 检查 device_id 孤立记录
    SELECT COUNT(*)
    INTO v_orphan_device
    FROM metric_quality_rules mqr
    WHERE mqr.device_id IS NOT NULL
      AND NOT EXISTS (
        SELECT 1 FROM dim_devices dd WHERE dd.id = mqr.device_id
    );
    
    -- 检查 metric_id 孤立记录
    SELECT COUNT(*)
    INTO v_orphan_metric
    FROM metric_quality_rules mqr
    WHERE mqr.metric_id IS NOT NULL
      AND NOT EXISTS (
        SELECT 1 FROM dim_metric_config dmc WHERE dmc.id = mqr.metric_id
    );
    
    IF v_orphan_station > 0 OR v_orphan_device > 0 OR v_orphan_metric > 0 THEN
        RAISE WARNING '发现孤立记录：station_id=%条, device_id=%条, metric_id=%条', 
            v_orphan_station, v_orphan_device, v_orphan_metric;
        RAISE EXCEPTION '存在孤立记录，无法添加外键约束。请先清理或修复这些记录。';
    ELSE
        RAISE NOTICE '✅ 数据完整性验证通过（无孤立记录）';
    END IF;
END $$;

-- 步骤2：添加外键约束
DO $$
BEGIN
    -- 添加 station_id 外键
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'metric_quality_rules_station_id_fkey'
            AND table_name = 'metric_quality_rules'
    ) THEN
        ALTER TABLE metric_quality_rules
        ADD CONSTRAINT metric_quality_rules_station_id_fkey
        FOREIGN KEY (station_id)
        REFERENCES dim_stations(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE;
        RAISE NOTICE '✅ 成功为 metric_quality_rules.station_id 添加外键约束';
    ELSE
        RAISE NOTICE '⚠️ metric_quality_rules.station_id 的外键约束已存在，跳过';
    END IF;
    
    -- 添加 device_id 外键
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'metric_quality_rules_device_id_fkey'
            AND table_name = 'metric_quality_rules'
    ) THEN
        ALTER TABLE metric_quality_rules
        ADD CONSTRAINT metric_quality_rules_device_id_fkey
        FOREIGN KEY (device_id)
        REFERENCES dim_devices(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE;
        RAISE NOTICE '✅ 成功为 metric_quality_rules.device_id 添加外键约束';
    ELSE
        RAISE NOTICE '⚠️ metric_quality_rules.device_id 的外键约束已存在，跳过';
    END IF;
    
    -- 添加 metric_id 外键
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'metric_quality_rules_metric_id_fkey'
            AND table_name = 'metric_quality_rules'
    ) THEN
        ALTER TABLE metric_quality_rules
        ADD CONSTRAINT metric_quality_rules_metric_id_fkey
        FOREIGN KEY (metric_id)
        REFERENCES dim_metric_config(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE;
        RAISE NOTICE '✅ 成功为 metric_quality_rules.metric_id 添加外键约束';
    ELSE
        RAISE NOTICE '⚠️ metric_quality_rules.metric_id 的外键约束已存在，跳过';
    END IF;
END $$;

-- =====================================================
-- 3. metric_rule_auto_baseline - 添加3个外键
-- =====================================================

-- 步骤1：数据完整性验证
DO $$
DECLARE
    v_orphan_station INTEGER;
    v_orphan_device INTEGER;
    v_orphan_metric INTEGER;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE '3. metric_rule_auto_baseline';
    RAISE NOTICE '========================================';
    
    -- 检查 station_id 孤立记录
    SELECT COUNT(*)
    INTO v_orphan_station
    FROM metric_rule_auto_baseline mrab
    WHERE mrab.station_id IS NOT NULL
      AND NOT EXISTS (
        SELECT 1 FROM dim_stations ds WHERE ds.id = mrab.station_id
    );
    
    -- 检查 device_id 孤立记录
    SELECT COUNT(*)
    INTO v_orphan_device
    FROM metric_rule_auto_baseline mrab
    WHERE mrab.device_id IS NOT NULL
      AND NOT EXISTS (
        SELECT 1 FROM dim_devices dd WHERE dd.id = mrab.device_id
    );
    
    -- 检查 metric_id 孤立记录
    SELECT COUNT(*)
    INTO v_orphan_metric
    FROM metric_rule_auto_baseline mrab
    WHERE mrab.metric_id IS NOT NULL
      AND NOT EXISTS (
        SELECT 1 FROM dim_metric_config dmc WHERE dmc.id = mrab.metric_id
    );
    
    IF v_orphan_station > 0 OR v_orphan_device > 0 OR v_orphan_metric > 0 THEN
        RAISE WARNING '发现孤立记录：station_id=%条, device_id=%条, metric_id=%条', 
            v_orphan_station, v_orphan_device, v_orphan_metric;
        RAISE EXCEPTION '存在孤立记录，无法添加外键约束。请先清理或修复这些记录。';
    ELSE
        RAISE NOTICE '✅ 数据完整性验证通过（无孤立记录）';
    END IF;
END $$;

-- 步骤2：添加外键约束
DO $$
BEGIN
    -- 添加 station_id 外键
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'metric_rule_auto_baseline_station_id_fkey'
            AND table_name = 'metric_rule_auto_baseline'
    ) THEN
        ALTER TABLE metric_rule_auto_baseline
        ADD CONSTRAINT metric_rule_auto_baseline_station_id_fkey
        FOREIGN KEY (station_id)
        REFERENCES dim_stations(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE;
        RAISE NOTICE '✅ 成功为 metric_rule_auto_baseline.station_id 添加外键约束';
    ELSE
        RAISE NOTICE '⚠️ metric_rule_auto_baseline.station_id 的外键约束已存在，跳过';
    END IF;
    
    -- 添加 device_id 外键
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'metric_rule_auto_baseline_device_id_fkey'
            AND table_name = 'metric_rule_auto_baseline'
    ) THEN
        ALTER TABLE metric_rule_auto_baseline
        ADD CONSTRAINT metric_rule_auto_baseline_device_id_fkey
        FOREIGN KEY (device_id)
        REFERENCES dim_devices(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE;
        RAISE NOTICE '✅ 成功为 metric_rule_auto_baseline.device_id 添加外键约束';
    ELSE
        RAISE NOTICE '⚠️ metric_rule_auto_baseline.device_id 的外键约束已存在，跳过';
    END IF;
    
    -- 添加 metric_id 外键
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'metric_rule_auto_baseline_metric_id_fkey'
            AND table_name = 'metric_rule_auto_baseline'
    ) THEN
        ALTER TABLE metric_rule_auto_baseline
        ADD CONSTRAINT metric_rule_auto_baseline_metric_id_fkey
        FOREIGN KEY (metric_id)
        REFERENCES dim_metric_config(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE;
        RAISE NOTICE '✅ 成功为 metric_rule_auto_baseline.metric_id 添加外键约束';
    ELSE
        RAISE NOTICE '⚠️ metric_rule_auto_baseline.metric_id 的外键约束已存在，跳过';
    END IF;
END $$;

-- =====================================================
-- 4. metric_capability_policy - 添加1个外键
-- =====================================================

-- 步骤1：数据完整性验证
DO $$
DECLARE
    v_orphan_count INTEGER;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE '4. metric_capability_policy';
    RAISE NOTICE '========================================';
    
    SELECT COUNT(*)
    INTO v_orphan_count
    FROM metric_capability_policy mcp
    WHERE NOT EXISTS (
        SELECT 1 FROM dim_metric_config dmc WHERE dmc.metric_key = mcp.metric_key
    );
    
    IF v_orphan_count > 0 THEN
        RAISE WARNING '发现 % 条孤立记录（metric_key 不在 dim_metric_config 中）', v_orphan_count;
        RAISE EXCEPTION '存在孤立记录，无法添加外键约束。请先清理或修复这些记录。';
    ELSE
        RAISE NOTICE '✅ 数据完整性验证通过（无孤立记录）';
    END IF;
END $$;

-- 步骤2：添加外键约束
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'metric_capability_policy_metric_key_fkey'
            AND table_name = 'metric_capability_policy'
    ) THEN
        ALTER TABLE metric_capability_policy
        ADD CONSTRAINT metric_capability_policy_metric_key_fkey
        FOREIGN KEY (metric_key)
        REFERENCES dim_metric_config(metric_key)
        ON UPDATE CASCADE
        ON DELETE CASCADE;
        RAISE NOTICE '✅ 成功为 metric_capability_policy.metric_key 添加外键约束';
    ELSE
        RAISE NOTICE '⚠️ metric_capability_policy.metric_key 的外键约束已存在，跳过';
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
    RAISE NOTICE '  1. metric_anomaly_strategy（3个外键）';
    RAISE NOTICE '  2. metric_quality_rules（3个外键）';
    RAISE NOTICE '  3. metric_rule_auto_baseline（3个外键）';
    RAISE NOTICE '  4. metric_capability_policy（1个外键）';
    RAISE NOTICE '';
    RAISE NOTICE '外键约束详情：';
    RAISE NOTICE '  - metric_anomaly_strategy.station_id → dim_stations.id';
    RAISE NOTICE '  - metric_anomaly_strategy.device_id → dim_devices.id';
    RAISE NOTICE '  - metric_anomaly_strategy.metric_id → dim_metric_config.id';
    RAISE NOTICE '  - metric_quality_rules.station_id → dim_stations.id';
    RAISE NOTICE '  - metric_quality_rules.device_id → dim_devices.id';
    RAISE NOTICE '  - metric_quality_rules.metric_id → dim_metric_config.id';
    RAISE NOTICE '  - metric_rule_auto_baseline.station_id → dim_stations.id';
    RAISE NOTICE '  - metric_rule_auto_baseline.device_id → dim_devices.id';
    RAISE NOTICE '  - metric_rule_auto_baseline.metric_id → dim_metric_config.id';
    RAISE NOTICE '  - metric_capability_policy.metric_key → dim_metric_config.metric_key';
    RAISE NOTICE '  - 级联规则：ON UPDATE CASCADE ON DELETE CASCADE';
    RAISE NOTICE '';
    RAISE NOTICE '下一步：';
    RAISE NOTICE '  1. 更新 prepare_dim 备份机制（添加3个遗漏的表）';
    RAISE NOTICE '  2. 验证外键约束是否正常工作';
    RAISE NOTICE '  3. 监控系统运行情况';
    RAISE NOTICE '========================================';
END $$;

COMMIT;

-- =====================================================
-- 文档结束
-- =====================================================

