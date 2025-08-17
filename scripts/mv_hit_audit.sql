-- 命中率审计：统计 MV 与事实表在 pg_stat_statements 中的占比
SET client_encoding = 'UTF8';
SET client_min_messages = WARNING;

CREATE SCHEMA IF NOT EXISTS monitoring;

-- 统计近一小时内的查询（以 pg_stat_statements 的 last execution 近似）
-- 注：不同版本字段差异较大，此处只统计包含对象名的 query 文本占比
CREATE OR REPLACE VIEW monitoring.v_mv_hit_audit AS
WITH base AS (
  SELECT lower(query) AS q
  FROM pg_stat_statements
)
SELECT
  sum(CASE WHEN q LIKE '%reporting.mv_measurements_hourly%' THEN 1 ELSE 0 END) AS hourly_hits,
  sum(CASE WHEN q LIKE '%reporting.mv_measurements_daily%' THEN 1 ELSE 0 END) AS daily_hits,
  sum(CASE WHEN q LIKE '%public.fact_measurements%' THEN 1 ELSE 0 END) AS fact_hits,
  count(*) AS total
FROM base;
