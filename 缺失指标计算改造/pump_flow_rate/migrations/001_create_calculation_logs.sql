-- ============================================================================
-- 数据库迁移脚本 #001: 创建 calculation_logs 表
-- ============================================================================
-- 创建时间: 2025-01-14
-- 作者: AI
-- 目的: 创建计算流水线日志表（分区表，按天分区，保留30天）
-- 依赖: 无
-- 回滚: 见 001_rollback_calculation_logs.sql
-- ============================================================================

-- 1. 创建 calculation_logs 表（分区表）
CREATE TABLE IF NOT EXISTS calculation_logs (
    log_id BIGSERIAL,
    task_id TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    span_id TEXT NOT NULL,
    parent_span_id TEXT,
    metric_key TEXT NOT NULL,
    station_id BIGINT,
    device_id BIGINT,
    stage TEXT NOT NULL,  -- data_loader, data_filter, method_selector, calculator, validator, data_writer
    log_level TEXT NOT NULL,  -- DEBUG, INFO, WARNING, ERROR
    message TEXT NOT NULL,
    extra_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (log_id, created_at)
) PARTITION BY RANGE (created_at);

-- 2. 添加表注释
COMMENT ON TABLE calculation_logs IS '计算流水线日志表（分区表，按天分区，保留30天）';

-- 3. 添加列注释
COMMENT ON COLUMN calculation_logs.log_id IS '日志ID（自增）';
COMMENT ON COLUMN calculation_logs.task_id IS '任务ID';
COMMENT ON COLUMN calculation_logs.trace_id IS '追踪ID（串联整个流程）';
COMMENT ON COLUMN calculation_logs.span_id IS '阶段ID';
COMMENT ON COLUMN calculation_logs.parent_span_id IS '父阶段ID';
COMMENT ON COLUMN calculation_logs.metric_key IS '指标键';
COMMENT ON COLUMN calculation_logs.station_id IS '泵站ID';
COMMENT ON COLUMN calculation_logs.device_id IS '设备ID';
COMMENT ON COLUMN calculation_logs.stage IS '流水线阶段';
COMMENT ON COLUMN calculation_logs.log_level IS '日志级别';
COMMENT ON COLUMN calculation_logs.message IS '日志消息';
COMMENT ON COLUMN calculation_logs.extra_data IS '额外数据（JSON格式）';
COMMENT ON COLUMN calculation_logs.created_at IS '创建时间';

-- 4. 创建索引
-- 按任务查询日志
CREATE INDEX IF NOT EXISTS idx_calculation_logs_task_id ON calculation_logs(task_id, created_at);

-- 追踪完整流程
CREATE INDEX IF NOT EXISTS idx_calculation_logs_trace_id ON calculation_logs(trace_id, created_at);

-- 按设备查询日志
CREATE INDEX IF NOT EXISTS idx_calculation_logs_device_id ON calculation_logs(device_id, created_at);

-- 按级别查询（ERROR日志）
CREATE INDEX IF NOT EXISTS idx_calculation_logs_log_level ON calculation_logs(log_level, created_at);

-- 支持JSON字段查询
CREATE INDEX IF NOT EXISTS idx_calculation_logs_extra_data ON calculation_logs USING GIN(extra_data);

-- 5. 创建最近30天的分区
DO $$
DECLARE
    partition_date DATE;
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
BEGIN
    -- 创建最近30天的分区
    FOR i IN 0..29 LOOP
        partition_date := CURRENT_DATE + i;
        partition_name := 'calculation_logs_' || TO_CHAR(partition_date, 'YYYYMMDD');
        start_date := partition_date;
        end_date := partition_date + INTERVAL '1 day';
        
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I PARTITION OF calculation_logs FOR VALUES FROM (%L) TO (%L)',
            partition_name, start_date, end_date
        );
        
        RAISE NOTICE '创建分区: % (% 到 %)', partition_name, start_date, end_date;
    END LOOP;
END;
$$;

-- 6. 创建分区维护函数
CREATE OR REPLACE FUNCTION maintain_calculation_logs_partitions()
RETURNS VOID AS $$
DECLARE
    partition_date DATE;
    partition_name TEXT;
    old_partition_name TEXT;
    start_date DATE;
    end_date DATE;
BEGIN
    -- 创建明天的分区
    partition_date := CURRENT_DATE + 1;
    partition_name := 'calculation_logs_' || TO_CHAR(partition_date, 'YYYYMMDD');
    start_date := partition_date;
    end_date := partition_date + INTERVAL '1 day';
    
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF calculation_logs FOR VALUES FROM (%L) TO (%L)',
        partition_name, start_date, end_date
    );
    
    RAISE NOTICE '创建明天分区: % (% 到 %)', partition_name, start_date, end_date;
    
    -- 删除31天前的分区
    partition_date := CURRENT_DATE - 31;
    old_partition_name := 'calculation_logs_' || TO_CHAR(partition_date, 'YYYYMMDD');
    
    EXECUTE format('DROP TABLE IF EXISTS %I', old_partition_name);
    
    RAISE NOTICE '删除旧分区: %', old_partition_name;
END;
$$ LANGUAGE plpgsql;

-- 7. 添加函数注释
COMMENT ON FUNCTION maintain_calculation_logs_partitions() IS '维护 calculation_logs 分区（每天执行，创建明天分区，删除31天前分区）';

-- 8. 验证表创建成功
DO $$
DECLARE
    table_count INT;
    partition_count INT;
BEGIN
    -- 验证表存在
    SELECT COUNT(*) INTO table_count
    FROM pg_tables
    WHERE tablename = 'calculation_logs';
    
    IF table_count = 0 THEN
        RAISE EXCEPTION '表 calculation_logs 创建失败';
    END IF;
    
    -- 验证分区数量
    SELECT COUNT(*) INTO partition_count
    FROM pg_tables
    WHERE tablename LIKE 'calculation_logs_%';
    
    RAISE NOTICE '✅ 表创建成功！分区数量: %', partition_count;
END;
$$;

-- ============================================================================
-- 迁移完成
-- ============================================================================

