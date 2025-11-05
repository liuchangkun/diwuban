-- Add missing parameters for 10 methods
-- Solution 6: Parameter System Fix
-- Created: 2025-10-26
-- Version: v1.0

-- Note: pump_inlet_pressure_method_b parameters were already added in fix 1.2
-- This script adds parameters for the remaining 9 methods

-- 1. pump_flow_rate_method_d
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value,
    param_type, is_optimizable, confidence_score, updated_by
) VALUES
(NULL, NULL, 'pump_flow_rate', 'pump_flow_rate_method_d', 'p_thr', 0.5, 'float', TRUE, 0.5, 'manual_fix_6')
ON CONFLICT DO NOTHING;

-- 2. pump_flow_rate_method_e
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value,
    param_type, is_optimizable, confidence_score, updated_by
) VALUES
(NULL, NULL, 'pump_flow_rate', 'pump_flow_rate_method_e', 'f_thr', 3.0, 'float', TRUE, 0.5, 'manual_fix_6')
ON CONFLICT DO NOTHING;

-- 3. pump_flow_rate_method_f
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value,
    param_type, is_optimizable, confidence_score, updated_by
) VALUES
(NULL, NULL, 'pump_flow_rate', 'pump_flow_rate_method_f', 'a0', 0.0, 'float', TRUE, 0.5, 'manual_fix_6'),
(NULL, NULL, 'pump_flow_rate', 'pump_flow_rate_method_f', 'a1', 1.0, 'float', TRUE, 0.5, 'manual_fix_6'),
(NULL, NULL, 'pump_flow_rate', 'pump_flow_rate_method_f', 'a2', 1.0, 'float', TRUE, 0.5, 'manual_fix_6'),
(NULL, NULL, 'pump_flow_rate', 'pump_flow_rate_method_f', 'a3', 0.0, 'float', TRUE, 0.5, 'manual_fix_6')
ON CONFLICT DO NOTHING;

-- 4. pump_outlet_pressure_method_c
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value,
    param_type, is_optimizable, confidence_score, updated_by
) VALUES
(NULL, NULL, 'pump_outlet_pressure', 'pump_outlet_pressure_method_c', 'rho', 1000.0, 'float', FALSE, 1.0, 'manual_fix_6'),
(NULL, NULL, 'pump_outlet_pressure', 'pump_outlet_pressure_method_c', 'g', 9.80665, 'float', FALSE, 1.0, 'manual_fix_6')
ON CONFLICT DO NOTHING;

-- 5. main_pipeline_inlet_pressure_method_b
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value,
    param_type, is_optimizable, confidence_score, updated_by
) VALUES
(NULL, NULL, 'main_pipeline_inlet_pressure', 'main_pipeline_inlet_pressure_method_b', 'P_atm', 0.101325, 'float', FALSE, 1.0, 'manual_fix_6'),
(NULL, NULL, 'main_pipeline_inlet_pressure', 'main_pipeline_inlet_pressure_method_b', 'rho', 1000.0, 'float', FALSE, 1.0, 'manual_fix_6'),
(NULL, NULL, 'main_pipeline_inlet_pressure', 'main_pipeline_inlet_pressure_method_b', 'g', 9.80665, 'float', FALSE, 1.0, 'manual_fix_6')
ON CONFLICT DO NOTHING;

-- 6. main_pipeline_outlet_pressure_method_b
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value,
    param_type, is_optimizable, confidence_score, updated_by
) VALUES
(NULL, NULL, 'main_pipeline_outlet_pressure', 'main_pipeline_outlet_pressure_method_b', 'rho', 1000.0, 'float', FALSE, 1.0, 'manual_fix_6'),
(NULL, NULL, 'main_pipeline_outlet_pressure', 'main_pipeline_outlet_pressure_method_b', 'g', 9.80665, 'float', FALSE, 1.0, 'manual_fix_6')
ON CONFLICT DO NOTHING;

-- 7. pump_cumulative_flow_method_a
INSERT INTO calculation_parameters (
    station_id, device_id, metric_key, method_id, param_name, param_value,
    param_type, is_optimizable, confidence_score, updated_by
) VALUES
(NULL, NULL, 'pump_cumulative_flow', 'pump_cumulative_flow_method_a', 'initial_value', 0.0, 'float', FALSE, 1.0, 'manual_fix_6'),
(NULL, NULL, 'pump_cumulative_flow', 'pump_cumulative_flow_method_a', 'time_interval', 1.0, 'float', FALSE, 1.0, 'manual_fix_6')
ON CONFLICT DO NOTHING;

-- Note: main_pipeline_inlet_pressure_method_c and main_pipeline_outlet_pressure_method_c
-- use aggregation_method parameter which is a string type
-- The calculation_parameters table only supports NUMERIC param_value
-- These parameters will be handled in code as hardcoded defaults for now
-- Future enhancement: Add param_value_text column to support string parameters

-- Verify the insertions
SELECT
    method_id,
    COUNT(*) as param_count,
    array_agg(param_name ORDER BY param_name) as params
FROM calculation_parameters
WHERE updated_by = 'manual_fix_6'
GROUP BY method_id
ORDER BY method_id;

