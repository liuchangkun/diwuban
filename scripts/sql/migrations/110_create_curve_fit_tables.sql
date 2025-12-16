-- =====================================================================
-- 迁移脚本: 110_create_curve_fit_tables.sql
-- 用途: 创建曲线拟合三表分离设计（curve_fit_results, curve_fit_params, curve_fit_metrics）
-- 创建日期: 2025-12-02
-- 版本: v1.0
-- 依赖: dim_devices 表
-- 说明: 实现特性曲线拟合系统的核心存储表
-- =====================================================================

\encoding UTF8
SET client_encoding = 'UTF8';

BEGIN;

-- ============================================================
-- 1. 主表: curve_fit_results（曲线拟合结果主表）
-- ============================================================

CREATE TABLE IF NOT EXISTS public.curve_fit_results (
    -- ========== 主键 ==========
    id SERIAL NOT NULL,

    -- ========== 基本信息 ==========
    device_id BIGINT NOT NULL,
    curve_type VARCHAR(50) NOT NULL,
    version VARCHAR(50) NOT NULL,
    method_name VARCHAR(100) NOT NULL,

    -- ========== 数据信息 ==========
    data_start_time TIMESTAMP WITH TIME ZONE,
    data_end_time TIMESTAMP WITH TIME ZONE,
    data_point_count INTEGER,
    data_coverage_rate DOUBLE PRECISION,

    -- ========== 复杂结构（保留JSONB） ==========
    physics_validation JSONB,
    historical_evaluation JSONB,
    normalization_params JSONB,

    -- ========== 元数据 ==========
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(100),
    status VARCHAR(20) DEFAULT 'active',
    tags TEXT[],
    notes TEXT,

    -- ========== 约束 ==========
    CONSTRAINT pk_curve_fit_results PRIMARY KEY (id),
    CONSTRAINT fk_results_device FOREIGN KEY (device_id)
        REFERENCES public.dim_devices(id) ON DELETE RESTRICT,
    CONSTRAINT uq_results_device_curve_version
        UNIQUE(device_id, curve_type, version),
    CONSTRAINT chk_results_curve_type
        CHECK (curve_type IN ('qh', 'qp', 'qeta', 'heta', 'peta', 'qnpsh')),
    CONSTRAINT chk_results_status
        CHECK (status IN ('active', 'archived', 'deprecated')),
    CONSTRAINT chk_results_coverage_rate
        CHECK (data_coverage_rate IS NULL OR
               (data_coverage_rate >= 0 AND data_coverage_rate <= 1))
);

