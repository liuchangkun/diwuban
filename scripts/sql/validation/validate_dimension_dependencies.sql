-- ============================================
-- 维度表ID依赖关系完整验证脚本
-- ============================================
-- 文件：scripts/sql/validation/validate_dimension_dependencies.sql
-- 用途：验证所有与 dim_devices.id 和 dim_stations.id 相关的依赖关系
-- 执行方式：psql -h localhost -U postgres -d pump_station -f validate_dimension_dependencies.sql
-- ============================================

\echo '=========================================='
\echo '维度表ID依赖关系完整验证'
\echo '=========================================='
\echo ''

-- ============================================
-- 第一部分：外键约束验证
-- ============================================

\echo '【1】外键约束验证'
\echo '----------------------------------------'

\echo '1.1 依赖 dim_devices.id 的外键约束（应该有16个）'
SELECT 
    tc.table_schema AS schema名称,
    tc.table_name AS 表名,
    kcu.column_name AS 外键列名,
    ccu.table_name AS 引用表,
    rc.update_rule AS UPDATE规则,
    rc.delete_rule AS DELETE规则
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
    AND ccu.table_name = 'dim_devices'
    AND ccu.column_name = 'id'
ORDER BY tc.table_schema, tc.table_name;

\echo ''
\echo '1.2 依赖 dim_stations.id 的外键约束（应该有12个）'
SELECT 
    tc.table_schema AS schema名称,
    tc.table_name AS 表名,
    kcu.column_name AS 外键列名,
    ccu.table_name AS 引用表,
    rc.update_rule AS UPDATE规则,
    rc.delete_rule AS DELETE规则
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
    AND ccu.table_name = 'dim_stations'
    AND ccu.column_name = 'id'
ORDER BY tc.table_schema, tc.table_name;

\echo ''
\echo '1.3 验证所有外键都配置了 CASCADE'
SELECT 
    tc.table_name AS 表名,
    kcu.column_name AS 外键列名,
    ccu.table_name AS 引用表,
    rc.update_rule AS UPDATE规则,
    rc.delete_rule AS DELETE规则,
    CASE 
        WHEN rc.update_rule = 'CASCADE' AND rc.delete_rule = 'CASCADE' THEN '✅ 完全保护'
        WHEN rc.update_rule = 'CASCADE' THEN '⚠️ 仅UPDATE保护'
        WHEN rc.delete_rule = 'CASCADE' THEN '⚠️ 仅DELETE保护'
        ELSE '❌ 无保护'
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
    AND ccu.table_name IN ('dim_devices', 'dim_stations')
    AND ccu.column_name = 'id'
    AND tc.table_schema = 'public'
ORDER BY 保护状态, tc.table_name;

-- ============================================
-- 第二部分：无外键约束的表识别
-- ============================================

\echo ''
\echo '【2】无外键约束的表识别'
\echo '----------------------------------------'

\echo '2.1 包含 device_id 但无外键约束的表'
SELECT 
    c.table_schema AS schema名称,
    c.table_name AS 表名,
    c.column_name AS 列名,
    t.table_type AS 表类型,
    CASE 
        WHEN c.table_name = 'fact_measurements' THEN '⚠️ 极高风险'
        WHEN c.table_name IN ('device_running_thresholds', 'metric_quality_rules', 'metric_rule_auto_baseline') THEN '⚠️ 高风险'
        WHEN c.table_name IN ('device_metric_candidates', 'metric_anomaly_strategy') THEN '⚠️ 中风险'
        WHEN c.table_schema = '_timescaledb_internal' THEN 'ℹ️ 低风险（TimescaleDB内部）'
        WHEN t.table_type = 'VIEW' THEN 'ℹ️ 低风险（视图）'
        ELSE 'ℹ️ 低风险'
    END AS 风险等级
FROM information_schema.columns c
JOIN information_schema.tables t 
    ON c.table_schema = t.table_schema 
    AND c.table_name = t.table_name
WHERE c.column_name = 'device_id'
    AND c.table_schema NOT IN ('pg_catalog', 'information_schema')
    AND NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu 
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = c.table_schema
            AND tc.table_name = c.table_name
            AND kcu.column_name = c.column_name
    )
ORDER BY 风险等级, c.table_schema, c.table_name;

\echo ''
\echo '2.2 包含 station_id 但无外键约束的表'
SELECT 
    c.table_schema AS schema名称,
    c.table_name AS 表名,
    c.column_name AS 列名,
    t.table_type AS 表类型,
    CASE 
        WHEN c.table_name = 'fact_measurements' THEN '⚠️ 极高风险'
        WHEN c.table_name IN ('metric_quality_rules', 'metric_rule_auto_baseline') THEN '⚠️ 高风险'
        WHEN c.table_name IN ('metric_anomaly_strategy') THEN '⚠️ 中风险'
        WHEN c.table_schema = '_timescaledb_internal' THEN 'ℹ️ 低风险（TimescaleDB内部）'
        WHEN t.table_type = 'VIEW' THEN 'ℹ️ 低风险（视图）'
        ELSE 'ℹ️ 低风险'
    END AS 风险等级
