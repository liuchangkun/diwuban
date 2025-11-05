-- ============================================
-- P0优先级：为配置表添加外键约束（基于业务逻辑分类）
-- ============================================
-- 文件：scripts/sql/validation/P0_add_foreign_keys_config_tables_v2.sql
-- 用途：仅为真正的"配置数据"表添加外键约束，历史数据表不添加
-- 优先级：P0 - 立即执行
-- 风险：低（已验证无孤立记录）
-- 执行方式：psql -h localhost -U postgres -d pump_station -f P0_add_foreign_keys_config_tables_v2.sql
-- ============================================

\echo '=========================================='
\echo 'P0优先级：为配置表添加外键约束（v2）'
\echo '基于业务逻辑分类：配置数据 vs 历史数据'
\echo '=========================================='
\echo ''

BEGIN;

-- ============================================
-- 第一步：执行前检查
-- ============================================

\echo '【1】执行前检查：验证是否存在孤立记录'
\echo '----------------------------------------'

\echo '1.1 检查 device_running_thresholds（P0 - 运行阈值配置）'
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

-- ============================================
-- 第二步：添加外键约束（仅P0优先级）
-- ============================================

\echo ''
\echo '【2】添加外键约束（P0优先级）'
\echo '----------------------------------------'

\echo '2.1 为 device_running_thresholds 添加外键'
\echo '    业务分类：运行阈值配置'
\echo '    影响功能：运行状态判定、启停窗口检测、功率因数判断'
\echo '    失联后果：设备无法判定运行状态，被排除在计算范围外'

ALTER TABLE device_running_thresholds
ADD CONSTRAINT device_running_thresholds_device_id_fkey
FOREIGN KEY (device_id) REFERENCES dim_devices(id)
ON UPDATE CASCADE ON DELETE CASCADE;

\echo '✅ device_running_thresholds.device_id 外键已添加'

-- ============================================
-- 第三步：验证外键约束
-- ============================================

\echo ''
\echo '【3】验证外键约束'
\echo '----------------------------------------'

\echo '3.1 验证外键已添加'
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
    AND tc.table_name = 'device_running_thresholds'
    AND ccu.table_name = 'dim_devices';

-- ============================================
-- 第四步：提交事务
-- ============================================

\echo ''
\echo '【4】提交事务'
\echo '----------------------------------------'

COMMIT;

\echo '✅ 外键约束已成功添加并提交'

\echo ''
\echo '=========================================='
\echo '执行完成'
\echo '=========================================='
\echo ''
\echo '总结：'
\echo '- 已为 1 个配置表添加外键约束（P0优先级）'
\echo '- device_running_thresholds: 运行阈值配置表'
\echo '- 外键配置了 ON UPDATE CASCADE ON DELETE CASCADE'
\echo '- 配置表现在受到完全保护'
\echo ''
\echo '说明：'
\echo '- fact_measurements 是历史数据表，不需要外键约束'
\echo '- 历史数据保留历史ID是合理的（记录过去的事实）'
\echo '- 配置数据必须跟随ID变化（影响程序如何运行）'
\echo ''
\echo '下一步：'
\echo '- P1优先级：为质量规则相关表添加外键约束'
\echo '  - metric_quality_rules'
\echo '  - metric_rule_auto_baseline'
\echo '  - metric_anomaly_strategy'
\echo '  - device_metric_candidates'
\echo ''

