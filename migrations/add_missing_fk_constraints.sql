-- ============================================
-- 为缺少外键约束的核心业务表添加约束
-- 方案7：外键约束级联更新修复
-- 执行时间：2025-10-26
-- ============================================

BEGIN;

-- 1. calculation_failures_log 表
ALTER TABLE calculation_failures_log
ADD CONSTRAINT calculation_failures_log_device_id_fkey
    FOREIGN KEY (device_id) REFERENCES dim_devices(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE calculation_failures_log
ADD CONSTRAINT calculation_failures_log_station_id_fkey
    FOREIGN KEY (station_id) REFERENCES dim_stations(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

-- 2. calculation_performance_metrics 表
ALTER TABLE calculation_performance_metrics
ADD CONSTRAINT calculation_performance_metrics_device_id_fkey
    FOREIGN KEY (device_id) REFERENCES dim_devices(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE calculation_performance_metrics
ADD CONSTRAINT calculation_performance_metrics_station_id_fkey
    FOREIGN KEY (station_id) REFERENCES dim_stations(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

-- 3. calculation_validation_config 表
ALTER TABLE calculation_validation_config
ADD CONSTRAINT calculation_validation_config_device_id_fkey
    FOREIGN KEY (device_id) REFERENCES dim_devices(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE calculation_validation_config
ADD CONSTRAINT calculation_validation_config_station_id_fkey
    FOREIGN KEY (station_id) REFERENCES dim_stations(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

-- 4. optimization_history 表
ALTER TABLE optimization_history
ADD CONSTRAINT optimization_history_device_id_fkey
    FOREIGN KEY (device_id) REFERENCES dim_devices(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE optimization_history
ADD CONSTRAINT optimization_history_station_id_fkey
    FOREIGN KEY (station_id) REFERENCES dim_stations(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

-- 5. pump_characteristic_curves 表
ALTER TABLE pump_characteristic_curves
ADD CONSTRAINT pump_characteristic_curves_device_id_fkey
    FOREIGN KEY (device_id) REFERENCES dim_devices(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

-- 6. quality_diagnosis_log 表
ALTER TABLE quality_diagnosis_log
ADD CONSTRAINT quality_diagnosis_log_device_id_fkey
    FOREIGN KEY (device_id) REFERENCES dim_devices(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE quality_diagnosis_log
ADD CONSTRAINT quality_diagnosis_log_station_id_fkey
    FOREIGN KEY (station_id) REFERENCES dim_stations(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

-- 7. quality_profile_log 表
ALTER TABLE quality_profile_log
ADD CONSTRAINT quality_profile_log_device_id_fkey
    FOREIGN KEY (device_id) REFERENCES dim_devices(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE quality_profile_log
ADD CONSTRAINT quality_profile_log_station_id_fkey
    FOREIGN KEY (station_id) REFERENCES dim_stations(id)
    ON UPDATE CASCADE ON DELETE CASCADE;

COMMIT;

-- 验证添加的约束
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
  AND tc.table_name IN (
      'calculation_failures_log',
      'calculation_performance_metrics',
      'calculation_validation_config',
      'optimization_history',
      'pump_characteristic_curves',
      'quality_diagnosis_log',
      'quality_profile_log'
  )
ORDER BY tc.table_name;

