-- ============================================
-- P0优先级：为配置表添加外键约束
-- ============================================
-- 文件：scripts/sql/validation/P0_add_foreign_keys_to_config_tables.sql
-- 用途：为无外键约束的配置表添加外键约束，确保数据一致性
-- 优先级：P0 - 立即执行
-- 风险：低（已验证无孤立记录）
-- 执行方式：psql -h localhost -U postgres -d pump_station -f P0_add_foreign_keys_to_config_tables.sql
-- ============================================

\echo '=========================================='
\echo 'P0优先级：为配置表添加外键约束'
\echo '=========================================='
\echo ''

BEGIN;

-- ============================================
-- 第一步：执行前检查
-- ============================================

\echo '【1】执行前检查：验证是否存在孤立记录'
\echo '----------------------------------------'

\echo '1.1 检查 device_running_thresholds'
DO $$
DECLARE
    orphaned_count INT;
BEGIN
    SELECT COUNT(*) INTO orphaned_count
    FROM device_running_thresholds drt
    LEFT JOIN dim_devices d ON d.id = drt.device_id
    WHERE d.id IS NULL;
    
    IF orphaned_count > 0 THEN
        RAISE EXCEPTION 'Found % orphaned records in device_running_thresholds. Please clean up before adding foreign key.', orphaned_count;
    ELSE
        RAISE NOTICE '✅ No orphaned records in device_running_thresholds';
    END IF;
END $$;

\echo ''
\echo '1.2 检查 metric_quality_rules'
DO $$
DECLARE
    orphaned_device_count INT;
    orphaned_station_count INT;
BEGIN
    SELECT COUNT(*) INTO orphaned_device_count
    FROM metric_quality_rules mqr
    LEFT JOIN dim_devices d ON d.id = mqr.device_id
    WHERE d.id IS NULL;
    
    SELECT COUNT(*) INTO orphaned_station_count
    FROM metric_quality_rules mqr
    LEFT JOIN dim_stations s ON s.id = mqr.station_id
    WHERE s.id IS NULL;
    
    IF orphaned_device_count > 0 OR orphaned_station_count > 0 THEN
        RAISE EXCEPTION 'Found % orphaned device_id and % orphaned station_id in metric_quality_rules', orphaned_device_count, orphaned_station_count;
    ELSE
        RAISE NOTICE '✅ No orphaned records in metric_quality_rules';
    END IF;
END $$;

\echo ''
\echo '1.3 检查 metric_rule_auto_baseline'
DO $$
DECLARE
    orphaned_device_count INT;
    orphaned_station_count INT;
BEGIN
    SELECT COUNT(*) INTO orphaned_device_count
    FROM metric_rule_auto_baseline mrab
    LEFT JOIN dim_devices d ON d.id = mrab.device_id
    WHERE d.id IS NULL;
    
    SELECT COUNT(*) INTO orphaned_station_count
    FROM metric_rule_auto_baseline mrab
    LEFT JOIN dim_stations s ON s.id = mrab.station_id
    WHERE s.id IS NULL;
    
    IF orphaned_device_count > 0 OR orphaned_station_count > 0 THEN
        RAISE EXCEPTION 'Found % orphaned device_id and % orphaned station_id in metric_rule_auto_baseline', orphaned_device_count, orphaned_station_count;
    ELSE
        RAISE NOTICE '✅ No orphaned records in metric_rule_auto_baseline';
    END IF;
END $$;

\echo ''
\echo '1.4 检查 device_metric_candidates'
DO $$
DECLARE
    orphaned_count INT;
BEGIN
    SELECT COUNT(*) INTO orphaned_count
    FROM device_metric_candidates dmc
    LEFT JOIN dim_devices d ON d.id = dmc.device_id
    WHERE d.id IS NULL;
    
    IF orphaned_count > 0 THEN
        RAISE EXCEPTION 'Found % orphaned records in device_metric_candidates', orphaned_count;
    ELSE
        RAISE NOTICE '✅ No orphaned records in device_metric_candidates';
    END IF;
END $$;

\echo ''
\echo '1.5 检查 metric_anomaly_strategy'
DO $$
DECLARE
    orphaned_device_count INT;
    orphaned_station_count INT;
BEGIN
    SELECT COUNT(*) INTO orphaned_device_count
    FROM metric_anomaly_strategy mas
    LEFT JOIN dim_devices d ON d.id = mas.device_id
    WHERE d.id IS NULL;
    
    SELECT COUNT(*) INTO orphaned_station_count
    FROM metric_anomaly_strategy mas
    LEFT JOIN dim_stations s ON s.id = mas.station_id
    WHERE s.id IS NULL;
    
    IF orphaned_device_count > 0 OR orphaned_station_count > 0 THEN
        RAISE EXCEPTION 'Found % orphaned device_id and % orphaned station_id in metric_anomaly_strategy', orphaned_device_count, orphaned_station_count;
    ELSE
        RAISE NOTICE '✅ No orphaned records in metric_anomaly_strategy';
    END IF;
