-- ============================================
-- 为现有外键约束添加级联更新规则
-- 方案7：外键约束级联更新修复
-- 执行时间：2025-10-26
-- ============================================

BEGIN;

-- 1. calculation_parameters 表（3个外键）
ALTER TABLE calculation_parameters
DROP CONSTRAINT IF EXISTS calculation_parameters_device_id_fkey,
ADD CONSTRAINT calculation_parameters_device_id_fkey
    FOREIGN KEY (device_id) REFERENCES dim_devices(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE calculation_parameters
DROP CONSTRAINT IF EXISTS calculation_parameters_station_id_fkey,
ADD CONSTRAINT calculation_parameters_station_id_fkey
    FOREIGN KEY (station_id) REFERENCES dim_stations(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE calculation_parameters
DROP CONSTRAINT IF EXISTS calculation_parameters_metric_key_fkey,
ADD CONSTRAINT calculation_parameters_metric_key_fkey
    FOREIGN KEY (metric_key) REFERENCES dim_metric_config(metric_key)
    ON UPDATE CASCADE ON DELETE CASCADE;

-- 2. device_rated_params 表（1个外键）
ALTER TABLE device_rated_params
DROP CONSTRAINT IF EXISTS device_rated_params_device_id_fkey,
ADD CONSTRAINT device_rated_params_device_id_fkey
    FOREIGN KEY (device_id) REFERENCES dim_devices(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

-- 3. completion_runs 表（2个外键）
ALTER TABLE completion_runs
DROP CONSTRAINT IF EXISTS completion_runs_device_id_fkey,
ADD CONSTRAINT completion_runs_device_id_fkey
    FOREIGN KEY (device_id) REFERENCES dim_devices(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE completion_runs
DROP CONSTRAINT IF EXISTS completion_runs_station_id_fkey,
ADD CONSTRAINT completion_runs_station_id_fkey
    FOREIGN KEY (station_id) REFERENCES dim_stations(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

-- 4. completion_steps 表（1个外键）
ALTER TABLE completion_steps
DROP CONSTRAINT IF EXISTS completion_steps_device_id_fkey,
ADD CONSTRAINT completion_steps_device_id_fkey
    FOREIGN KEY (device_id) REFERENCES dim_devices(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

-- 5. device_running_thresholds_shadow 表（1个外键）
ALTER TABLE device_running_thresholds_shadow
DROP CONSTRAINT IF EXISTS device_running_thresholds_shadow_device_id_fkey,
ADD CONSTRAINT device_running_thresholds_shadow_device_id_fkey
    FOREIGN KEY (device_id) REFERENCES dim_devices(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

-- 6. dim_device_capabilities 表（1个外键）
ALTER TABLE dim_device_capabilities
DROP CONSTRAINT IF EXISTS dim_device_capabilities_device_id_fkey,
ADD CONSTRAINT dim_device_capabilities_device_id_fkey
    FOREIGN KEY (device_id) REFERENCES dim_devices(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

-- 7. dim_devices 表（1个外键）
ALTER TABLE dim_devices
DROP CONSTRAINT IF EXISTS dim_devices_station_id_fkey,
ADD CONSTRAINT dim_devices_station_id_fkey
    FOREIGN KEY (station_id) REFERENCES dim_stations(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

-- 8. dim_metric_metadata 表（1个外键）
ALTER TABLE dim_metric_metadata
DROP CONSTRAINT IF EXISTS dim_metric_metadata_metric_id_fkey,
ADD CONSTRAINT dim_metric_metadata_metric_id_fkey
    FOREIGN KEY (metric_id) REFERENCES dim_metric_config(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

-- 9. dim_metric_metadata_override 表（3个外键）
ALTER TABLE dim_metric_metadata_override
DROP CONSTRAINT IF EXISTS dim_metric_metadata_override_device_id_fkey,
ADD CONSTRAINT dim_metric_metadata_override_device_id_fkey
    FOREIGN KEY (device_id) REFERENCES dim_devices(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE dim_metric_metadata_override
DROP CONSTRAINT IF EXISTS dim_metric_metadata_override_station_id_fkey,
ADD CONSTRAINT dim_metric_metadata_override_station_id_fkey
    FOREIGN KEY (station_id) REFERENCES dim_stations(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE dim_metric_metadata_override
DROP CONSTRAINT IF EXISTS dim_metric_metadata_override_metric_id_fkey,
ADD CONSTRAINT dim_metric_metadata_override_metric_id_fkey
    FOREIGN KEY (metric_id) REFERENCES dim_metric_config(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

-- 10. metric_quality_rules_shadow 表（3个外键）
ALTER TABLE metric_quality_rules_shadow
DROP CONSTRAINT IF EXISTS metric_quality_rules_shadow_device_id_fkey,
ADD CONSTRAINT metric_quality_rules_shadow_device_id_fkey
    FOREIGN KEY (device_id) REFERENCES dim_devices(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE metric_quality_rules_shadow
DROP CONSTRAINT IF EXISTS metric_quality_rules_shadow_station_id_fkey,
ADD CONSTRAINT metric_quality_rules_shadow_station_id_fkey
    FOREIGN KEY (station_id) REFERENCES dim_stations(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE metric_quality_rules_shadow
DROP CONSTRAINT IF EXISTS metric_quality_rules_shadow_metric_id_fkey,
ADD CONSTRAINT metric_quality_rules_shadow_metric_id_fkey
    FOREIGN KEY (metric_id) REFERENCES dim_metric_config(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

-- 11. metric_rule_auto_baseline_shadow 表（3个外键）
ALTER TABLE metric_rule_auto_baseline_shadow
DROP CONSTRAINT IF EXISTS metric_rule_auto_baseline_shadow_device_id_fkey,
ADD CONSTRAINT metric_rule_auto_baseline_shadow_device_id_fkey
    FOREIGN KEY (device_id) REFERENCES dim_devices(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE metric_rule_auto_baseline_shadow
DROP CONSTRAINT IF EXISTS metric_rule_auto_baseline_shadow_station_id_fkey,
ADD CONSTRAINT metric_rule_auto_baseline_shadow_station_id_fkey
    FOREIGN KEY (station_id) REFERENCES dim_stations(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE metric_rule_auto_baseline_shadow
DROP CONSTRAINT IF EXISTS metric_rule_auto_baseline_shadow_metric_id_fkey,
ADD CONSTRAINT metric_rule_auto_baseline_shadow_metric_id_fkey
    FOREIGN KEY (metric_id) REFERENCES dim_metric_config(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

-- 12. calculation_method_registry 表（1个外键）
ALTER TABLE calculation_method_registry
DROP CONSTRAINT IF EXISTS calculation_method_registry_metric_key_fkey,
ADD CONSTRAINT calculation_method_registry_metric_key_fkey
    FOREIGN KEY (metric_key) REFERENCES dim_metric_config(metric_key)
    ON UPDATE CASCADE ON DELETE CASCADE;

-- 13. dim_mapping_items 表（1个外键）
ALTER TABLE dim_mapping_items
DROP CONSTRAINT IF EXISTS dim_mapping_items_metric_key_fkey,
ADD CONSTRAINT dim_mapping_items_metric_key_fkey
    FOREIGN KEY (metric_key) REFERENCES dim_metric_config(metric_key)
    ON UPDATE CASCADE ON DELETE CASCADE;

-- 14. metric_calculation_order 表（1个外键）
ALTER TABLE metric_calculation_order
DROP CONSTRAINT IF EXISTS metric_calculation_order_metric_key_fkey,
ADD CONSTRAINT metric_calculation_order_metric_key_fkey
    FOREIGN KEY (metric_key) REFERENCES dim_metric_config(metric_key)
    ON UPDATE CASCADE ON DELETE CASCADE;

COMMIT;

-- 验证修改
SELECT 
    tc.table_name, 
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    rc.update_rule,
    rc.delete_rule
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
JOIN information_schema.referential_constraints AS rc
  ON rc.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND ccu.table_name IN ('dim_stations', 'dim_devices', 'dim_metric_config')
  AND rc.update_rule = 'CASCADE'
ORDER BY tc.table_name;

