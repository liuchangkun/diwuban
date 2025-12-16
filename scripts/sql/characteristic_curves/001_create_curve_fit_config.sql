-- ============================================================
-- 特性曲线拟合配置表
-- 用途：存储特性曲线拟合相关的配置参数（包括推荐方法规则）
-- 创建日期：2025-12-11
-- 版本：v1.0
-- ============================================================

BEGIN;

-- 创建配置表
CREATE TABLE IF NOT EXISTS curve_fit_config (
    id SERIAL PRIMARY KEY,
    config_key TEXT NOT NULL UNIQUE,
    config_value JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT DEFAULT 'system'
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_curve_fit_config_key ON curve_fit_config(config_key);

-- 添加注释
COMMENT ON TABLE curve_fit_config IS '特性曲线拟合配置表：存储推荐方法规则、验证阈值等配置参数';
COMMENT ON COLUMN curve_fit_config.config_key IS '配置键（唯一标识符）';
COMMENT ON COLUMN curve_fit_config.config_value IS '配置值（JSONB格式）';
COMMENT ON COLUMN curve_fit_config.description IS '配置描述';
COMMENT ON COLUMN curve_fit_config.created_at IS '创建时间';
COMMENT ON COLUMN curve_fit_config.updated_at IS '更新时间';
COMMENT ON COLUMN curve_fit_config.updated_by IS '更新者';

-- ============================================================
-- 插入推荐方法规则配置
-- ============================================================

INSERT INTO curve_fit_config (config_key, config_value, description, updated_by) VALUES
('recommended_methods', '{
    "qh": {
        "default": ["poly2"],
        "high_quality": ["poly2", "poly3"],
        "sparse_data": ["piecewise_linear"],
        "noisy_data": ["piecewise_linear"]
    },
    "qp": {
        "default": ["poly2"],
        "high_quality": ["poly2", "poly3"],
        "sparse_data": ["piecewise_linear"],
        "noisy_data": ["piecewise_linear"]
    },
    "qeta": {
        "default": ["poly2"],
        "high_quality": ["poly2"],
        "sparse_data": ["piecewise_linear"],
        "noisy_data": ["piecewise_linear"]
    }
}'::jsonb, '方法推荐规则：根据曲线类型和数据质量推荐拟合方法', 'migration:001')
ON CONFLICT (config_key) DO UPDATE SET
    config_value = EXCLUDED.config_value,
    description = EXCLUDED.description,
    updated_at = NOW(),
    updated_by = EXCLUDED.updated_by;

-- ============================================================
-- 验证数据
-- ============================================================

-- 查询推荐方法配置
SELECT config_key, config_value, description 
FROM curve_fit_config 
WHERE config_key = 'recommended_methods';

COMMIT;
