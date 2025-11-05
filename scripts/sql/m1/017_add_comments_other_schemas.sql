\encoding UTF8
SET client_encoding = 'UTF8';

-- 为非 public 架构对象补充“用途/参数/返回/示例 SQL”注释（仅 COMMENT，不改对象定义）

-- monitoring 架构视图
COMMENT ON VIEW monitoring.v_active_index_coverage IS $DOC$
用途: 活跃索引覆盖率评估（近窗口内）。
字段: schemaname name, part_name name, indexname name。
示例:
SELECT * FROM monitoring.v_active_index_coverage ORDER BY schemaname, part_name, indexname LIMIT 200;
$DOC$;

COMMENT ON VIEW monitoring.v_active_partitions IS $DOC$
用途: 活跃分区清单。
字段: schemaname name, part_name name, relpartbound text。
示例:
SELECT * FROM monitoring.v_active_partitions WHERE part_name LIKE 'fact_measurements_%' ORDER BY part_name;
$DOC$;

COMMENT ON VIEW monitoring.v_active_partitions_last7d IS $DOC$
用途: 最近 7 天活跃分区。
字段: schemaname name, part_name name, relpartbound text, lower_ts timestamptz, upper_ts timestamptz。
示例:
SELECT * FROM monitoring.v_active_partitions_last7d ORDER BY part_name;
$DOC$;

COMMENT ON VIEW monitoring.v_missing_indexes_last7d IS $DOC$
用途: 最近 7 天缺失索引建议（基于 pg_stat_statements 快照）。
字段: schemaname name, part_name name。
示例:
SELECT * FROM monitoring.v_missing_indexes_last7d ORDER BY part_name LIMIT 200;
$DOC$;

COMMENT ON VIEW monitoring.v_mv_hit_audit IS $DOC$
用途: 物化视图命中审计。
字段: hourly_hits bigint, daily_hits bigint, fact_hits bigint, total bigint。
示例:
SELECT * FROM monitoring.v_mv_hit_audit ORDER BY total DESC LIMIT 200;
$DOC$;

COMMENT ON VIEW monitoring.v_query_coverage IS $DOC$
用途: 查询覆盖率与命中统计。
字段: schemaname name, tablename name, indexname name, indexdef text, coverage text。
示例:
SELECT * FROM monitoring.v_query_coverage ORDER BY coverage DESC NULLS LAST LIMIT 200;
$DOC$;

-- reporting 架构视图与物化视图
COMMENT ON VIEW reporting.v_metrics_daily IS $DOC$
用途: 指标按日聚合视图。
字段: station_id bigint, device_id bigint, metric_id bigint, ts timestamptz, cnt bigint, avg_value numeric, min_value numeric, max_value numeric, sum_value numeric。
示例:
SELECT * FROM reporting.v_metrics_daily
WHERE ts BETWEEN current_date-7 AND current_date-1
ORDER BY station_id, device_id, metric_id, ts;
$DOC$;

COMMENT ON MATERIALIZED VIEW reporting.mv_measurements_daily IS $DOC$
用途: 日级汇总物化视图。
示例:
SELECT * FROM reporting.mv_measurements_daily
WHERE ts BETWEEN current_date-7 AND current_date-1
ORDER BY station_id, device_id, metric_id, ts;
-- 刷新示例（注意并发与锁）：REFRESH MATERIALIZED VIEW CONCURRENTLY reporting.mv_measurements_daily;
$DOC$;

COMMENT ON MATERIALIZED VIEW reporting.mv_measurements_hourly IS $DOC$
用途: 小时级汇总物化视图。
示例:
SELECT * FROM reporting.mv_measurements_hourly
WHERE ts_hour >= now()-interval '24 hours'
ORDER BY station_id, device_id, metric_id, ts_hour;
-- 刷新示例：REFRESH MATERIALIZED VIEW CONCURRENTLY reporting.mv_measurements_hourly;
$DOC$;

-- api 架构函数
COMMENT ON FUNCTION api.upsert_measurement(bigint,bigint,bigint,timestamptz,numeric,text) IS $DOC$
用途: 单条测点 UPSERT。
参数: p_station_id, p_device_id, p_metric_id, p_ts_raw, p_value, p_source_hint。
返回: boolean（是否执行写入）。
示例:
SELECT api.upsert_measurement(1,1,101,'2025-09-01 00:00:00+00',12.34,'api');
$DOC$;

COMMENT ON FUNCTION api.update_measurement_value(bigint,bigint,bigint,timestamptz,numeric,text) IS $DOC$
用途: 更新现有测点的数值与来源。
返回: integer（受影响行数）。
示例:
SELECT api.update_measurement_value(1,1,101,'2025-09-01 00:00:00+00',23.45,'fix');
$DOC$;

COMMENT ON FUNCTION api.delete_measurement(bigint,bigint,bigint,timestamptz) IS $DOC$
用途: 删除指定单点。
返回: integer（受影响行数）。
示例:
SELECT api.delete_measurement(1,1,101,'2025-09-01 00:00:00+00');
$DOC$;

COMMENT ON FUNCTION api.delete_measurements_by_filter(bigint[],timestamptz,timestamptz,bigint[],bigint[],integer) IS $DOC$
用途: 条件批量删除（按站点/设备/指标与时间窗，分批）。
返回: TABLE(total_deleted integer)。
示例:
SELECT * FROM api.delete_measurements_by_filter(ARRAY[1], now()-interval '1 day', now(), NULL, NULL, 5000);
$DOC$;

COMMENT ON FUNCTION api.get_measurements(bigint[],timestamptz,timestamptz,bigint[],bigint[],integer,integer) IS $DOC$
用途: 条件分页读取明细。
返回: TABLE(station_id, device_id, metric_id, ts_raw, ts_bucket, value, source_hint, inserted_at)。
示例:
SELECT * FROM api.get_measurements(ARRAY[1], now()-interval '10 minutes', now(), NULL, ARRAY[101], 1000, 0) LIMIT 1000;
$DOC$;

-- monitoring 架构函数
COMMENT ON FUNCTION monitoring.capture_pgss_snapshot() IS $DOC$
用途: 捕获 pg_stat_statements 快照。
返回: integer（采集/插入的快照记录数）。
示例:
SELECT monitoring.capture_pgss_snapshot();
$DOC$;

COMMENT ON FUNCTION monitoring.cleanup_pgss_snapshot(integer) IS $DOC$
用途: 清理过期快照。
参数: retention_days。
返回: integer（删除的历史快照行数）。
示例:
SELECT monitoring.cleanup_pgss_snapshot(7);
$DOC$;

COMMENT ON FUNCTION monitoring.ensure_active_indexes(integer) IS $DOC$
用途: 确保近窗口所需索引处于活跃状态。
参数: window_days。
返回: integer（新建/确认活跃的索引数量）。
示例:
SELECT monitoring.ensure_active_indexes(7);
$DOC$;

COMMENT ON FUNCTION monitoring.run_ab_test(bigint,timestamptz,timestamptz,bigint[]) IS $DOC$
用途: 在时间窗内对指标做 A/B 试验（示例）。
参数: p_station_id, p_start_ts, p_end_ts, p_metric_ids=NULL。
返回: bigint（run_id）。
示例:
SELECT monitoring.run_ab_test(1, now()-interval '1 day', now(), ARRAY[101,102]);
$DOC$;

