-- 迁移脚本：扩展 optimization_history 表
-- 方案8：参数历史记录和增量优化修复方案
-- 创建日期：2025-10-26
-- 版本：v1.0

-- 步骤1：添加 method_id 字段
ALTER TABLE optimization_history
ADD COLUMN IF NOT EXISTS method_id TEXT;

-- 步骤2：添加 covariance_matrix 字段（存储P矩阵）
ALTER TABLE optimization_history
ADD COLUMN IF NOT EXISTS covariance_matrix JSONB;

-- 步骤3：添加 rls_state 字段（存储RLS算法的其他状态）
ALTER TABLE optimization_history
ADD COLUMN IF NOT EXISTS rls_state JSONB;

-- 步骤4：为 method_id 添加索引
CREATE INDEX IF NOT EXISTS idx_oh_method_id ON optimization_history(method_id);

-- 步骤5：添加复合索引（常用查询组合）
CREATE INDEX IF NOT EXISTS idx_oh_device_method_time 
ON optimization_history(device_id, method_id, created_at DESC);

-- 步骤6：添加唯一约束（防止重复记录）
-- 注意：同一时刻同一设备同一方法只能有一条优化记录
-- 由于 created_at 有默认值 now()，可能会有重复，所以先不添加唯一约束
-- ALTER TABLE optimization_history
-- ADD CONSTRAINT uq_oh_device_method_time 
-- UNIQUE (station_id, device_id, metric_key, method_id, created_at);

-- 步骤7：添加注释
COMMENT ON COLUMN optimization_history.method_id IS '计算方法ID（如 FLOW_COEF_V1）';
COMMENT ON COLUMN optimization_history.covariance_matrix IS 'RLS协方差矩阵P（JSONB格式，存储为二维数组）';
COMMENT ON COLUMN optimization_history.rls_state IS 'RLS算法的其他状态（如遗忘因子、迭代次数等）';

