-- 查询覆盖审计（只读）：索引覆盖 + 近7天活跃分区缺失索引
SET client_encoding = 'UTF8';
SET client_min_messages = WARNING;

CREATE SCHEMA IF NOT EXISTS monitoring;

-- 1) 审计 fact_measurements 的常用查询路径是否有索引覆盖
CREATE OR REPLACE VIEW monitoring.v_query_coverage AS
SELECT
  i.schemaname,
  i.tablename,
  i.indexname,
  i.indexdef,
  CASE WHEN i.indexdef ILIKE '%(station_id, device_id, metric_id, ts_bucket)%' THEN 'covers_smdt'
       WHEN i.indexdef ILIKE '%(station_id, ts_bucket)%' THEN 'covers_st'
       WHEN i.indexdef ILIKE '%(station_id, device_id, ts_bucket)%' THEN 'covers_sdt'
       ELSE 'other' END AS coverage
FROM pg_indexes i
WHERE i.tablename ~* 'fact_measurements.*' OR i.tablename = 'fact_measurements';

-- 2) 审计近7天叶子分区索引缺失情况（依赖 active_partition_audit 的 last7d 视图）
CREATE OR REPLACE VIEW monitoring.v_missing_indexes_last7d AS
SELECT p.schemaname, p.part_name
FROM monitoring.v_active_partitions_last7d p
LEFT JOIN pg_indexes i
  ON i.schemaname = p.schemaname AND i.tablename = p.part_name
GROUP BY 1,2
HAVING bool_or(i.indexname ILIKE 'idx_%_smdt') IS NOT TRUE;
