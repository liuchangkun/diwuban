-- =====================================================================
-- 回滚脚本：删除所有错误的注释
-- =====================================================================

-- 删除表注释
COMMENT ON TABLE device_rated_params IS NULL;
COMMENT ON TABLE calculation_parameters IS NULL;
COMMENT ON TABLE fact_measurements IS NULL;
COMMENT ON TABLE global_default_rated_params IS NULL;
COMMENT ON TABLE dim_stations IS NULL;
COMMENT ON TABLE dim_devices IS NULL;
COMMENT ON TABLE dim_metric_config IS NULL;

-- 删除字段注释
COMMENT ON COLUMN global_default_rated_params.param_key IS NULL;
COMMENT ON COLUMN global_default_rated_params.default_value IS NULL;
COMMENT ON COLUMN global_default_rated_params.param_unit IS NULL;
COMMENT ON COLUMN global_default_rated_params.description IS NULL;
COMMENT ON COLUMN global_default_rated_params.created_at IS NULL;
COMMENT ON COLUMN global_default_rated_params.updated_at IS NULL;
COMMENT ON COLUMN global_default_rated_params.created_by IS NULL;

COMMENT ON COLUMN fact_measurements.quality_codes IS NULL;

COMMENT ON COLUMN calculation_parameters.id IS NULL;
COMMENT ON COLUMN calculation_parameters.station_id IS NULL;
COMMENT ON COLUMN calculation_parameters.device_id IS NULL;
COMMENT ON COLUMN calculation_parameters.metric_key IS NULL;
COMMENT ON COLUMN calculation_parameters.method_id IS NULL;
COMMENT ON COLUMN calculation_parameters.param_name IS NULL;
COMMENT ON COLUMN calculation_parameters.param_value IS NULL;
COMMENT ON COLUMN calculation_parameters.param_type IS NULL;
COMMENT ON COLUMN calculation_parameters.is_optimizable IS NULL;
COMMENT ON COLUMN calculation_parameters.param_min IS NULL;
COMMENT ON COLUMN calculation_parameters.param_max IS NULL;
COMMENT ON COLUMN calculation_parameters.created_at IS NULL;
COMMENT ON COLUMN calculation_parameters.updated_at IS NULL;
COMMENT ON COLUMN calculation_parameters.updated_by IS NULL;

COMMENT ON COLUMN dim_stations.is_active IS NULL;
COMMENT ON COLUMN dim_devices.is_active IS NULL;

-- 删除其他表的字段注释
COMMENT ON COLUMN calculation_method_registry.method_id IS NULL;
COMMENT ON COLUMN calculation_method_registry.metric_key IS NULL;
COMMENT ON COLUMN calculation_method_registry.method_name IS NULL;
COMMENT ON COLUMN calculation_method_registry.method_code IS NULL;
COMMENT ON COLUMN calculation_method_registry.priority IS NULL;
COMMENT ON COLUMN calculation_method_registry.created_at IS NULL;
COMMENT ON COLUMN calculation_method_registry.updated_at IS NULL;

COMMENT ON COLUMN calculation_failures_log.id IS NULL;
COMMENT ON COLUMN calculation_failures_log.device_id IS NULL;
COMMENT ON COLUMN calculation_failures_log.metric_key IS NULL;
COMMENT ON COLUMN calculation_failures_log.method_id IS NULL;
COMMENT ON COLUMN calculation_failures_log.error_message IS NULL;
COMMENT ON COLUMN calculation_failures_log.created_at IS NULL;

COMMENT ON COLUMN completion_audit.id IS NULL;
COMMENT ON COLUMN completion_audit.run_id IS NULL;
COMMENT ON COLUMN completion_audit.created_at IS NULL;

COMMENT ON COLUMN completion_failures.id IS NULL;
COMMENT ON COLUMN completion_failures.run_id IS NULL;
COMMENT ON COLUMN completion_failures.created_at IS NULL;

COMMENT ON COLUMN completion_runs.station_id IS NULL;
COMMENT ON COLUMN completion_runs.device_id IS NULL;
COMMENT ON COLUMN completion_runs.created_at IS NULL;

COMMENT ON COLUMN completion_steps.id IS NULL;
COMMENT ON COLUMN completion_steps.run_id IS NULL;
COMMENT ON COLUMN completion_steps.device_id IS NULL;
COMMENT ON COLUMN completion_steps.metric_id IS NULL;
COMMENT ON COLUMN completion_steps.created_at IS NULL;

COMMENT ON COLUMN metric_calculation_order.metric_key IS NULL;
COMMENT ON COLUMN metric_calculation_order.depends_on IS NULL;
COMMENT ON COLUMN metric_calculation_order.created_at IS NULL;
COMMENT ON COLUMN metric_calculation_order.updated_at IS NULL;

COMMENT ON COLUMN optimization_history.id IS NULL;
COMMENT ON COLUMN optimization_history.device_id IS NULL;
COMMENT ON COLUMN optimization_history.metric_key IS NULL;
COMMENT ON COLUMN optimization_history.method_id IS NULL;
COMMENT ON COLUMN optimization_history.created_at IS NULL;

COMMENT ON COLUMN quality_code_dict.code IS NULL;
COMMENT ON COLUMN quality_code_dict.description IS NULL;
COMMENT ON COLUMN quality_code_dict.severity IS NULL;
COMMENT ON COLUMN quality_code_dict.category IS NULL;

COMMENT ON COLUMN quality_diagnosis_log.id IS NULL;
COMMENT ON COLUMN quality_diagnosis_log.device_id IS NULL;
COMMENT ON COLUMN quality_diagnosis_log.created_at IS NULL;

COMMENT ON COLUMN quality_eval_by_device_metric.device_id IS NULL;
COMMENT ON COLUMN quality_eval_by_device_metric.metric_id IS NULL;
COMMENT ON COLUMN quality_eval_by_device_metric.created_at IS NULL;

COMMENT ON COLUMN quality_profile_log.id IS NULL;
COMMENT ON COLUMN quality_profile_log.device_id IS NULL;
COMMENT ON COLUMN quality_profile_log.created_at IS NULL;

