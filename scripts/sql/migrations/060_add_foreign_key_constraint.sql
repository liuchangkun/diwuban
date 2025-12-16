\encoding UTF8
SET client_encoding = 'UTF8';

-- =====================================================================
-- 迁移脚本: 060_add_foreign_key_constraint.sql
-- 用途: 为device_running_thresholds表添加外键约束
-- 创建日期: 2025-10-31
-- 依赖: 009_device_running_thresholds.sql
-- 理由: 确保device_id与dim_devices表保持一致，支持级联更新和删除
-- 修订说明:
--   1. 解决维度表ID变化的自适应处理问题
--   2. 防止孤立记录（device_id不存在于dim_devices表）
--   3. 使用ON UPDATE CASCADE自动处理device_id变化
--   4. 使用ON DELETE CASCADE自动清理已删除设备的配置
-- =====================================================================

BEGIN;

-- ========== 步骤1: 检查孤立记录 ==========

DO $$
DECLARE
    v_orphan_count INTEGER;
    v_orphan_devices TEXT;
BEGIN
    -- 统计孤立记录数量
    SELECT COUNT(*) INTO v_orphan_count
    FROM public.device_running_thresholds drt
    LEFT JOIN public.dim_devices d ON d.id = drt.device_id
    WHERE d.id IS NULL;
    
    IF v_orphan_count > 0 THEN
        -- 获取孤立记录的device_id列表
        SELECT STRING_AGG(drt.device_id::TEXT, ', ') INTO v_orphan_devices
        FROM public.device_running_thresholds drt
        LEFT JOIN public.dim_devices d ON d.id = drt.device_id
        WHERE d.id IS NULL;
        
        RAISE WARNING '发现 % 个孤立记录（device_id不存在于dim_devices表）: %', v_orphan_count, v_orphan_devices;
        RAISE EXCEPTION '请先清理孤立记录，再添加外键约束。清理SQL: DELETE FROM device_running_thresholds WHERE device_id IN (%)', v_orphan_devices;
    ELSE
        RAISE NOTICE '✅ 无孤立记录，可以安全添加外键约束';
    END IF;
END $$;

-- ========== 步骤2: 添加外键约束 ==========

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
        ALTER TABLE public.device_running_thresholds
        ADD CONSTRAINT device_running_thresholds_device_id_fkey
        FOREIGN KEY (device_id)
        REFERENCES public.dim_devices(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE;
        
        RAISE NOTICE '✅ 成功为 device_running_thresholds.device_id 添加外键约束';
        RAISE NOTICE '   - ON UPDATE CASCADE: device_id变化时自动更新';
        RAISE NOTICE '   - ON DELETE CASCADE: 设备删除时自动清理配置';
    ELSE
        RAISE NOTICE '⚠️ device_running_thresholds.device_id 的外键约束已存在，跳过';
    END IF;
END $$;

COMMIT;

-- =====================================================================
-- 验证脚本
-- =====================================================================

-- 验证外键约束已创建
DO $$
DECLARE
    v_constraint_exists BOOLEAN;
    v_update_rule TEXT;
    v_delete_rule TEXT;
BEGIN
    -- 检查外键约束是否存在
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'device_running_thresholds_device_id_fkey'
            AND table_name = 'device_running_thresholds'
            AND table_schema = 'public'
    ) INTO v_constraint_exists;
    
    IF v_constraint_exists THEN
        -- 获取级联规则
        SELECT rc.update_rule, rc.delete_rule
        INTO v_update_rule, v_delete_rule
        FROM information_schema.referential_constraints rc
        WHERE rc.constraint_name = 'device_running_thresholds_device_id_fkey'
            AND rc.constraint_schema = 'public';
        
        RAISE NOTICE '[验证成功] 外键约束已存在';
        RAISE NOTICE '  - 约束名: device_running_thresholds_device_id_fkey';
        RAISE NOTICE '  - 更新规则: %', v_update_rule;
        RAISE NOTICE '  - 删除规则: %', v_delete_rule;
        
        -- 验证级联规则
        IF v_update_rule = 'CASCADE' AND v_delete_rule = 'CASCADE' THEN
            RAISE NOTICE '[验证成功] 级联规则正确配置';
        ELSE
            RAISE WARNING '[验证失败] 级联规则不正确，预期: CASCADE/CASCADE，实际: %/%', v_update_rule, v_delete_rule;
        END IF;
    ELSE
        RAISE WARNING '[验证失败] 外键约束不存在';
    END IF;
END $$;

-- 显示外键约束详细信息
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
    AND tc.table_name = 'device_running_thresholds'
    AND tc.table_schema = 'public';

-- =====================================================================
-- 回滚脚本（仅供参考，不自动执行）
-- =====================================================================

-- 如果需要回滚，执行以下SQL:
-- ALTER TABLE public.device_running_thresholds
-- DROP CONSTRAINT IF EXISTS device_running_thresholds_device_id_fkey;

