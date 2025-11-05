\encoding UTF8
SET client_encoding = 'UTF8';

-- =====================================================================
-- 迁移脚本: 067_add_fusion_threshold_field.sql
-- 用途: 为device_running_thresholds表添加fusion_threshold字段
-- 创建日期: 2025-11-01
-- 依赖: 060_alter_device_running_thresholds_phase1.sql
-- 说明: 
--   1. 添加 fusion_threshold 字段，支持每个设备独立配置融合阈值
--   2. 默认值0.6（与之前硬编码值一致）
--   3. 约束范围0.3-1.0（防止不合理的阈值）
-- =====================================================================

BEGIN;

-- ========== 1. 添加 fusion_threshold 字段 ==========

ALTER TABLE public.device_running_thresholds
ADD COLUMN IF NOT EXISTS fusion_threshold DOUBLE PRECISION DEFAULT 0.6;

COMMENT ON COLUMN public.device_running_thresholds.fusion_threshold IS 
  '加权融合阈值(0.3-1.0): 当融合分数>=此阈值时判断为运行。默认0.6，建议范围0.6-0.8。用于加权融合算法（use_weighted_fusion=TRUE时生效）';

-- ========== 2. 添加约束 ==========

ALTER TABLE public.device_running_thresholds
ADD CONSTRAINT chk_fusion_threshold_range
  CHECK (fusion_threshold >= 0.3 AND fusion_threshold <= 1.0);

COMMIT;

-- =====================================================================
-- 验证脚本
-- =====================================================================

-- 验证字段已创建
DO $$
DECLARE
    v_column_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'device_running_thresholds'
          AND column_name = 'fusion_threshold'
    ) INTO v_column_exists;
    
    IF v_column_exists THEN
        RAISE NOTICE '[验证成功] fusion_threshold 字段已创建';
    ELSE
        RAISE EXCEPTION '[验证失败] fusion_threshold 字段未创建';
    END IF;
END$$;

-- 验证约束已创建
DO $$
DECLARE
    v_constraint_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.check_constraints
        WHERE constraint_schema = 'public'
          AND constraint_name = 'chk_fusion_threshold_range'
    ) INTO v_constraint_exists;
    
    IF v_constraint_exists THEN
        RAISE NOTICE '[验证成功] chk_fusion_threshold_range 约束已创建';
    ELSE
        RAISE EXCEPTION '[验证失败] chk_fusion_threshold_range 约束未创建';
    END IF;
END$$;

-- 显示字段信息
SELECT 
    column_name,
    data_type,
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'device_running_thresholds'
  AND column_name = 'fusion_threshold';

-- 显示约束信息
SELECT 
    constraint_name,
    check_clause
FROM information_schema.check_constraints
WHERE constraint_schema = 'public'
  AND constraint_name = 'chk_fusion_threshold_range';

-- 测试约束（应该失败）
DO $$
BEGIN
    -- 测试下限（应该失败）
    BEGIN
        INSERT INTO public.device_running_thresholds(device_id, fusion_threshold)
        VALUES (-999999, 0.2);
        RAISE EXCEPTION '[约束测试失败] 应该拒绝 fusion_threshold=0.2';
    EXCEPTION
        WHEN check_violation THEN
            RAISE NOTICE '[约束测试成功] 正确拒绝了 fusion_threshold=0.2（低于下限0.3）';
            ROLLBACK;
    END;
    
    -- 测试上限（应该失败）
    BEGIN
        INSERT INTO public.device_running_thresholds(device_id, fusion_threshold)
        VALUES (-999998, 1.1);
        RAISE EXCEPTION '[约束测试失败] 应该拒绝 fusion_threshold=1.1';
    EXCEPTION
        WHEN check_violation THEN
            RAISE NOTICE '[约束测试成功] 正确拒绝了 fusion_threshold=1.1（超过上限1.0）';
            ROLLBACK;
    END;
END$$;

RAISE NOTICE '[迁移完成] 067_add_fusion_threshold_field.sql 执行成功';

