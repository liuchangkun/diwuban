-- =====================================================
-- 创建性能指标表
-- =====================================================
-- 用途：记录计算过程的性能指标，用于自适应优化
-- 作者：System
-- 创建时间：2025-10-05
-- =====================================================

-- 创建性能指标表
CREATE TABLE IF NOT EXISTS calculation_performance_metrics (
    id BIGSERIAL PRIMARY KEY,
    
    -- 关联信息
    run_id BIGINT,  -- 可选，关联completion_runs表
    station_id BIGINT NOT NULL,
    device_id BIGINT NOT NULL,
    
    -- 批次信息
    batch_number INT NOT NULL,
    time_window_minutes INT NOT NULL,
    batch_size INT NOT NULL,
    data_points INT NOT NULL,
    
    -- 性能指标
    duration_ms INT NOT NULL,
    memory_mb NUMERIC,
    throughput NUMERIC,  -- 条/秒
    
    -- 调整信息
    adjustment_type TEXT,  -- 'window'/'batch'/'none'
    adjustment_reason TEXT,
    old_value INT,
    new_value INT,
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 约束
    CONSTRAINT chk_adjustment_type CHECK (
        adjustment_type IS NULL OR 
        adjustment_type IN ('window', 'batch', 'none')
    ),
    CONSTRAINT chk_positive_values CHECK (
        batch_number > 0 AND
        time_window_minutes > 0 AND
        batch_size > 0 AND
        data_points >= 0 AND
        duration_ms >= 0
    )
);

-- 创建索引（优化查询性能）
CREATE INDEX IF NOT EXISTS idx_perf_metrics_device_time 
ON calculation_performance_metrics (device_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_perf_metrics_station_time 
ON calculation_performance_metrics (station_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_perf_metrics_run_id 
ON calculation_performance_metrics (run_id) 
WHERE run_id IS NOT NULL;

-- 添加表注释
COMMENT ON TABLE calculation_performance_metrics IS '计算性能指标表，记录批次处理的性能数据';
COMMENT ON COLUMN calculation_performance_metrics.run_id IS '运行ID，关联completion_runs表（可选）';
COMMENT ON COLUMN calculation_performance_metrics.batch_number IS '批次编号（从1开始）';
COMMENT ON COLUMN calculation_performance_metrics.time_window_minutes IS '时间窗口大小（分钟）';
COMMENT ON COLUMN calculation_performance_metrics.batch_size IS '批量大小（条数）';
COMMENT ON COLUMN calculation_performance_metrics.data_points IS '数据点数';
COMMENT ON COLUMN calculation_performance_metrics.duration_ms IS '处理耗时（毫秒）';
COMMENT ON COLUMN calculation_performance_metrics.memory_mb IS '内存使用（MB）';
COMMENT ON COLUMN calculation_performance_metrics.throughput IS '吞吐量（条/秒）';
COMMENT ON COLUMN calculation_performance_metrics.adjustment_type IS '调整类型：window=时间窗口, batch=批量大小, none=无调整';
COMMENT ON COLUMN calculation_performance_metrics.adjustment_reason IS '调整原因描述';
COMMENT ON COLUMN calculation_performance_metrics.old_value IS '调整前的值';
COMMENT ON COLUMN calculation_performance_metrics.new_value IS '调整后的值';

-- 验证表结构
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'calculation_performance_metrics'
ORDER BY ordinal_position;

COMMIT;

