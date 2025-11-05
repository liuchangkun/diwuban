-- Add parameters for remaining 2 methods (string parameters)
-- Solution 6: Parameter System Fix - Step 3 (Remaining 2 methods)
-- Created: 2025-10-26
-- Version: v2.0
-- Note: pump_inlet_pressure_method_b is excluded because it's not registered in calculation_method_registry

-- 1. main_pipeline_inlet_pressure_method_c (aggregation_method='mean')
-- Use param_value=0 as placeholder (actual value in param_value_text)
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_value_text,
    param_type, is_optimizable, confidence_score, updated_by
) VALUES
(NULL, NULL, 'main_pipeline_inlet_pressure', 'main_pipeline_inlet_pressure_method_c', 'aggregation_method', 0, 'mean', 'string', FALSE, 1.0, 'manual_fix_6_step3')
ON CONFLICT DO NOTHING;

-- 2. main_pipeline_outlet_pressure_method_c (aggregation_method='max')
-- Use param_value=0 as placeholder (actual value in param_value_text)
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value, param_value_text,
    param_type, is_optimizable, confidence_score, updated_by
) VALUES
(NULL, NULL, 'main_pipeline_outlet_pressure', 'main_pipeline_outlet_pressure_method_c', 'aggregation_method', 0, 'max', 'string', FALSE, 1.0, 'manual_fix_6_step3')
ON CONFLICT DO NOTHING;

-- Verify the insertions
SELECT
    method_id,
    param_name,
    param_value,
    param_value_text,
    param_type,
    updated_by
FROM calculation_parameters
WHERE updated_by = 'manual_fix_6_step3'
ORDER BY method_id, param_name;

-- Verify total count for all 10 methods
SELECT
    method_id,
    COUNT(*) as param_count,
    array_agg(param_name ORDER BY param_name) as params
FROM calculation_parameters
WHERE updated_by IN ('manual_fix_6', 'manual_fix_6_step3')
GROUP BY method_id
ORDER BY method_id;

