-- ============================================
-- 补充 calculation_method_registry 表的 allowed_device_types 字段
--
-- 功能：根据 metric_key 前缀填充 allowed_device_types 字段
-- 作者：AI
-- 创建日期：2025-01-17
-- 最后修改：2025-01-17
--
-- 使用方法：
--   psql -h <host> -U <user> -d <database> -f backfill_allowed_device_types.sql
--
-- 说明：
--   - 本脚本是幂等的，可以安全地多次执行
--   - 只更新 allowed_device_types 为空数组的记录
--   - 使用事务确保原子性，失败时自动回滚
--
-- 更新规则：
--   - pump_% → '{pump}'::text[]
--   - main_pipeline_% → '{main_pipeline}'::text[]
--   - pool_% 或 clear_water_pool_% → '{clear_water_pool}'::text[]
-- ============================================

BEGIN;

-- 显示更新前的状态
SELECT '=== 更新前状态 ===' AS info;
SELECT 
    metric_key,
    method_id,
    allowed_device_types,
    CASE 
        WHEN allowed_device_types = '{}'::text[] THEN '空数组'
        ELSE '已填充'
    END AS status
FROM calculation_method_registry
ORDER BY metric_key, method_id;

-- 统计空数组的记录数
SELECT '=== 空数组记录统计 ===' AS info;
SELECT COUNT(*) AS empty_count
FROM calculation_method_registry
WHERE allowed_device_types = '{}'::text[];

-- 更新1：pump_% 指标
UPDATE calculation_method_registry
SET allowed_device_types = '{pump}'::text[]
WHERE metric_key LIKE 'pump_%'
  AND allowed_device_types = '{}'::text[];

-- 更新2：main_pipeline_% 指标
UPDATE calculation_method_registry
SET allowed_device_types = '{main_pipeline}'::text[]
WHERE metric_key LIKE 'main_pipeline_%'
  AND allowed_device_types = '{}'::text[];

-- 更新3：pool_% 和 clear_water_pool_% 指标
UPDATE calculation_method_registry
SET allowed_device_types = '{clear_water_pool}'::text[]
WHERE (metric_key LIKE 'pool_%' OR metric_key LIKE 'clear_water_pool_%')
  AND allowed_device_types = '{}'::text[];

-- 显示更新后的状态
SELECT '=== 更新后状态 ===' AS info;
SELECT 
    metric_key,
    method_id,
    allowed_device_types,
    CASE 
        WHEN allowed_device_types = '{}'::text[] THEN '空数组'
        ELSE '已填充'
    END AS status
FROM calculation_method_registry
ORDER BY metric_key, method_id;

-- 验证：检查是否还有空数组
SELECT '=== 验证结果 ===' AS info;
SELECT COUNT(*) AS remaining_empty_count
FROM calculation_method_registry
WHERE allowed_device_types = '{}'::text[];

-- 如果还有空数组，显示详细信息
SELECT '=== 剩余空数组记录（如果有）===' AS info;
SELECT 
    metric_key,
    method_id,
    allowed_device_types
FROM calculation_method_registry
WHERE allowed_device_types = '{}'::text[]
ORDER BY metric_key, method_id;

COMMIT;

-- 执行完成提示
SELECT '=== 执行完成 ===' AS info;
SELECT 
    '脚本执行成功，所有符合规则的记录已更新' AS message,
    NOW() AS completed_at;

