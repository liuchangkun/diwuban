\encoding UTF8
SET client_encoding = 'UTF8';

-- =====================================================================
-- 迁移脚本: 108_fix_calculation_parameters_metric_key_fk.sql
-- 用途: 修改 calculation_parameters 表的 metric_key 外键约束
-- 创建日期: 2025-11-14
-- 依赖: calculation_parameters 表和 dim_metric_config 表已存在
-- 理由: 防止 dim_metric_config 表被清空时级联删除 calculation_parameters 表
-- 修订说明:
--   1. 将 metric_key 外键的 ON DELETE CASCADE 改为 ON DELETE RESTRICT
--   2. 保护 calculation_parameters 表中的优化参数不被意外删除
--   3. 保留 device_id 和 station_id 的 CASCADE 删除规则（业务需要）
--   4. 保留 method_id 的 NO ACTION 删除规则（已有设计）
-- =====================================================================

BEGIN;

-- ========== 步骤1: 检查当前外键约束状态 ==========

DO $$
DECLARE
    v_current_delete_rule TEXT;
BEGIN
    -- 查询当前 metric_key 外键的删除规则
    SELECT rc.delete_rule INTO v_current_delete_rule
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.referential_constraints AS rc
        ON rc.constraint_name = tc.constraint_name
        AND rc.constraint_schema = tc.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_name = 'calculation_parameters'
        AND tc.constraint_name = 'calculation_parameters_metric_key_fkey'
        AND tc.table_schema = 'public';
    
    IF v_current_delete_rule IS NULL THEN
        RAISE NOTICE '⚠️ 未找到 calculation_parameters_metric_key_fkey 外键约束';
    ELSE
        RAISE NOTICE '📋 当前 metric_key 外键的删除规则: %', v_current_delete_rule;
        IF v_current_delete_rule = 'CASCADE' THEN
            RAISE NOTICE '⚠️ 当前使用 CASCADE 删除规则，将修改为 RESTRICT';
        ELSIF v_current_delete_rule = 'RESTRICT' THEN
            RAISE NOTICE '✅ 已经是 RESTRICT 删除规则，无需修改';
        END IF;
    END IF;
END $$;

-- ========== 步骤2: 删除现有的 metric_key 外键约束 ==========

DO $$
BEGIN
    ALTER TABLE public.calculation_parameters
    DROP CONSTRAINT IF EXISTS calculation_parameters_metric_key_fkey;

    RAISE NOTICE '✅ 已删除现有的 metric_key 外键约束';
END $$;

-- ========== 步骤3: 重新创建外键约束（使用 RESTRICT） ==========

DO $$
BEGIN
    -- 检查外键是否已存在
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'calculation_parameters_metric_key_fkey'
            AND table_name = 'calculation_parameters'
            AND table_schema = 'public'
    ) THEN
        -- 添加外键约束，使用 ON DELETE RESTRICT
        ALTER TABLE public.calculation_parameters
        ADD CONSTRAINT calculation_parameters_metric_key_fkey
        FOREIGN KEY (metric_key)
        REFERENCES public.dim_metric_config(metric_key)
        ON UPDATE CASCADE
        ON DELETE RESTRICT;
        
        RAISE NOTICE '✅ 成功创建 metric_key 外键约束';
        RAISE NOTICE '   - ON UPDATE CASCADE: metric_key 变化时自动更新';
        RAISE NOTICE '   - ON DELETE RESTRICT: 删除指标前必须先删除依赖的参数';
    ELSE
        RAISE NOTICE '⚠️ metric_key 外键约束已存在，跳过创建';
    END IF;
END $$;

-- ========== 步骤4: 验证修改结果 ==========

DO $$
DECLARE
    v_metric_key_delete_rule TEXT;
    v_device_id_delete_rule TEXT;
    v_station_id_delete_rule TEXT;
    v_method_id_delete_rule TEXT;
BEGIN
    -- 查询所有外键的删除规则
    SELECT 
        MAX(CASE WHEN tc.constraint_name = 'calculation_parameters_metric_key_fkey' THEN rc.delete_rule END),
        MAX(CASE WHEN tc.constraint_name = 'calculation_parameters_device_id_fkey' THEN rc.delete_rule END),
        MAX(CASE WHEN tc.constraint_name = 'calculation_parameters_station_id_fkey' THEN rc.delete_rule END),
        MAX(CASE WHEN tc.constraint_name = 'calculation_parameters_method_id_fkey' THEN rc.delete_rule END)
    INTO v_metric_key_delete_rule, v_device_id_delete_rule, v_station_id_delete_rule, v_method_id_delete_rule
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.referential_constraints AS rc
        ON rc.constraint_name = tc.constraint_name
        AND rc.constraint_schema = tc.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_name = 'calculation_parameters'
        AND tc.table_schema = 'public';
    
    -- 验证 metric_key 外键
    IF v_metric_key_delete_rule = 'RESTRICT' THEN
        RAISE NOTICE '✅ metric_key 外键删除规则验证通过: RESTRICT';
    ELSE
        RAISE EXCEPTION '❌ metric_key 外键删除规则验证失败: 预期 RESTRICT，实际 %', v_metric_key_delete_rule;
    END IF;
    
    -- 验证 device_id 外键（应保持 CASCADE）
    IF v_device_id_delete_rule = 'CASCADE' THEN
        RAISE NOTICE '✅ device_id 外键删除规则验证通过: CASCADE（未修改）';
    ELSE
        RAISE WARNING '⚠️ device_id 外键删除规则异常: 预期 CASCADE，实际 %', v_device_id_delete_rule;
    END IF;
    
    -- 验证 station_id 外键（应保持 CASCADE）
    IF v_station_id_delete_rule = 'CASCADE' THEN
        RAISE NOTICE '✅ station_id 外键删除规则验证通过: CASCADE（未修改）';
    ELSE
        RAISE WARNING '⚠️ station_id 外键删除规则异常: 预期 CASCADE，实际 %', v_station_id_delete_rule;
    END IF;
    
    -- 验证 method_id 外键（应保持 NO ACTION）
    IF v_method_id_delete_rule = 'NO ACTION' THEN
        RAISE NOTICE '✅ method_id 外键删除规则验证通过: NO ACTION（未修改）';
    ELSE
        RAISE WARNING '⚠️ method_id 外键删除规则异常: 预期 NO ACTION，实际 %', v_method_id_delete_rule;
    END IF;
END $$;

COMMIT;

-- ========== 最终验证查询 ==========

-- 显示所有外键约束的详细信息
SELECT 
    tc.constraint_name AS 约束名,
    tc.table_name AS 表名,
    kcu.column_name AS 列名,
    ccu.table_name AS 引用表名,
    ccu.column_name AS 引用列名,
    rc.update_rule AS 更新规则,
    rc.delete_rule AS 删除规则
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
JOIN information_schema.referential_constraints AS rc
    ON rc.constraint_name = tc.constraint_name
    AND rc.constraint_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name = 'calculation_parameters'
    AND tc.table_schema = 'public'
ORDER BY tc.constraint_name;

