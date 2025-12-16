-- 泵组拟合方法推荐配置
-- 文件: scripts/sql/characteristic_curves/002_group_recommended_methods.sql
-- 创建日期: 2025-12-13
-- 说明: 为泵组直接拟合功能添加推荐方法配置

-- 插入泵组推荐方法配置
INSERT INTO curve_fit_config (config_key, config_value, description, created_at)
VALUES (
    'group_recommended_methods',
    '{
        "qh": {
            "default": ["math_poly_2", "math_poly_3"],
            "high_quality": ["ml_gradient_boost", "ml_gaussian_process", "math_poly_3"],
            "sparse_data": ["math_poly_2"],
            "noisy_data": ["ml_gradient_boost", "math_poly_2"]
        },
        "qp": {
            "default": ["math_poly_2", "physics_power_eq"],
            "high_quality": ["physics_power_eq", "ml_gradient_boost"],
            "sparse_data": ["math_poly_2"],
            "noisy_data": ["ml_gradient_boost"]
        },
        "qeta": {
            "default": ["math_poly_3", "math_stat_gaussian"],
            "high_quality": ["ml_gaussian_process", "math_poly_3"],
            "sparse_data": ["math_poly_3"],
            "noisy_data": ["math_stat_gaussian"]
        }
    }'::jsonb,
    '泵组拟合推荐方法配置',
    NOW()
)
ON CONFLICT (config_key) DO UPDATE 
SET 
    config_value = EXCLUDED.config_value,
    description = EXCLUDED.description,
    updated_at = NOW();

-- 验证配置
SELECT 
    config_key,
    config_value->'qh'->'default' AS qh_default_methods,
    config_value->'qp'->'default' AS qp_default_methods,
    created_at
FROM curve_fit_config
WHERE config_key = 'group_recommended_methods';
