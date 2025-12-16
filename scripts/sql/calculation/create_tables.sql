-- =====================================================
-- 缺失指标计算功能 - 数据库表创建脚本
-- =====================================================
-- 创建时间: 2025-09-30
-- 用途: 创建6个核心数据库表，支持缺失指标计算功能
-- 表列表:
--   1. metric_calculation_order - 指标计算顺序表
--   2. calculation_method_registry - 计算方法注册表
--   3. calculation_parameters - 计算参数表
--   4. calculation_validation_config - 验证配置表
--   5. calculation_failures_log - 计算失败日志表
--   6. optimization_history - 优化历史表
-- =====================================================

-- 表1: metric_calculation_order - 指标计算顺序表
-- 用途: 存储指标的依赖关系和拓扑排序结果
CREATE TABLE IF NOT EXISTS metric_calculation_order (
    metric_key TEXT PRIMARY KEY REFERENCES dim_metric_config(metric_key),
    depends_on TEXT[] NOT NULL DEFAULT '{}',  -- 依赖的指标列表（metric_key数组）
    priority INTEGER NOT NULL DEFAULT 100,     -- 优先级（越大越优先）
    order_index INTEGER NOT NULL,              -- 拓扑排序后的顺序（从0开始）
    is_circular BOOLEAN NOT NULL DEFAULT FALSE, -- 是否涉及循环依赖
    circular_group TEXT,                        -- 循环依赖组ID
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT NOT NULL DEFAULT 'system'
);

CREATE INDEX IF NOT EXISTS idx_mco_order ON metric_calculation_order(order_index);
CREATE INDEX IF NOT EXISTS idx_mco_priority ON metric_calculation_order(priority DESC);

COMMENT ON TABLE metric_calculation_order IS '指标计算顺序表：记录指标的依赖关系和计算顺序';
COMMENT ON COLUMN metric_calculation_order.metric_key IS '指标键（外键引用dim_metric_config）';
COMMENT ON COLUMN metric_calculation_order.depends_on IS '依赖的指标列表（metric_key数组）';
COMMENT ON COLUMN metric_calculation_order.order_index IS '拓扑排序后的计算顺序（从0开始）';
COMMENT ON COLUMN metric_calculation_order.is_circular IS '是否涉及循环依赖';
COMMENT ON COLUMN metric_calculation_order.circular_group IS '循环依赖组ID（用于标识哪些指标形成循环）';

-- 表2: calculation_method_registry - 计算方法注册表
-- 用途: 记录每个指标的所有计算方法
CREATE TABLE IF NOT EXISTS calculation_method_registry (
    method_id TEXT PRIMARY KEY,                -- 如：pump_flow_rate_method_a
    metric_key TEXT NOT NULL REFERENCES dim_metric_config(metric_key),
    method_name TEXT NOT NULL,                 -- 如：功率×频率分摊
    method_code TEXT NOT NULL,                 -- 如：A, B, C
    priority INTEGER NOT NULL DEFAULT 100,     -- 优先级（越大越优先）
    dependencies TEXT[] NOT NULL DEFAULT '{}', -- 依赖的指标列表（metric_key数组）
    conditions JSONB NOT NULL DEFAULT '{}',    -- 使用条件（JSON格式）
    formula_ref TEXT,                          -- 公式文档引用
    accuracy_level TEXT NOT NULL DEFAULT 'medium', -- high/medium/low
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(metric_key, method_code)
);

CREATE INDEX IF NOT EXISTS idx_cmr_metric ON calculation_method_registry(metric_key);
CREATE INDEX IF NOT EXISTS idx_cmr_priority ON calculation_method_registry(metric_key, priority DESC);
CREATE INDEX IF NOT EXISTS idx_cmr_enabled ON calculation_method_registry(is_enabled) WHERE is_enabled = TRUE;

