-- ============================================================================
-- 删除未使用的数据库表
-- 创建时间: 2025-01-17
-- 说明: 删除4个未使用的表，清理数据库结构
-- ============================================================================

-- 1. optimization_history 表
-- 原因: 优化历史已存储在 calculation_parameters.optimization_history 字段（JSONB）
--       独立表从未被使用，表中无数据
DROP TABLE IF EXISTS public.optimization_history CASCADE;

-- 2. metrics_presence_per_second_device_legacy 表
-- 原因: 遗留表，已被新的存在性统计机制替代
DROP TABLE IF EXISTS public.metrics_presence_per_second_device_legacy CASCADE;

-- 3. calculation_validation_config_backup 表
-- 原因: 备份表，临时使用，不再需要
DROP TABLE IF EXISTS public.calculation_validation_config_backup CASCADE;

-- 4. tmp_calc_status_fix_backup 表
-- 原因: 临时备份表，不再需要
DROP TABLE IF EXISTS public.tmp_calc_status_fix_backup CASCADE;

-- ============================================================================
-- 执行完成
-- ============================================================================