FROM information_schema.columns c
JOIN information_schema.tables t 
    ON c.table_schema = t.table_schema 
    AND c.table_name = t.table_name
WHERE c.column_name = 'station_id'
    AND c.table_schema NOT IN ('pg_catalog', 'information_schema')
    AND NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu 
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = c.table_schema
            AND tc.table_name = c.table_name
            AND kcu.column_name = c.column_name
    )
ORDER BY 风险等级, c.table_schema, c.table_name;

-- ============================================
-- 第三部分：数据完整性检查
-- ============================================

\echo ''
\echo '【3】数据完整性检查'
\echo '----------------------------------------'

\echo '3.1 检查 fact_measurements 中的孤立记录'
SELECT 
    '孤立的device_id' AS 检查项,
    COUNT(DISTINCT fm.device_id) AS 孤立ID数量,
    CASE 
        WHEN COUNT(DISTINCT fm.device_id) = 0 THEN '✅ 无孤立记录'
        ELSE '❌ 存在孤立记录'
    END AS 状态
FROM fact_measurements fm
LEFT JOIN dim_devices d ON d.id = fm.device_id
WHERE d.id IS NULL

UNION ALL

SELECT 
    '孤立的station_id' AS 检查项,
    COUNT(DISTINCT fm.station_id) AS 孤立ID数量,
    CASE 
        WHEN COUNT(DISTINCT fm.station_id) = 0 THEN '✅ 无孤立记录'
        ELSE '❌ 存在孤立记录'
    END AS 状态
FROM fact_measurements fm
LEFT JOIN dim_stations s ON s.id = fm.station_id
WHERE s.id IS NULL;

\echo ''
\echo '3.2 检查 device_running_thresholds 中的孤立记录'
SELECT 
    '孤立的device_id' AS 检查项,
    COUNT(*) AS 孤立记录数,
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ 无孤立记录'
        ELSE '❌ 存在孤立记录'
    END AS 状态
FROM device_running_thresholds drt
LEFT JOIN dim_devices d ON d.id = drt.device_id
WHERE d.id IS NULL;

\echo ''
\echo '3.3 检查 metric_quality_rules 中的孤立记录'
SELECT 
    '孤立的device_id' AS 检查项,
    COUNT(*) AS 孤立记录数,
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ 无孤立记录'
        ELSE '❌ 存在孤立记录'
    END AS 状态
FROM metric_quality_rules mqr
LEFT JOIN dim_devices d ON d.id = mqr.device_id
WHERE d.id IS NULL

UNION ALL

SELECT 
    '孤立的station_id' AS 检查项,
    COUNT(*) AS 孤立记录数,
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ 无孤立记录'
        ELSE '❌ 存在孤立记录'
    END AS 状态
FROM metric_quality_rules mqr
LEFT JOIN dim_stations s ON s.id = mqr.station_id
WHERE s.id IS NULL;

\echo ''
\echo '3.4 检查 metric_rule_auto_baseline 中的孤立记录'
SELECT 
    '孤立的device_id' AS 检查项,
    COUNT(*) AS 孤立记录数,
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ 无孤立记录'
        ELSE '❌ 存在孤立记录'
    END AS 状态
FROM metric_rule_auto_baseline mrab
LEFT JOIN dim_devices d ON d.id = mrab.device_id
WHERE d.id IS NULL

UNION ALL

SELECT 
    '孤立的station_id' AS 检查项,
    COUNT(*) AS 孤立记录数,
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ 无孤立记录'
        ELSE '❌ 存在孤立记录'
    END AS 状态
FROM metric_rule_auto_baseline mrab
LEFT JOIN dim_stations s ON s.id = mrab.station_id
WHERE s.id IS NULL;

-- ============================================
-- 第四部分：记录数统计
-- ============================================

\echo ''
\echo '【4】记录数统计'
\echo '----------------------------------------'

\echo '4.1 有外键约束的表记录数'
SELECT 
    'device_rated_params' AS 表名,
    COUNT(*) AS 记录数,
    '✅ 有外键' AS 外键状态
FROM device_rated_params

UNION ALL

SELECT 
    'optimization_history' AS 表名,
    COUNT(*) AS 记录数,
    '✅ 有外键' AS 外键状态
FROM optimization_history

UNION ALL

