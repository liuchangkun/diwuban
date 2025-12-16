-- ============================================
-- 自适应SQL脚本：metric_anomaly_strategy（异常检测策略配置）
-- ============================================
-- 文件：scripts/sql/adaptive/05_metric_anomaly_strategy.sql
-- 用途：生成 metric_anomaly_strategy 表的全局策略配置
-- 依赖：dim_metric_config 和 dim_stations 表必须已存在且包含数据
-- 特性：自适应关联，使用 metric_key 定位指标，使用实际的 station_id
-- ============================================

BEGIN;

-- 清空表（完全重建）
TRUNCATE TABLE metric_anomaly_strategy CASCADE;

-- ============================================
-- 全局策略配置（使用实际的第一个站点ID作为全局配置）
-- ============================================

-- 获取第一个站点ID（作为全局配置的站点）
DO $$
DECLARE
    global_station_id BIGINT;
BEGIN
    -- 获取第一个站点ID
    SELECT MIN(id) INTO global_station_id FROM dim_stations;
    
    IF global_station_id IS NULL THEN
        RAISE EXCEPTION '没有找到任何站点，无法生成 metric_anomaly_strategy 配置';
    END IF;
    
    RAISE NOTICE '使用站点ID % 作为全局配置', global_station_id;
    
    -- work_condition 策略（工况判定）
    INSERT INTO metric_anomaly_strategy (metric_id, station_id, device_id, strategy, bins, model, deps, hard_bounds_source, enabled, updated_by)
    SELECT 
        mc.id,
        global_station_id,
        0,
        'work_condition',
        '{"f_bin":"1Hz","min_samples":1}'::jsonb,
        NULL,
        NULL,
        'none',
        TRUE,
        'adaptive_sql'
    FROM dim_metric_config mc
    WHERE mc.metric_key IN ('pump_running_status', 'pump_start_count', 'pump_stop_count')
    ON CONFLICT (metric_id, station_id, device_id) DO UPDATE SET
        strategy = EXCLUDED.strategy,
        bins = EXCLUDED.bins,
        model = EXCLUDED.model,
        deps = EXCLUDED.deps,
        hard_bounds_source = EXCLUDED.hard_bounds_source,
        enabled = EXCLUDED.enabled,
        updated_at = now(),
        updated_by = EXCLUDED.updated_by;
    
    -- physics 策略（物理约束）
    INSERT INTO metric_anomaly_strategy (metric_id, station_id, device_id, strategy, bins, model, deps, hard_bounds_source, enabled, updated_by)
    SELECT 
        mc.id,
        global_station_id,
        0,
        'physics',
        NULL,
        NULL,
        CASE 
            WHEN mc.metric_key = 'pump_power_factor' THEN '["PF_range"]'::jsonb
            WHEN mc.metric_key IN ('pump_cumulative_flow', 'pump_cumulative_runtime', 'main_pipeline_cumulative_flow') THEN '["monotonic"]'::jsonb
            ELSE NULL
        END,
        'metadata',
        TRUE,
        'adaptive_sql'
    FROM dim_metric_config mc
    WHERE mc.metric_key IN (
        'pump_voltage', 'pump_current', 'pump_active_power',
        'pump_power_factor', 'pump_cumulative_flow', 'pump_cumulative_runtime',
        'main_pipeline_cumulative_flow'
    )
    ON CONFLICT (metric_id, station_id, device_id) DO UPDATE SET
        strategy = EXCLUDED.strategy,
        bins = EXCLUDED.bins,
        model = EXCLUDED.model,
        deps = EXCLUDED.deps,
        hard_bounds_source = EXCLUDED.hard_bounds_source,
        enabled = EXCLUDED.enabled,
        updated_at = now(),
        updated_by = EXCLUDED.updated_by;
    
    -- residual 策略（残差分析）
    INSERT INTO metric_anomaly_strategy (metric_id, station_id, device_id, strategy, bins, model, deps, hard_bounds_source, enabled, updated_by)
    SELECT 
        mc.id,
        global_station_id,
        0,
        'residual',
        '{"f_bin":"1Hz","min_samples":1}'::jsonb,
        '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb,
        '["f"]'::jsonb,
        'metadata',
        TRUE,
        'adaptive_sql'
    FROM dim_metric_config mc
    WHERE mc.metric_key IN (
        'pool_liquid_level', 'pool_liquid_level_a', 'pool_liquid_level_b',
        'pool_liquid_level_c', 'pool_liquid_level_d', 'pool_liquid_level_e',
        'pool_liquid_level_f', 'pool_liquid_level_g'
    )
    ON CONFLICT (metric_id, station_id, device_id) DO UPDATE SET
        strategy = EXCLUDED.strategy,
        bins = EXCLUDED.bins,
        model = EXCLUDED.model,
        deps = EXCLUDED.deps,
        hard_bounds_source = EXCLUDED.hard_bounds_source,
        enabled = EXCLUDED.enabled,
        updated_at = now(),
        updated_by = EXCLUDED.updated_by;
    
    -- hybrid 策略（混合策略：工况+物理+残差）
    INSERT INTO metric_anomaly_strategy (metric_id, station_id, device_id, strategy, bins, model, deps, hard_bounds_source, enabled, updated_by)
    SELECT 
        mc.id,
        global_station_id,
        0,
        'hybrid',
        '{"f_bin":"1Hz","min_samples":1}'::jsonb,
        CASE 
            WHEN mc.metric_key = 'pump_efficiency' THEN '{"residual":"bin_quantile","q":0.9,"mad_k":4}'::jsonb
            ELSE '{"residual":"bin_quantile","q":0.95,"mad_k":4}'::jsonb
        END,
        CASE 
            WHEN mc.metric_key IN ('pump_frequency', 'pump_inlet_pressure', 'pump_head', 'pump_outlet_pressure') THEN '["U","I","P","PF","f"]'::jsonb
            WHEN mc.metric_key IN ('pump_flow_rate', 'main_pipeline_flow_rate', 'main_pipeline_outlet_pressure', 'main_pipeline_inlet_flow_rate') THEN '["f","Q"]'::jsonb
            WHEN mc.metric_key IN ('pump_speed', 'main_pipeline_inlet_pressure') THEN '["f"]'::jsonb
            WHEN mc.metric_key = 'pump_efficiency' THEN '["f","Q","H"]'::jsonb
            WHEN mc.metric_key = 'pump_torque' THEN '["f"]'::jsonb
            WHEN mc.metric_key = 'pump_shaft_power' THEN '["P","speed"]'::jsonb
            ELSE '["f"]'::jsonb
        END,
        'metadata',
        TRUE,
        'adaptive_sql'
    FROM dim_metric_config mc
    WHERE mc.metric_key IN (
        'pump_frequency', 'pump_inlet_pressure', 'pump_head', 'pump_outlet_pressure',
        'pump_flow_rate', 'pump_speed', 'pump_efficiency', 'pump_torque', 'pump_shaft_power',
        'main_pipeline_flow_rate', 'main_pipeline_inlet_pressure', 'main_pipeline_outlet_pressure',
        'main_pipeline_inlet_flow_rate'
    )
    ON CONFLICT (metric_id, station_id, device_id) DO UPDATE SET
        strategy = EXCLUDED.strategy,
        bins = EXCLUDED.bins,
        model = EXCLUDED.model,
        deps = EXCLUDED.deps,
        hard_bounds_source = EXCLUDED.hard_bounds_source,
        enabled = EXCLUDED.enabled,
        updated_at = now(),
        updated_by = EXCLUDED.updated_by;

END $$;

COMMIT;

-- ============================================
-- 说明
-- ============================================
-- 此脚本使用第一个站点ID作为全局配置的站点ID（而不是硬编码的0）
-- 这样可以满足外键约束，同时保持全局配置的语义（device_id=0）
--
-- 策略分类：
-- - work_condition: 工况判定（运行状态、启停次数等）
-- - physics: 物理约束（电压、电流、功率因数等）
-- - residual: 残差分析（液位等）
-- - hybrid: 混合策略（流量、扬程、效率等）
--
-- 自适应关联的关键点：
-- - 使用 JOIN dim_metric_config mc WHERE mc.metric_key IN (...) 获取 metric_id
-- - 使用 SELECT MIN(id) FROM dim_stations 获取第一个站点ID
-- - 使用 device_id=0 表示全局配置（适用于所有设备）
-- ============================================

