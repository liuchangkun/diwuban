-- A/B 验证框架：活跃分区 btree 索引收益评估（在线安全）
SET client_encoding = 'UTF8';
SET client_min_messages = WARNING;

CREATE SCHEMA IF NOT EXISTS monitoring;

-- 记录一次 A/B 运行的元数据
CREATE TABLE IF NOT EXISTS monitoring.ab_test_runs (
  id           bigserial PRIMARY KEY,
  run_time     timestamptz NOT NULL DEFAULT now(),
  station_id   bigint,
  start_ts     timestamptz,
  end_ts       timestamptz,
  metric_ids   bigint[]
);

-- 记录每个阶段（before/after）的结果
CREATE TABLE IF NOT EXISTS monitoring.ab_test_results (
  run_id       bigint REFERENCES monitoring.ab_test_runs(id) ON DELETE CASCADE,
  phase        text CHECK (phase IN ('before','after')),
  rows_count   bigint,
  duration_ms  double precision,
  created_at   timestamptz NOT NULL DEFAULT now()
);

-- 将 phase1 的活跃索引创建逻辑函数化并参数化时间窗口
CREATE OR REPLACE FUNCTION monitoring.ensure_active_indexes(window_days int DEFAULT 7)
RETURNS integer AS $$
DECLARE
  r RECORD;
  lower_ts timestamptz;
  upper_ts timestamptz;
  created_cnt integer := 0;
BEGIN
  FOR r IN (
    SELECT c.oid AS relid, n.nspname AS schemaname, c.relname AS part_name,
           pg_get_expr(c.relpartbound, c.oid) AS relpartbound
    FROM pg_partition_tree('public.fact_measurements') t
    JOIN pg_class c ON c.oid = t.relid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE t.isleaf
  ) LOOP
    -- 提取 RANGE 分区边界
    SELECT (m.matches)[1]::timestamptz, (m.matches)[2]::timestamptz
      INTO lower_ts, upper_ts
    FROM (
      SELECT regexp_matches(r.relpartbound, 'FROM \(''([^'']+)''\) TO \(''([^'']+)''\)') AS matches
    ) m;

    IF upper_ts IS NULL OR lower_ts IS NULL THEN
      CONTINUE;
    END IF;

    -- 与最近 window_days 内区间有交集
    IF upper_ts > (now() - make_interval(days => window_days)) AND lower_ts < now() THEN
      EXECUTE format(
        'CREATE INDEX IF NOT EXISTS %I ON %I.%I (station_id, device_id, metric_id, ts_bucket) INCLUDE (value) WITH (fillfactor = 70)',
        'idx_' || r.part_name || '_smdt', r.schemaname, r.part_name
      );
      created_cnt := created_cnt + 1;
    END IF;
  END LOOP;
  RETURN created_cnt;
END;
$$ LANGUAGE plpgsql;

-- 运行 A/B：在确保活跃索引前后，分别测量一次典型查询耗时（毫秒）与返回行数
CREATE OR REPLACE FUNCTION monitoring.run_ab_test(
  p_station_id bigint,
  p_start_ts   timestamptz,
  p_end_ts     timestamptz,
  p_metric_ids bigint[] DEFAULT NULL
) RETURNS bigint AS $$
DECLARE
  v_run_id bigint;
  t0 timestamptz;
  t1 timestamptz;
  dur_ms double precision;
  cnt bigint;
  _sql text;
BEGIN
  INSERT INTO monitoring.ab_test_runs (station_id, start_ts, end_ts, metric_ids)
  VALUES (p_station_id, p_start_ts, p_end_ts, p_metric_ids)
  RETURNING id INTO v_run_id;

  -- 构造查询SQL（分区剪枝：station_id + ts_bucket）
  IF p_metric_ids IS NULL THEN
    _sql := 'SELECT ts_bucket, device_id, metric_id, value FROM public.fact_measurements
             WHERE station_id = $1 AND ts_bucket BETWEEN $2 AND $3
             ORDER BY ts_bucket, device_id, metric_id';
  ELSE
    _sql := 'SELECT ts_bucket, device_id, metric_id, value FROM public.fact_measurements
             WHERE station_id = $1 AND ts_bucket BETWEEN $2 AND $3 AND metric_id = ANY($4)
             ORDER BY ts_bucket, device_id, metric_id';
  END IF;

  -- before：测量
  t0 := clock_timestamp();
  IF p_metric_ids IS NULL THEN
    EXECUTE 'SELECT count(*) FROM public.fact_measurements WHERE station_id = $1 AND ts_bucket BETWEEN $2 AND $3'
      INTO cnt USING p_station_id, p_start_ts, p_end_ts;
  ELSE
    EXECUTE 'SELECT count(*) FROM public.fact_measurements WHERE station_id = $1 AND ts_bucket BETWEEN $2 AND $3 AND metric_id = ANY($4)'
      INTO cnt USING p_station_id, p_start_ts, p_end_ts, p_metric_ids;
  END IF;
  t1 := clock_timestamp();
  dur_ms := EXTRACT(MILLISECOND FROM (t1 - t0)) + EXTRACT(SECOND FROM (t1 - t0)) * 1000 + (EXTRACT(MINUTE FROM (t1 - t0)) * 60000);
  INSERT INTO monitoring.ab_test_results(run_id, phase, rows_count, duration_ms) VALUES (v_run_id, 'before', cnt, dur_ms);

  -- ensure active indexes（最近 7 天）
  PERFORM monitoring.ensure_active_indexes(7);

  -- after：再次测量
  t0 := clock_timestamp();
  IF p_metric_ids IS NULL THEN
    EXECUTE 'SELECT count(*) FROM public.fact_measurements WHERE station_id = $1 AND ts_bucket BETWEEN $2 AND $3'
      INTO cnt USING p_station_id, p_start_ts, p_end_ts;
  ELSE
    EXECUTE 'SELECT count(*) FROM public.fact_measurements WHERE station_id = $1 AND ts_bucket BETWEEN $2 AND $3 AND metric_id = ANY($4)'
      INTO cnt USING p_station_id, p_start_ts, p_end_ts, p_metric_ids;
  END IF;
  t1 := clock_timestamp();
  dur_ms := EXTRACT(MILLISECOND FROM (t1 - t0)) + EXTRACT(SECOND FROM (t1 - t0)) * 1000 + (EXTRACT(MINUTE FROM (t1 - t0)) * 60000);
  INSERT INTO monitoring.ab_test_results(run_id, phase, rows_count, duration_ms) VALUES (v_run_id, 'after', cnt, dur_ms);

  RETURN v_run_id;
END;
$$ LANGUAGE plpgsql;
