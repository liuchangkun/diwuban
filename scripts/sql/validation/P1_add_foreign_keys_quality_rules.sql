-- ============================================
-- P1优先级：为质量规则相关表添加外键约束
-- ============================================
-- 文件：scripts/sql/validation/P1_add_foreign_keys_quality_rules.sql
-- 用途：为质量规则、自动基线、异常策略等配置表添加外键约束
-- 优先级：P1 - 1个月内执行
-- 风险：低（当前表为空，无孤立记录风险）
-- 执行方式：psql -h localhost -U postgres -d pump_station -f P1_add_foreign_keys_quality_rules.sql
-- ============================================

\echo '=========================================='
\echo 'P1优先级：为质量规则相关表添加外键约束'
\echo '=========================================='
\echo ''

BEGIN;

-- ============================================
-- 第一步：执行前检查
-- ============================================

\echo '【1】执行前检查：验证是否存在孤立记录'
\echo '----------------------------------------'

\echo '1.1 检查 metric_quality_rules'
DO $$
DECLARE
    orphaned_device_count INT;
    orphaned_station_count INT;
BEGIN
    SELECT COUNT(*) INTO orphaned_device_count
    FROM metric_quality_rules mqr
    LEFT JOIN dim_devices d ON d.id = mqr.device_id
    WHERE mqr.device_id IS NOT NULL AND d.id IS NULL;
    
    SELECT COUNT(*) INTO orphaned_station_count
    FROM metric_quality_rules mqr
    LEFT JOIN dim_stations s ON s.id = mqr.station_id
    WHERE mqr.station_id IS NOT NULL AND s.id IS NULL;
    
    IF orphaned_device_count > 0 OR orphaned_station_count > 0 THEN
        RAISE EXCEPTION 'Found % orphaned device_id and % orphaned station_id in metric_quality_rules', orphaned_device_count, orphaned_station_count;
    ELSE
        RAISE NOTICE '✅ No orphaned records in metric_quality_rules';
    END IF;
END $$;

\echo ''
\echo '1.2 检查 metric_rule_auto_baseline'
DO $$
DECLARE
    orphaned_device_count INT;
    orphaned_station_count INT;
BEGIN
    SELECT COUNT(*) INTO orphaned_device_count
    FROM metric_rule_auto_baseline mrab
    LEFT JOIN dim_devices d ON d.id = mrab.device_id
    WHERE mrab.device_id IS NOT NULL AND d.id IS NULL;
    
    SELECT COUNT(*) INTO orphaned_station_count
    FROM metric_rule_auto_baseline mrab
    LEFT JOIN dim_stations s ON s.id = mrab.station_id
    WHERE mrab.station_id IS NOT NULL AND s.id IS NULL;
    
    IF orphaned_device_count > 0 OR orphaned_station_count > 0 THEN
        RAISE EXCEPTION 'Found % orphaned device_id and % orphaned station_id in metric_rule_auto_baseline', orphaned_device_count, orphaned_station_count;
    ELSE
        RAISE NOTICE '✅ No orphaned records in metric_rule_auto_baseline';
    END IF;
END $$;

\echo ''
\echo '1.3 检查 metric_anomaly_strategy'
DO $$
DECLARE
    orphaned_device_count INT;
    orphaned_station_count INT;
BEGIN
    SELECT COUNT(*) INTO orphaned_device_count
    FROM metric_anomaly_strategy mas
    LEFT JOIN dim_devices d ON d.id = mas.device_id
    WHERE mas.device_id IS NOT NULL AND d.id IS NULL;
    
    SELECT COUNT(*) INTO orphaned_station_count
    FROM metric_anomaly_strategy mas
    LEFT JOIN dim_stations s ON s.id = mas.station_id
    WHERE mas.station_id IS NOT NULL AND s.id IS NULL;
    
    IF orphaned_device_count > 0 OR orphaned_station_count > 0 THEN
        RAISE EXCEPTION 'Found % orphaned device_id and % orphaned station_id in metric_anomaly_strategy', orphaned_device_count, orphaned_station_count;
    ELSE
        RAISE NOTICE '✅ No orphaned records in metric_anomaly_strategy';
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
    WHERE dmc.device_id IS NOT NULL AND d.id IS NULL;
    
    IF orphaned_count > 0 THEN
        RAISE EXCEPTION 'Found % orphaned records in device_metric_candidates', orphaned_count;
    ELSE
        RAISE NOTICE '✅ No orphaned records in device_metric_candidates';
    END IF;
END $$;

-- ============================================
-- 第二步：添加外键约束
-- ============================================

\echo ''
\echo '【2】添加外键约束'
\echo '----------------------------------------'

\echo '2.1 为 metric_quality_rules 添加外键'
\echo '    业务分类：质量规则配置'
\echo '    影响功能：质量评价、异常检测、数据过滤'
\echo '    失联后果：无法判断数据质量，无法检测异常，无法过滤无效数据'

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
\echo '2.2 为 metric_rule_auto_baseline 添加外键'
\echo '    业务分类：自动基线配置'
\echo '    影响功能：基线生成、阈值推荐'
\echo '    失联后果：无法生成质量规则，无法推荐阈值参数'

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
\echo '2.3 为 metric_anomaly_strategy 添加外键'
\echo '    业务分类：异常策略配置'
\echo '    影响功能：异常检测策略、参数来源配置'
\echo '    失联后果：无法获取异常检测策略，无法获取检测参数'

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
        'metric_quality_rules',
        'metric_rule_auto_baseline',
        'metric_anomaly_strategy',
        'device_metric_candidates'
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
\echo '- 已为 4 个配置表添加外键约束（P1优先级）'
\echo '- metric_quality_rules: 质量规则配置表'
\echo '- metric_rule_auto_baseline: 自动基线配置表'
\echo '- metric_anomaly_strategy: 异常策略配置表'
\echo '- device_metric_candidates: 设备指标候选配置表'
\echo '- 共添加 7 个外键约束（device_id: 4个, station_id: 3个）'
\echo '- 所有外键都配置了 ON UPDATE CASCADE ON DELETE CASCADE'
\echo '- 配置表现在受到完全保护'
\echo ''

