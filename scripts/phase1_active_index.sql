SET client_encoding = 'UTF8';
SET client_min_messages = WARNING;

-- Phase1: 为近7天活跃分区创建 btree 索引（station_id, device_id, metric_id, ts_bucket）
-- 在线执行，使用 CONCURRENTLY；仅对与 (now()-7d, now()] 区间有交集的叶子分区创建
DO $$
DECLARE
  r RECORD;
  bound TEXT;
  m TEXT[];
  lower_ts timestamptz;
  upper_ts timestamptz;
  idx_name TEXT;
BEGIN
  FOR r IN (
    SELECT c.oid AS relid, n.nspname AS schemaname, c.relname AS part_name,
           pg_get_expr(c.relpartbound, c.oid) AS relpartbound
    FROM pg_partition_tree('public.fact_measurements') t
    JOIN pg_class c ON c.oid = t.relid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE t.isleaf
  ) LOOP
    bound := r.relpartbound;
    -- 提取 RANGE 分区的 FROM/TO 时间边界
    SELECT regexp_matches(bound, 'FROM \(''([^'']+)''\) TO \(''([^'']+)''\)') INTO m;
    IF m IS NULL OR array_length(m,1) < 2 THEN
      CONTINUE;
    END IF;
    lower_ts := m[1]::timestamptz;
    upper_ts := m[2]::timestamptz;

    -- 与最近7天有交集则创建索引
    IF upper_ts > (now() - interval '7 days') AND lower_ts < now() THEN
      idx_name := format('idx_%s_smdt', r.part_name);
      EXECUTE format(
        'CREATE INDEX CONCURRENTLY IF NOT EXISTS %I ON %I.%I (station_id, device_id, metric_id, ts_bucket) INCLUDE (value) WITH (fillfactor = 70)',
        idx_name, r.schemaname, r.part_name
      );
    END IF;
  END LOOP;
END $$;