COMMENT ON TABLE calculation_method_registry IS '计算方法注册表：记录每个指标的所有计算方法';
COMMENT ON COLUMN calculation_method_registry.method_id IS '方法唯一标识符（如pump_flow_rate_method_a）';
COMMENT ON COLUMN calculation_method_registry.method_code IS '方法代码（A/B/C/D等）';
COMMENT ON COLUMN calculation_method_registry.dependencies IS '依赖的指标列表（metric_key数组）';
COMMENT ON COLUMN calculation_method_registry.conditions IS '使用条件（JSON）：如{"running_count": {"min": 2}, "device_type": "pump"}';
COMMENT ON COLUMN calculation_method_registry.accuracy_level IS '精度等级：high（高精度）/medium（中等）/low（低精度）';

-- 表3: calculation_parameters - 计算参数表
-- 用途: 存储每个设备每个指标每个方法的参数
CREATE TABLE IF NOT EXISTS calculation_parameters (
    id BIGSERIAL PRIMARY KEY,
    station_id BIGINT REFERENCES dim_stations(id),
    device_id BIGINT REFERENCES dim_devices(id),
    metric_key TEXT NOT NULL REFERENCES dim_metric_config(metric_key),
    method_id TEXT NOT NULL REFERENCES calculation_method_registry(method_id),
    param_name TEXT NOT NULL,                  -- 如：alpha, beta, f_thr
    param_value NUMERIC NOT NULL,
    param_type TEXT NOT NULL DEFAULT 'float',  -- float/int/bool
    is_optimizable BOOLEAN NOT NULL DEFAULT TRUE,
    optimization_history JSONB,                -- 优化历史记录
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT NOT NULL DEFAULT 'system',
    UNIQUE(device_id, metric_key, method_id, param_name)
);

CREATE INDEX IF NOT EXISTS idx_cp_device_metric ON calculation_parameters(device_id, metric_key);
CREATE INDEX IF NOT EXISTS idx_cp_method ON calculation_parameters(method_id);
CREATE INDEX IF NOT EXISTS idx_cp_station ON calculation_parameters(station_id);
CREATE INDEX IF NOT EXISTS idx_cp_global ON calculation_parameters(device_id) WHERE device_id IS NULL;

COMMENT ON TABLE calculation_parameters IS '计算参数表：存储每个设备每个指标每个方法的参数';
COMMENT ON COLUMN calculation_parameters.station_id IS '泵站ID（NULL表示全局默认）';
COMMENT ON COLUMN calculation_parameters.device_id IS '设备ID（NULL表示全局默认）';
COMMENT ON COLUMN calculation_parameters.is_optimizable IS '是否可优化（有些参数是固定的，如g=9.80665）';
COMMENT ON COLUMN calculation_parameters.optimization_history IS '优化历史记录（JSON格式）';

-- 表4: calculation_validation_config - 验证配置表
-- 用途: 存储验证器的参数
CREATE TABLE IF NOT EXISTS calculation_validation_config (
    id BIGSERIAL PRIMARY KEY,
    station_id BIGINT REFERENCES dim_stations(id),
    device_id BIGINT REFERENCES dim_devices(id),
    metric_key TEXT NOT NULL REFERENCES dim_metric_config(metric_key),
    validator_type TEXT NOT NULL,              -- physics/curve/statistical
    param_name TEXT NOT NULL,                  -- 如：min_value, max_value, threshold
    param_value NUMERIC NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(device_id, metric_key, validator_type, param_name)
);

CREATE INDEX IF NOT EXISTS idx_cvc_device_metric ON calculation_validation_config(device_id, metric_key);
CREATE INDEX IF NOT EXISTS idx_cvc_validator_type ON calculation_validation_config(validator_type);
CREATE INDEX IF NOT EXISTS idx_cvc_enabled ON calculation_validation_config(enabled) WHERE enabled = TRUE;

