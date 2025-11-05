-- 添加 slip 参数到 global_default_rated_params 表
-- 执行时间：2025-10-26

BEGIN;

-- 插入 slip 参数（滑差，默认0.02，即2%）
INSERT INTO global_default_rated_params (param_key, default_value, description)
VALUES ('slip', 0.02, 'Default motor slip (2%)')
ON CONFLICT (param_key) DO UPDATE
SET default_value = EXCLUDED.default_value,
    description = EXCLUDED.description;

COMMIT;

-- 验证插入
SELECT param_key, default_value, description
FROM global_default_rated_params
WHERE param_key = 'slip';

