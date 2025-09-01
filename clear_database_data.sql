-- =====================================================
-- 地五班项目数据库表内容清空脚本
-- 创建时间: 2025-08-22
-- 说明: 安全清空所有核心表数据，保留表结构和函数/视图
-- =====================================================

BEGIN;

-- 1. 首先清空事实表（分区表），避免外键约束问题
TRUNCATE TABLE fact_measurements CASCADE;

-- 2. 清空映射表
TRUNCATE TABLE dim_mapping_items CASCADE;

-- 3. 清空设备表（有外键依赖）
TRUNCATE TABLE dim_devices CASCADE;

-- 4. 清空站点表
TRUNCATE TABLE dim_stations CASCADE;

-- 5. 清空指标配置表
TRUNCATE TABLE dim_metric_config CASCADE;

-- 6. 重置序列（ID自增计数器）
SELECT setval('dim_stations_id_seq', 1, false);
SELECT setval('dim_devices_id_seq', 1, false);
SELECT setval('dim_metric_config_id_seq', 1, false);
SELECT setval('dim_mapping_items_id_seq', 1, false);
SELECT setval('fact_measurements_id_seq', 1, false);

-- 7. 验证清空结果
SELECT 
    'dim_stations' as table_name, 
    COUNT(*) as record_count 
FROM dim_stations
UNION ALL
SELECT 
    'dim_devices' as table_name, 
    COUNT(*) as record_count 
FROM dim_devices
UNION ALL
SELECT 
    'dim_metric_config' as table_name, 
    COUNT(*) as record_count 
FROM dim_metric_config
UNION ALL
SELECT 
    'dim_mapping_items' as table_name, 
    COUNT(*) as record_count 
FROM dim_mapping_items
UNION ALL
SELECT 
    'fact_measurements' as table_name, 
    COUNT(*) as record_count 
FROM fact_measurements;

COMMIT;

-- 显示操作完成信息
SELECT 
    '数据库表内容清空完成！' as status,
    '所有表数据已删除，序列已重置，表结构和函数/视图保持不变' as details;