-- ========== 主表索引 ==========
CREATE INDEX IF NOT EXISTS idx_results_device_curve ON public.curve_fit_results(device_id, curve_type);
CREATE INDEX IF NOT EXISTS idx_results_version ON public.curve_fit_results(version);
CREATE INDEX IF NOT EXISTS idx_results_created_at ON public.curve_fit_results(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_results_status ON public.curve_fit_results(status);
CREATE INDEX IF NOT EXISTS idx_results_method ON public.curve_fit_results(method_name);

-- ========== 主表注释 ==========
COMMENT ON TABLE public.curve_fit_results IS '曲线拟合结果主表（三表分离设计）';
COMMENT ON COLUMN public.curve_fit_results.id IS '主键ID';
COMMENT ON COLUMN public.curve_fit_results.device_id IS '设备ID（外键关联dim_devices）';
COMMENT ON COLUMN public.curve_fit_results.curve_type IS '曲线类型：qh/qp/qeta/heta/peta/qnpsh';
COMMENT ON COLUMN public.curve_fit_results.version IS '版本号（时间戳格式：YYYYMMDD_HHMMSS）';
COMMENT ON COLUMN public.curve_fit_results.method_name IS '拟合方法名称';
COMMENT ON COLUMN public.curve_fit_results.data_start_time IS '拟合数据起始时间';
COMMENT ON COLUMN public.curve_fit_results.data_end_time IS '拟合数据结束时间';
COMMENT ON COLUMN public.curve_fit_results.data_point_count IS '拟合数据点数';
COMMENT ON COLUMN public.curve_fit_results.data_coverage_rate IS '数据覆盖率（0-1）';
COMMENT ON COLUMN public.curve_fit_results.physics_validation IS '物理约束验证结果（JSONB）';
COMMENT ON COLUMN public.curve_fit_results.historical_evaluation IS '历史数据评估结果（JSONB）';
COMMENT ON COLUMN public.curve_fit_results.normalization_params IS '归一化参数（JSONB）';
COMMENT ON COLUMN public.curve_fit_results.created_at IS '创建时间';
COMMENT ON COLUMN public.curve_fit_results.created_by IS '创建者';
COMMENT ON COLUMN public.curve_fit_results.status IS '状态：active/archived/deprecated';
COMMENT ON COLUMN public.curve_fit_results.tags IS '标签数组';
COMMENT ON COLUMN public.curve_fit_results.notes IS '备注';

-- ============================================================
-- 2. 参数表: curve_fit_params（拟合参数表）
-- ============================================================

CREATE TABLE IF NOT EXISTS public.curve_fit_params (
    -- ========== 主键 ==========
    id SERIAL NOT NULL,

    -- ========== 外键关联 ==========
    result_id INTEGER NOT NULL,

    -- ========== 参数信息 ==========
    param_category VARCHAR(50) NOT NULL,
    param_key VARCHAR(100) NOT NULL,
    param_value DOUBLE PRECISION,
    param_text TEXT,

    -- ========== 元数据 ==========
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- ========== 约束 ==========
    CONSTRAINT pk_curve_fit_params PRIMARY KEY (id),
    CONSTRAINT fk_params_result_id
        FOREIGN KEY (result_id) REFERENCES public.curve_fit_results(id) ON DELETE CASCADE,
    CONSTRAINT uq_params_result_category_key
        UNIQUE(result_id, param_category, param_key),
    CONSTRAINT chk_params_category
        CHECK (param_category IN ('fit', 'method'))
);

-- ========== 参数表索引 ==========
CREATE INDEX IF NOT EXISTS idx_params_result_id ON public.curve_fit_params(result_id);
CREATE INDEX IF NOT EXISTS idx_params_category ON public.curve_fit_params(param_category);
CREATE INDEX IF NOT EXISTS idx_params_key ON public.curve_fit_params(param_key);

-- ========== 参数表注释 ==========
COMMENT ON TABLE public.curve_fit_params IS '曲线拟合参数表（存储拟合系数和方法参数）';
COMMENT ON COLUMN public.curve_fit_params.id IS '主键ID';
COMMENT ON COLUMN public.curve_fit_params.result_id IS '外键关联主表curve_fit_results.id';
COMMENT ON COLUMN public.curve_fit_params.param_category IS '参数类别：fit（拟合系数）/method（方法参数）';
COMMENT ON COLUMN public.curve_fit_params.param_key IS '参数名（如a0, a1, a2, degree, lambda等）';
COMMENT ON COLUMN public.curve_fit_params.param_value IS '数值型参数值';
COMMENT ON COLUMN public.curve_fit_params.param_text IS '文本型参数值（如字符串配置）';
COMMENT ON COLUMN public.curve_fit_params.created_at IS '创建时间';

-- ============================================================
-- 3. 指标表: curve_fit_metrics（拟合指标表）
-- ============================================================

CREATE TABLE IF NOT EXISTS public.curve_fit_metrics (
    -- ========== 主键 ==========
    id SERIAL NOT NULL,

    -- ========== 外键关联（1:1关系） ==========
    result_id INTEGER NOT NULL,

    -- ========== 评估指标 ==========
    r_squared DOUBLE PRECISION,
    rmse DOUBLE PRECISION,
    mae DOUBLE PRECISION,
    mape DOUBLE PRECISION,

    -- ========== 元数据 ==========
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- ========== 约束 ==========
    CONSTRAINT pk_curve_fit_metrics PRIMARY KEY (id),
    CONSTRAINT fk_metrics_result_id
        FOREIGN KEY (result_id) REFERENCES public.curve_fit_results(id) ON DELETE CASCADE,
    CONSTRAINT uq_metrics_result_id UNIQUE(result_id),
    CONSTRAINT chk_metrics_r_squared
        CHECK (r_squared IS NULL OR (r_squared >= 0 AND r_squared <= 1))
);

-- ========== 指标表索引 ==========
CREATE INDEX IF NOT EXISTS idx_metrics_result_id ON public.curve_fit_metrics(result_id);
CREATE INDEX IF NOT EXISTS idx_metrics_r_squared ON public.curve_fit_metrics(r_squared DESC);

-- ========== 指标表注释 ==========
COMMENT ON TABLE public.curve_fit_metrics IS '曲线拟合指标表（存储评估指标）';
COMMENT ON COLUMN public.curve_fit_metrics.id IS '主键ID';
COMMENT ON COLUMN public.curve_fit_metrics.result_id IS '外键关联主表curve_fit_results.id（1:1关系）';
COMMENT ON COLUMN public.curve_fit_metrics.r_squared IS 'R²拟合优度（0-1）';
COMMENT ON COLUMN public.curve_fit_metrics.rmse IS '均方根误差';
COMMENT ON COLUMN public.curve_fit_metrics.mae IS '平均绝对误差';
COMMENT ON COLUMN public.curve_fit_metrics.mape IS '平均绝对百分比误差（%）';
COMMENT ON COLUMN public.curve_fit_metrics.created_at IS '创建时间';

-- ============================================================
-- 4. 历史评估表: curve_fit_history
-- ============================================================

CREATE TABLE IF NOT EXISTS public.curve_fit_history (
    id SERIAL PRIMARY KEY,
    result_id INTEGER NOT NULL REFERENCES public.curve_fit_results(id) ON DELETE CASCADE,
    evaluation_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    test_period_start TIMESTAMP WITH TIME ZONE,
    test_period_end TIMESTAMP WITH TIME ZONE,
    test_point_count INTEGER,
    deviation_stats JSONB,
    pass_rate JSONB,
    segment_evaluation JSONB,
    overall_score DOUBLE PRECISION,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_history_result_id ON public.curve_fit_history(result_id);
CREATE INDEX IF NOT EXISTS idx_history_eval_time ON public.curve_fit_history(evaluation_time DESC);

COMMENT ON TABLE public.curve_fit_history IS '曲线拟合历史评估记录';
COMMENT ON COLUMN public.curve_fit_history.result_id IS '外键关联主表curve_fit_results.id';

-- ============================================================
-- 5. 学习约束参数表: learned_constraints
-- ============================================================

CREATE TABLE IF NOT EXISTS public.learned_constraints (
    -- ========== 主键 ==========
    id SERIAL PRIMARY KEY,

    -- ========== 基本信息 ==========
    device_id BIGINT NOT NULL,
    curve_type VARCHAR(50) NOT NULL,

    -- ========== 约束参数 ==========
    constraints JSONB NOT NULL,

    -- ========== 学习信息 ==========
    learned_from_samples INTEGER NOT NULL,
    learning_method VARCHAR(50) NOT NULL,
    statistics JSONB,

    -- ========== 自动验证结果 ==========
    auto_validation_result JSONB NOT NULL,
    is_applied BOOLEAN DEFAULT FALSE,
    applied_at TIMESTAMP WITH TIME ZONE,

    -- ========== 元数据 ==========
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(100),

    -- ========== 约束 ==========
    CONSTRAINT unique_device_curve_constraints
        UNIQUE(device_id, curve_type),
    CONSTRAINT check_curve_type_learned
        CHECK (curve_type IN ('qh', 'qp', 'qeta', 'heta', 'peta', 'qnpsh')),
    CONSTRAINT check_samples
        CHECK (learned_from_samples >= 20),
    CONSTRAINT check_learning_method
        CHECK (learning_method IN ('3sigma', 'quantile', 'rated_based'))
);

CREATE INDEX IF NOT EXISTS idx_learned_constraints_device ON public.learned_constraints(device_id);
CREATE INDEX IF NOT EXISTS idx_learned_constraints_applied ON public.learned_constraints(is_applied);
CREATE INDEX IF NOT EXISTS idx_learned_constraints_created ON public.learned_constraints(created_at DESC);

COMMENT ON TABLE public.learned_constraints IS '从历史成功拟合中学习到的约束参数';
COMMENT ON COLUMN public.learned_constraints.constraints IS '学习到的约束参数（JSONB）';
COMMENT ON COLUMN public.learned_constraints.statistics IS '统计信息：均值、标准差、分位数等';
COMMENT ON COLUMN public.learned_constraints.auto_validation_result IS '自动验证结果';
COMMENT ON COLUMN public.learned_constraints.is_applied IS '是否已应用';
COMMENT ON COLUMN public.learned_constraints.applied_at IS '应用时间';

-- ============================================================
-- 6. 约束参数变更历史表: constraint_change_history
-- ============================================================

CREATE TABLE IF NOT EXISTS public.constraint_change_history (
    -- ========== 主键 ==========
    id SERIAL PRIMARY KEY,

    -- ========== 基本信息 ==========
    device_id BIGINT NOT NULL,
    curve_type VARCHAR(50) NOT NULL,

    -- ========== 变更信息 ==========
    change_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    trigger_reason VARCHAR(50) NOT NULL,

    -- ========== 约束参数变更 ==========
    old_constraints JSONB,
    new_constraints JSONB NOT NULL,

    -- ========== 学习信息 ==========
    learning_method VARCHAR(50) NOT NULL,
    learned_from_samples INTEGER NOT NULL,
    statistics JSONB,

    -- ========== 自动验证结果 ==========
    auto_validation_result JSONB NOT NULL,

    -- ========== 变更结果 ==========
    is_successful BOOLEAN NOT NULL,
    failure_reason TEXT,

    -- ========== 元数据 ==========
    created_by VARCHAR(100),
    notes TEXT,

    -- ========== 约束 ==========
    CONSTRAINT check_curve_type_history
        CHECK (curve_type IN ('qh', 'qp', 'qeta', 'heta', 'peta', 'qnpsh')),
    CONSTRAINT check_trigger_reason
        CHECK (trigger_reason IN ('scheduled', 'manual', 'api')),
    CONSTRAINT check_learning_method_history
        CHECK (learning_method IN ('3sigma', 'quantile', 'rated_based'))
);

CREATE INDEX IF NOT EXISTS idx_change_history_device ON public.constraint_change_history(device_id);
CREATE INDEX IF NOT EXISTS idx_change_history_curve ON public.constraint_change_history(curve_type);
CREATE INDEX IF NOT EXISTS idx_change_history_time ON public.constraint_change_history(change_time DESC);
CREATE INDEX IF NOT EXISTS idx_change_history_successful ON public.constraint_change_history(is_successful);
CREATE INDEX IF NOT EXISTS idx_change_history_device_curve ON public.constraint_change_history(device_id, curve_type);

COMMENT ON TABLE public.constraint_change_history IS '约束参数变更历史记录';
COMMENT ON COLUMN public.constraint_change_history.trigger_reason IS '触发原因：scheduled/manual/api';
COMMENT ON COLUMN public.constraint_change_history.old_constraints IS '变更前的约束参数';
COMMENT ON COLUMN public.constraint_change_history.new_constraints IS '变更后的约束参数';
COMMENT ON COLUMN public.constraint_change_history.is_successful IS '变更是否成功';
COMMENT ON COLUMN public.constraint_change_history.failure_reason IS '失败原因';

-- ============================================================
-- 7. 视图: curve_fit_latest（每个设备每种曲线的最新版本）
-- ============================================================

CREATE OR REPLACE VIEW public.curve_fit_latest AS
WITH ranked AS (
    SELECT
        r.*,
        m.r_squared,
        m.rmse,
        m.mae,
        m.mape,
        ROW_NUMBER() OVER (
            PARTITION BY r.device_id, r.curve_type
            ORDER BY r.created_at DESC
        ) as rn
    FROM public.curve_fit_results r
    LEFT JOIN public.curve_fit_metrics m ON r.id = m.result_id
    WHERE r.status = 'active'
)
SELECT
    id, device_id, curve_type, version, method_name,
    r_squared, rmse, mae, mape,
    physics_validation, historical_evaluation,
    normalization_params, created_at, status
FROM ranked
WHERE rn = 1;

COMMENT ON VIEW public.curve_fit_latest IS '每个设备每种曲线的最新活跃版本';

-- ============================================================
-- 8. 视图: v_curve_fit_full（三表联合的完整拟合结果视图）
-- ============================================================

CREATE OR REPLACE VIEW public.v_curve_fit_full AS
SELECT
    r.id,
    r.device_id,
    r.curve_type,
    r.version,
    r.method_name,
    r.data_start_time,
    r.data_end_time,
    r.data_point_count,
    r.data_coverage_rate,
    r.physics_validation,
    r.historical_evaluation,
    r.normalization_params,
    r.created_at,
    r.created_by,
    r.status,
    r.tags,
    r.notes,
    m.r_squared,
    m.rmse,
    m.mae,
    m.mape,
    (
        SELECT jsonb_object_agg(p.param_key, p.param_value)
        FROM public.curve_fit_params p
        WHERE p.result_id = r.id AND p.param_category = 'fit'
    ) AS fit_params,
    (
        SELECT jsonb_object_agg(p.param_key, COALESCE(p.param_value::text, p.param_text))
        FROM public.curve_fit_params p
        WHERE p.result_id = r.id AND p.param_category = 'method'
    ) AS method_params
FROM public.curve_fit_results r
LEFT JOIN public.curve_fit_metrics m ON r.id = m.result_id;

COMMENT ON VIEW public.v_curve_fit_full IS '三表联合的完整拟合结果视图，提供与原单表类似的查询体验';

-- ============================================================
-- 完成迁移
-- ============================================================

DO $$
BEGIN
    RAISE NOTICE '✅ 曲线拟合三表分离设计创建完成';
    RAISE NOTICE '   - curve_fit_results: 主表';
    RAISE NOTICE '   - curve_fit_params: 参数表';
    RAISE NOTICE '   - curve_fit_metrics: 指标表';
    RAISE NOTICE '   - curve_fit_history: 历史评估表';
    RAISE NOTICE '   - learned_constraints: 学习约束参数表';
    RAISE NOTICE '   - constraint_change_history: 约束变更历史表';
    RAISE NOTICE '   - curve_fit_latest: 最新版本视图';
    RAISE NOTICE '   - v_curve_fit_full: 完整结果视图';
END $$;

COMMIT;

