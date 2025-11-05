-- =====================================================
-- 添加缺失的指标到dim_metric_config表
-- =====================================================
-- 创建时间: 2025-10-05
-- 用途: 确保所有需要计算的指标都在dim_metric_config表中
-- =====================================================

-- 修复ID序列（如果需要）
SELECT setval('dim_metric_config_id_seq', (SELECT COALESCE(MAX(id), 0) FROM dim_metric_config), true);

-- main_pipeline_inlet_pressure - 总管进口压力
-- 先检查是否存在
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM dim_metric_config WHERE metric_key = 'main_pipeline_inlet_pressure') THEN
        INSERT INTO dim_metric_config (metric_key, unit, unit_display, decimals_policy, fixed_decimals, value_type, valid_min, valid_max)
        VALUES ('main_pipeline_inlet_pressure', 'MPa', 'MPa', 'fixed', 3, 'float', 0, 2);
        RAISE NOTICE '已添加指标: main_pipeline_inlet_pressure';
    ELSE
        RAISE NOTICE '指标已存在: main_pipeline_inlet_pressure';
    END IF;
END $$;

-- 验证所有新增指标都存在
SELECT '所有新增指标已添加到dim_metric_config表！' AS message,
       COUNT(*) AS total_metrics
FROM dim_metric_config
WHERE metric_key IN ('pump_speed', 'pump_torque', 'main_pipeline_outlet_pressure', 
                     'main_pipeline_inlet_pressure', 'pump_cumulative_flow');