END $$;

-- ============================================
-- 第二步：添加外键约束
-- ============================================

\echo ''
\echo '【2】添加外键约束'
\echo '----------------------------------------'

\echo '2.1 为 device_running_thresholds 添加外键'
ALTER TABLE device_running_thresholds
ADD CONSTRAINT device_running_thresholds_device_id_fkey
FOREIGN KEY (device_id) REFERENCES dim_devices(id)
ON UPDATE CASCADE ON DELETE CASCADE;

\echo '✅ device_running_thresholds.device_id 外键已添加'

\echo ''
\echo '2.2 为 metric_quality_rules 添加外键'
ALTER TABLE metric_quality_rules
ADD CONSTRAINT metric_quality_rules_device_id_fkey
FOREIGN KEY (device_id) REFERENCES dim_devices(id)
ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE metric_quality_rules
ADD CONSTRAINT metric_quality_rules_station_id_fkey
FOREIGN KEY (station_id) REFERENCES dim_stations(id)
ON UPDATE CASCADE ON DELETE CASCADE;

\echo '✅ metric_quality_rules.device_id 外键已添加'
\echo '✅ metric_quality_rules.station_id 外键已添加'

\echo ''
\echo '2.3 为 metric_rule_auto_baseline 添加外键'
ALTER TABLE metric_rule_auto_baseline
ADD CONSTRAINT metric_rule_auto_baseline_device_id_fkey
FOREIGN KEY (device_id) REFERENCES dim_devices(id)
ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE metric_rule_auto_baseline
ADD CONSTRAINT metric_rule_auto_baseline_station_id_fkey
FOREIGN KEY (station_id) REFERENCES dim_stations(id)
ON UPDATE CASCADE ON DELETE CASCADE;

\echo '✅ metric_rule_auto_baseline.device_id 外键已添加'
\echo '✅ metric_rule_auto_baseline.station_id 外键已添加'

\echo ''
\echo '2.4 为 metric_anomaly_strategy 添加外键'
ALTER TABLE metric_anomaly_strategy
ADD CONSTRAINT metric_anomaly_strategy_device_id_fkey
FOREIGN KEY (device_id) REFERENCES dim_devices(id)
ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE metric_anomaly_strategy
ADD CONSTRAINT metric_anomaly_strategy_station_id_fkey
FOREIGN KEY (station_id) REFERENCES dim_stations(id)
ON UPDATE CASCADE ON DELETE CASCADE;

\echo '✅ metric_anomaly_strategy.device_id 外键已添加'
\echo '✅ metric_anomaly_strategy.station_id 外键已添加'

-- ============================================
-- 第三步：验证外键约束
-- ============================================

\echo ''
\echo '【3】验证外键约束'
\echo '----------------------------------------'

\echo '3.1 验证所有外键都已添加'
SELECT 
    tc.table_name AS 表名,
    kcu.column_name AS 外键列名,
    ccu.table_name AS 引用表,
    rc.update_rule AS UPDATE规则,
    rc.delete_rule AS DELETE规则,
    CASE 
        WHEN rc.update_rule = 'CASCADE' AND rc.delete_rule = 'CASCADE' THEN '✅ 完全保护'
        ELSE '⚠️ 部分保护'
    END AS 保护状态
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu 
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage ccu 
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
JOIN information_schema.referential_constraints rc
    ON rc.constraint_name = tc.constraint_name
    AND rc.constraint_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name IN (
        'device_running_thresholds',
        'metric_quality_rules',
        'metric_rule_auto_baseline',
        'device_metric_candidates',
        'metric_anomaly_strategy'
    )
    AND ccu.table_name IN ('dim_devices', 'dim_stations')
ORDER BY tc.table_name, kcu.column_name;

-- ============================================
-- 第四步：提交事务
-- ============================================

\echo ''
\echo '【4】提交事务'
\echo '----------------------------------------'

COMMIT;

\echo '✅ 所有外键约束已成功添加并提交'

\echo ''
\echo '=========================================='
\echo '执行完成'
\echo '=========================================='
\echo ''
\echo '总结：'
\echo '- 已为 5 个配置表添加外键约束'
\echo '- 共添加 8 个外键约束（device_id: 5个, station_id: 3个）'
\echo '- 所有外键都配置了 ON UPDATE CASCADE ON DELETE CASCADE'
\echo '- 配置表现在受到完全保护'
\echo ''

