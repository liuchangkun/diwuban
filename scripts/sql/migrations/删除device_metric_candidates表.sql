-- ============================================================================
-- 删除 device_metric_candidates 表
-- ============================================================================
-- 创建日期: 2025-01-17
-- 说明: 删除未使用的 device_metric_candidates 表
-- 原因: 该表从未被使用，已被 metric_capability_policy 表替代
-- 风险等级: 极低（无外键依赖、无代码引用、无数据）
-- ============================================================================

-- 步骤1: 验证表当前状态
DO $$
BEGIN
  RAISE NOTICE '=== 验证表当前状态 ===';
  
  -- 检查表是否存在
  IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'device_metric_candidates') THEN
    RAISE NOTICE '✓ 表 device_metric_candidates 存在';
  ELSE
    RAISE NOTICE '✗ 表 device_metric_candidates 不存在';
  END IF;
END $$;

-- 步骤2: 检查外键依赖
SELECT
  '外键依赖检查' AS check_type,
  tc.table_name AS referencing_table,
  kcu.column_name AS referencing_column,
  ccu.table_name AS referenced_table,
  ccu.column_name AS referenced_column
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND ccu.table_name = 'device_metric_candidates';
-- 预期结果: 0 rows（无外键依赖）

-- 步骤3: 检查表的行数
SELECT 
  '数据行数检查' AS check_type,
  COUNT(*) as row_count 
FROM device_metric_candidates;
-- 预期结果: 0 rows

-- 步骤4: 删除表（包含级联删除外键约束）
DROP TABLE IF EXISTS public.device_metric_candidates CASCADE;

-- 步骤5: 验证删除成功
DO $$
BEGIN
  RAISE NOTICE '=== 验证删除结果 ===';
  
  -- 检查表是否已删除
  IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'device_metric_candidates') THEN
    RAISE NOTICE '✓ 表 device_metric_candidates 已成功删除';
  ELSE
    RAISE NOTICE '✗ 表 device_metric_candidates 仍然存在';
  END IF;
END $$;

-- 步骤6: 检查外键约束残留
SELECT
  '外键约束残留检查' AS check_type,
  constraint_name 
FROM information_schema.table_constraints 
WHERE constraint_name LIKE '%device_metric_candidates%';
-- 预期结果: 0 rows（无残留约束）

-- 步骤7: 检查索引残留
SELECT
  '索引残留检查' AS check_type,
  indexname 
FROM pg_indexes 
WHERE indexname LIKE '%device_metric_candidates%';
-- 预期结果: 0 rows（无残留索引）

-- ============================================================================
-- 执行完成
-- ============================================================================
-- 预期结果:
-- 1. 表 device_metric_candidates 已删除
-- 2. 无外键约束残留
-- 3. 无索引残留
-- ============================================================================

