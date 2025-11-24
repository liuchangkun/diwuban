-- ============================================================================
-- 特性曲线拟合系统 - 初始化业务参数
-- 迁移编号: 111
-- 创建日期: 2025-12-08
-- 说明: 初始化验证阈值、方法推荐规则等业务参数
-- ============================================================================

BEGIN;

-- 获取迁移锁
SELECT pg_advisory_xact_lock(999999, 111);

-- ============================================================================
-- 1. 创建业务参数配置表（如果不存在）
-- ============================================================================

CREATE TABLE IF NOT EXISTS curve_fit_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE curve_fit_config IS '特性曲线拟合系统配置表';
COMMENT ON COLUMN curve_fit_config.config_key IS '配置键名';
COMMENT ON COLUMN curve_fit_config.config_value IS '配置值（JSONB格式）';
COMMENT ON COLUMN curve_fit_config.description IS '配置说明';

-- ============================================================================
-- 2. 插入验证阈值配置
-- ============================================================================

INSERT INTO curve_fit_config (config_key, config_value, description)
VALUES (
    'validation_thresholds',
    '{
        "r_squared": {
            "excellent": 0.99,
            "good": 0.95,
            "acceptable": 0.90,
            "minimum": 0.85
        },
        "rmse": {
            "qh": {"excellent": 0.5, "good": 1.0, "acceptable": 2.0, "maximum": 5.0},
            "qp": {"excellent": 1.0, "good": 2.0, "acceptable": 5.0, "maximum": 10.0},
            "qeta": {"excellent": 0.01, "good": 0.02, "acceptable": 0.05, "maximum": 0.10}
        },
        "data_points": {
            "minimum": 50,
            "recommended": 200,
            "optimal": 500
        },
        "prediction_accuracy": {
            "pass_ratio": 0.90,
            "deviation_threshold": 0.05
        }
    }'::jsonb,
    '拟合质量验证阈值配置'
)
ON CONFLICT (config_key) DO UPDATE SET
    config_value = EXCLUDED.config_value,
    updated_at = NOW();

-- ============================================================================
-- 3. 插入方法推荐规则配置
-- ============================================================================

INSERT INTO curve_fit_config (config_key, config_value, description)
VALUES (
    'method_recommendation',
    '{
        "qh": {
            "priority": ["polynomial_2", "polynomial_3", "exponential", "power"],
            "default": "polynomial_2",
            "conditions": {
                "polynomial_2": {"min_points": 50, "description": "二次多项式，适用于标准Q-H曲线"},
                "polynomial_3": {"min_points": 100, "description": "三次多项式，适用于复杂Q-H曲线"},
                "exponential": {"min_points": 50, "description": "指数函数，适用于陡降曲线"},
                "power": {"min_points": 50, "description": "幂函数，适用于平缓曲线"}
            }
        },
        "qp": {
            "priority": ["polynomial_2", "polynomial_3", "linear"],
            "default": "polynomial_2",
            "conditions": {
                "polynomial_2": {"min_points": 50, "description": "二次多项式，适用于标准Q-P曲线"},
                "polynomial_3": {"min_points": 100, "description": "三次多项式，适用于复杂Q-P曲线"},
                "linear": {"min_points": 30, "description": "线性函数，适用于简单Q-P关系"}
            }
        },
        "qeta": {
            "priority": ["gaussian", "polynomial_3", "polynomial_4"],
            "default": "gaussian",
            "conditions": {
                "gaussian": {"min_points": 100, "description": "高斯函数，适用于单峰效率曲线"},
                "polynomial_3": {"min_points": 100, "description": "三次多项式，适用于一般效率曲线"},
                "polynomial_4": {"min_points": 150, "description": "四次多项式，适用于复杂效率曲线"}
            }
        }
    }'::jsonb,
    '拟合方法推荐规则配置'
)
ON CONFLICT (config_key) DO UPDATE SET
    config_value = EXCLUDED.config_value,
    updated_at = NOW();

-- ============================================================================
-- 4. 插入物理约束配置
-- ============================================================================

INSERT INTO curve_fit_config (config_key, config_value, description)
VALUES (
    'physics_constraints',
    '{
        "qh": {
            "monotonicity": "decreasing",
            "H0_range_factor": [0.9, 1.3],
            "K_range": [-0.1, 0.0],
            "description": "Q-H曲线：扬程随流量增加而单调递减"
        },
        "qp": {
            "monotonicity": "increasing",
            "P0_range_factor": [0.3, 0.8],
            "description": "Q-P曲线：功率随流量增加而单调递增"
        },
        "qeta": {
            "monotonicity": "single_peak",
            "eta_max_range": [0.5, 0.95],
            "description": "Q-η曲线：效率呈单峰分布"
        }
    }'::jsonb,
    '物理约束配置'
)
ON CONFLICT (config_key) DO UPDATE SET
    config_value = EXCLUDED.config_value,
    updated_at = NOW();

-- ============================================================================
-- 5. 插入缓存配置
-- ============================================================================

INSERT INTO curve_fit_config (config_key, config_value, description)
VALUES (
    'cache_settings',
    '{
        "default_ttl_seconds": 3600,
        "max_entries": 1000,
        "eviction_policy": "lru",
        "key_patterns": {
            "fit_result": "fit:{device_id}:{curve_type}:{version}",
            "constraints": "constraints:{device_id}:{curve_type}"
        }
    }'::jsonb,
    '缓存配置'
)
ON CONFLICT (config_key) DO UPDATE SET
    config_value = EXCLUDED.config_value,
    updated_at = NOW();

-- 记录迁移历史
INSERT INTO migration_history (migration_id, description, executed_at)
VALUES ('111_insert_curve_fit_params', '初始化特性曲线拟合系统业务参数', NOW())
ON CONFLICT (migration_id) DO NOTHING;

COMMIT;

