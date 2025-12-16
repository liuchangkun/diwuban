-- =====================================================
-- 修复 metric_key 大小写不一致问题
-- =====================================================
-- 
-- 问题描述：
--   dim_metric_config 表中存在大小写不一致的 metric_key：
--   - pump_Inlet_pressure (应为 pump_inlet_pressure)
--   - main_pipeline_Inlet_pressure (应为 main_pipeline_inlet_pressure)
--
-- 影响范围：
--   - MetricMapper 无法找到对应的 metric_id
--   - 计算方法的依赖检查失败
--   - 数据加载失败
--
-- 解决方案：
--   将所有 metric_key 统一为小写+下划线格式
--
-- 执行前检查：
--   SELECT id, metric_key FROM dim_metric_config WHERE metric_key != LOWER(metric_key);
--
-- 执行后验证：
--   SELECT id, metric_key FROM dim_metric_config WHERE metric_key != LOWER(metric_key);
--   -- 应该返回 0 行
--
-- =====================================================

BEGIN;

-- 备份原始数据（可选，如果需要回滚）
-- CREATE TEMP TABLE dim_metric_config_backup AS SELECT * FROM dim_metric_config;

-- 更新 pump_Inlet_pressure -> pump_inlet_pressure
UPDATE dim_metric_config
SET metric_key = 'pump_inlet_pressure'
WHERE metric_key = 'pump_Inlet_pressure';

-- 更新 main_pipeline_Inlet_pressure -> main_pipeline_inlet_pressure
UPDATE dim_metric_config
SET metric_key = 'main_pipeline_inlet_pressure'
WHERE metric_key = 'main_pipeline_Inlet_pressure';

-- 验证：检查是否还有大小写不一致的 metric_key
DO $$
DECLARE
    inconsistent_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO inconsistent_count
    FROM dim_metric_config
    WHERE metric_key != LOWER(metric_key);
    
    IF inconsistent_count > 0 THEN
        RAISE EXCEPTION '仍有 % 个 metric_key 存在大小写不一致问题', inconsistent_count;
    ELSE
        RAISE NOTICE '✅ 所有 metric_key 已统一为小写格式';
    END IF;
END $$;

COMMIT;

-- 显示修改结果
SELECT 
    id, 
    metric_key,
    CASE 
        WHEN metric_key = 'pump_inlet_pressure' THEN '✅ 已修复 (原: pump_Inlet_pressure)'
        WHEN metric_key = 'main_pipeline_inlet_pressure' THEN '✅ 已修复 (原: main_pipeline_Inlet_pressure)'
        ELSE '无需修改'
    END as status
FROM dim_metric_config
WHERE id IN (13, 61)
ORDER BY id;