SELECT 
    'metric_quality_rules_shadow' AS 表名,
    COUNT(*) AS 记录数,
    '✅ 有外键' AS 外键状态
FROM metric_quality_rules_shadow

UNION ALL

SELECT 
    'metric_rule_auto_baseline_shadow' AS 表名,
    COUNT(*) AS 记录数,
    '✅ 有外键' AS 外键状态
FROM metric_rule_auto_baseline_shadow

UNION ALL

SELECT 
    'calculation_parameters' AS 表名,
    COUNT(*) AS 记录数,
    '✅ 有外键' AS 外键状态
FROM calculation_parameters

UNION ALL

SELECT 
    'completion_runs' AS 表名,
    COUNT(*) AS 记录数,
    '✅ 有外键' AS 外键状态
FROM completion_runs

UNION ALL

SELECT 
    'dim_device_capabilities' AS 表名,
    COUNT(*) AS 记录数,
    '✅ 有外键' AS 外键状态
FROM dim_device_capabilities

ORDER BY 记录数 DESC;

\echo ''
\echo '4.2 无外键约束的表记录数'
SELECT 
    'fact_measurements' AS 表名,
    COUNT(*) AS 记录数,
    '❌ 无外键' AS 外键状态,
    '⚠️ 极高风险' AS 风险等级
FROM fact_measurements

UNION ALL

SELECT 
    'device_running_thresholds' AS 表名,
    COUNT(*) AS 记录数,
    '❌ 无外键' AS 外键状态,
    '⚠️ 高风险' AS 风险等级
FROM device_running_thresholds

UNION ALL

SELECT 
    'metric_quality_rules' AS 表名,
    COUNT(*) AS 记录数,
    '❌ 无外键' AS 外键状态,
    '⚠️ 高风险' AS 风险等级
FROM metric_quality_rules

UNION ALL

SELECT 
    'metric_rule_auto_baseline' AS 表名,
    COUNT(*) AS 记录数,
    '❌ 无外键' AS 外键状态,
    '⚠️ 高风险' AS 风险等级
FROM metric_rule_auto_baseline

UNION ALL

SELECT 
    'device_metric_candidates' AS 表名,
    COUNT(*) AS 记录数,
    '❌ 无外键' AS 外键状态,
    '⚠️ 中风险' AS 风险等级
FROM device_metric_candidates

UNION ALL

SELECT 
    'metric_anomaly_strategy' AS 表名,
    COUNT(*) AS 记录数,
    '❌ 无外键' AS 外键状态,
    '⚠️ 中风险' AS 风险等级
FROM metric_anomaly_strategy

ORDER BY 记录数 DESC;

-- ============================================
-- 第五部分：TimescaleDB特殊检查
-- ============================================

\echo ''
\echo '【5】TimescaleDB特殊检查'
\echo '----------------------------------------'

\echo '5.1 fact_measurements 的 Hypertable 信息'
SELECT 
    hypertable_schema,
    hypertable_name,
    num_dimensions,
    num_chunks,
    compression_enabled,
    tablespaces
FROM timescaledb_information.hypertables
WHERE hypertable_name = 'fact_measurements';

\echo ''
\echo '5.2 fact_measurements 的分区（chunks）数量'
SELECT 
    COUNT(*) AS chunk数量,
    MIN(range_start) AS 最早时间,
    MAX(range_end) AS 最晚时间
FROM timescaledb_information.chunks
WHERE hypertable_name = 'fact_measurements';

-- ============================================
-- 第六部分：汇总报告
-- ============================================

\echo ''
\echo '【6】汇总报告'
\echo '----------------------------------------'

\echo '6.1 外键约束汇总'
SELECT 
    '有外键约束的表' AS 分类,
    COUNT(DISTINCT tc.table_name) AS 表数量,
    SUM(CASE WHEN rc.update_rule = 'CASCADE' AND rc.delete_rule = 'CASCADE' THEN 1 ELSE 0 END) AS CASCADE数量,
    CASE 
        WHEN COUNT(DISTINCT tc.table_name) = SUM(CASE WHEN rc.update_rule = 'CASCADE' AND rc.delete_rule = 'CASCADE' THEN 1 ELSE 0 END) 
        THEN '✅ 100%保护'
        ELSE '⚠️ 部分保护'
    END AS 保护状态
FROM information_schema.table_constraints tc
JOIN information_schema.constraint_column_usage ccu 
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
JOIN information_schema.referential_constraints rc
    ON rc.constraint_name = tc.constraint_name
    AND rc.constraint_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND ccu.table_name IN ('dim_devices', 'dim_stations')
    AND ccu.column_name = 'id'
    AND tc.table_schema = 'public';

\echo ''
\echo '=========================================='
\echo '验证完成'
\echo '=========================================='

