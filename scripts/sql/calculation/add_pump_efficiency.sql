-- 添加pump_efficiency（泵效率）计算方法
-- 
-- 执行方式:
--   psql -U postgres -d pump_station_optimization -f scripts/sql/calculation/add_pump_efficiency.sql
--
-- 或通过Python:
--   python -m app.cli.main calc init-methods

-- 删除已存在的pump_efficiency方法（如果有）
DELETE FROM calculation_method_registry
WHERE metric_key = 'pump_efficiency';

-- 插入pump_efficiency的计算方法
INSERT INTO calculation_method_registry (
    metric_key,
    method_code,
    method_name,
    method_id,
    dependencies,
    priority,
    conditions,
    formula_ref,
    accuracy_level,
    is_enabled
) VALUES (
    'pump_efficiency',
    'MAIN',
    '基于功率、流量和扬程计算泵效率',
    'pump_efficiency_method_main',
    ARRAY['pump_flow_rate', 'pump_head', 'pump_active_power'],
    100,
    '{}'::jsonb,
    'η = (ρ × g × Q × H) / (1000 × P), 其中ρ=1000 kg/m³, g=9.80665 m/s², 效率范围0.3-0.9',
    'HIGH',
    true
);

-- 验证插入结果
SELECT 
    metric_key,
    method_code,
    method_name,
    method_id,
    dependencies,
    priority
FROM calculation_method_registry
WHERE metric_key = 'pump_efficiency'
ORDER BY priority DESC;