COMMENT ON TABLE calculation_validation_config IS '验证配置表：存储验证器的参数';
COMMENT ON COLUMN calculation_validation_config.validator_type IS '验证器类型：physics（物理定律）/curve（特性曲线）/statistical（统计阈值）';
COMMENT ON COLUMN calculation_validation_config.param_name IS '参数名称：如min_value（最小值）/max_value（最大值）/threshold（阈值）';

-- 表5: calculation_failures_log - 计算失败日志表
-- 用途: 记录所有计算和验证失败的情况
CREATE TABLE IF NOT EXISTS calculation_failures_log (
    id BIGSERIAL PRIMARY KEY,
    station_id BIGINT NOT NULL,
    device_id BIGINT NOT NULL,
    metric_key TEXT NOT NULL,
    ts_second TIMESTAMPTZ NOT NULL,
    method_id TEXT,
    error_type TEXT NOT NULL,                  -- missing_data/validation_failed/calculation_error/circular_dependency
    error_message TEXT NOT NULL,
    error_details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cfl_device_time ON calculation_failures_log(device_id, ts_second);
CREATE INDEX IF NOT EXISTS idx_cfl_metric ON calculation_failures_log(metric_key);
CREATE INDEX IF NOT EXISTS idx_cfl_error_type ON calculation_failures_log(error_type);
CREATE INDEX IF NOT EXISTS idx_cfl_created_at ON calculation_failures_log(created_at DESC);

COMMENT ON TABLE calculation_failures_log IS '计算失败日志表：记录所有计算和验证失败的情况';
COMMENT ON COLUMN calculation_failures_log.error_type IS '错误类型：missing_data（缺失数据）/validation_failed（验证失败）/calculation_error（计算错误）/circular_dependency（循环依赖）';
COMMENT ON COLUMN calculation_failures_log.error_details IS '错误详情（JSON格式）：包含更多上下文信息';

-- 表6: optimization_history - 优化历史表
-- 用途: 记录参数优化的历史
CREATE TABLE IF NOT EXISTS optimization_history (
    id BIGSERIAL PRIMARY KEY,
    station_id BIGINT NOT NULL,
    device_id BIGINT NOT NULL,
    metric_key TEXT NOT NULL,
    optimization_type TEXT NOT NULL,           -- rls/curve/manual
    params_before JSONB NOT NULL,
    params_after JSONB NOT NULL,
    improvement_score NUMERIC,                 -- 改进分数（如RMS误差降低百分比）
    data_window_start TIMESTAMPTZ NOT NULL,
    data_window_end TIMESTAMPTZ NOT NULL,
    data_points_count INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by TEXT NOT NULL DEFAULT 'system'
);

CREATE INDEX IF NOT EXISTS idx_oh_device_metric ON optimization_history(device_id, metric_key);
CREATE INDEX IF NOT EXISTS idx_oh_time ON optimization_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_oh_optimization_type ON optimization_history(optimization_type);

COMMENT ON TABLE optimization_history IS '优化历史表：记录参数优化的历史';
COMMENT ON COLUMN optimization_history.optimization_type IS '优化类型：rls（递归最小二乘）/curve（特性曲线优化）/manual（手动调整）';
COMMENT ON COLUMN optimization_history.params_before IS '优化前的参数（JSON格式）';
COMMENT ON COLUMN optimization_history.params_after IS '优化后的参数（JSON格式）';
COMMENT ON COLUMN optimization_history.improvement_score IS '改进分数：如RMS误差降低百分比';
COMMENT ON COLUMN optimization_history.data_window_start IS '优化使用的数据窗口起始时间';
COMMENT ON COLUMN optimization_history.data_window_end IS '优化使用的数据窗口结束时间';

-- =====================================================
-- 创建完成
-- =====================================================
-- 验证方法:
-- SELECT table_name FROM information_schema.tables 
-- WHERE table_schema = 'public' 
-- AND table_name IN (
--     'metric_calculation_order',
--     'calculation_method_registry',
--     'calculation_parameters',
--     'calculation_validation_config',
--     'calculation_failures_log',
--     'optimization_history'
-- );
-- =====================================================

