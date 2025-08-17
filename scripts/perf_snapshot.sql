-- 创建性能观测快照表与采集函数（基于 pg_stat_statements 已启用）
SET client_encoding = 'UTF8';
SET client_min_messages = WARNING;

CREATE SCHEMA IF NOT EXISTS monitoring;

CREATE TABLE IF NOT EXISTS monitoring.pgss_snapshot (
  snapshot_time      timestamptz NOT NULL DEFAULT now(),
  dbname             text,
  userid             oid,
  queryid            bigint,
  calls              bigint,
  rows               bigint,
  blk_read_time      double precision,
  blk_write_time     double precision,
  temp_blks_read     bigint,
  temp_blks_written  bigint
);

CREATE OR REPLACE FUNCTION monitoring.capture_pgss_snapshot()
RETURNS integer AS $$
DECLARE
  inserted_rows integer;
BEGIN
  INSERT INTO monitoring.pgss_snapshot (dbname, userid, queryid, calls, rows, blk_read_time, blk_write_time, temp_blks_read, temp_blks_written)
  SELECT current_database(), userid, queryid, calls, rows, blk_read_time, blk_write_time, temp_blks_read, temp_blks_written
  FROM pg_stat_statements;
  GET DIAGNOSTICS inserted_rows = ROW_COUNT;
  RETURN inserted_rows;
END;
$$ LANGUAGE plpgsql;

-- 可选：清理过旧数据（保留最近 7 天）
CREATE OR REPLACE FUNCTION monitoring.cleanup_pgss_snapshot(retention_days integer DEFAULT 7)
RETURNS integer AS $$
DECLARE
  deleted_rows integer;
BEGIN
  DELETE FROM monitoring.pgss_snapshot WHERE snapshot_time < now() - (retention_days || ' days')::interval;
  GET DIAGNOSTICS deleted_rows = ROW_COUNT;
  RETURN deleted_rows;
END;
$$ LANGUAGE plpgsql;
