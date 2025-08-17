-- 审计近7天叶子分区的活跃索引覆盖情况
SET client_encoding = 'UTF8';
SET client_min_messages = WARNING;

CREATE OR REPLACE VIEW monitoring.v_active_partitions AS
SELECT
  n.nspname AS schemaname,
  c.relname AS part_name,
  pg_get_expr(c.relpartbound, c.oid) AS relpartbound
FROM pg_partition_tree('public.fact_measurements') t
JOIN pg_class c ON c.oid = t.relid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE t.isleaf;

CREATE OR REPLACE VIEW monitoring.v_active_partitions_last7d AS
SELECT p.schemaname, p.part_name, p.relpartbound,
       (m.matches)[1]::timestamptz AS lower_ts,
       (m.matches)[2]::timestamptz AS upper_ts
FROM monitoring.v_active_partitions p
CROSS JOIN LATERAL (
  SELECT regexp_matches(p.relpartbound, 'FROM \(''([^'']+)''\) TO \(''([^'']+)''\)') AS matches
) m
WHERE (m.matches)[2]::timestamptz > (now() - interval '7 days')
  AND (m.matches)[1]::timestamptz < now();

CREATE OR REPLACE VIEW monitoring.v_active_index_coverage AS
SELECT p.schemaname, p.part_name, i.indexname
FROM monitoring.v_active_partitions_last7d p
LEFT JOIN pg_indexes i
  ON i.schemaname = p.schemaname AND i.tablename = p.part_name
WHERE i.indexname ILIKE 'idx_%_smdt' OR i.indexname IS NULL;
