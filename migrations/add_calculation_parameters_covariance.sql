-- 迁移脚本：扩展 calculation_parameters 表
-- 方案8：参数历史记录和增量优化修复方案
-- 创建日期：2025-10-26
-- 版本：v1.0

-- 步骤1：添加 covariance_matrix 字段
ALTER TABLE calculation_parameters
ADD COLUMN IF NOT EXISTS covariance_matrix JSONB;

-- 步骤2：添加 rls_iterations 字段（记录RLS迭代次数）
ALTER TABLE calculation_parameters
ADD COLUMN IF NOT EXISTS rls_iterations INTEGER DEFAULT 0;

-- 步骤3：添加 last_p_trace 字段（记录P矩阵的迹，用于监控）
ALTER TABLE calculation_parameters
ADD COLUMN IF NOT EXISTS last_p_trace NUMERIC;

-- 步骤4：添加注释
COMMENT ON COLUMN calculation_parameters.covariance_matrix IS '当前的RLS协方差矩阵P（JSONB格式）';
COMMENT ON COLUMN calculation_parameters.rls_iterations IS 'RLS算法的累计迭代次数';
COMMENT ON COLUMN calculation_parameters.last_p_trace IS 'P矩阵的迹（trace），用于监控参数估计的不确定性';

