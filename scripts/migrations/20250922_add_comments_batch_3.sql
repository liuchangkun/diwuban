-- 迁移（批次三）：为扩展函数补充中文注释（仅注释，不改结构）
-- 范围：TimescaleDB 与 pg_stat_statements 常用/对外函数（精确签名），包含用途/参数/返回/示例/性能与安全提示
-- 口径：统一 UTC、时间窗半开区间 [start, end)；谨慎在业务高峰期执行管理/统计类函数

/* ===== pg_stat_statements 扩展（public）===== */
COMMENT ON FUNCTION public.pg_stat_statements(boolean) IS
'用途：返回 SQL 语句级的执行与 I/O 统计，支持是否包含 query 文本（showtext）。
参数：showtext boolean
返回：SETOF record（含 userid/dbid/toplevel/queryid/query/.../时间与块 I/O/JIT 等统计）
示例：
  SELECT dbid, calls, total_exec_time, query
  FROM public.pg_stat_statements(true)
  WHERE toplevel IS TRUE
  ORDER BY total_exec_time DESC
  LIMIT 50;
性能/安全：
  - 仅 DBA/诊断用途；大结果集请 LIMIT，并按 dbid/toplevel 过滤；
  - 重置统计请使用 pg_stat_statements_reset，谨慎在生产高峰期执行。';

COMMENT ON FUNCTION public.pg_stat_statements_info() IS
'用途：返回 pg_stat_statements 的统计信息（如重置时间）。
参数：无
返回：record（dealloc、stats_reset）
示例：
  SELECT * FROM public.pg_stat_statements_info();';

COMMENT ON FUNCTION public.pg_stat_statements_reset(oid, oid, bigint) IS
'用途：重置 pg_stat_statements 统计。
参数：userid oid, dbid oid, queryid bigint（可为 0/NULL 表示全部）
返回：void
示例：
  SELECT public.pg_stat_statements_reset(0, 0, NULL);
注意：具有破坏性，会清零历史统计；生产环境请审批后执行。';

/* ===== TimescaleDB：时间分桶/填充 ===== */
COMMENT ON FUNCTION public.time_bucket(interval, timestamp with time zone) IS
'用途：按固定宽度对 timestamptz 时间戳进行对齐分桶。
参数：bucket_width interval, ts timestamptz
返回：timestamptz（桶起始时间）
示例：
  SELECT time_bucket(INTERVAL ''1 minute'', ts) AS ts_min, avg(value)
  FROM fact_measurements
  WHERE ts >= ''2025-09-01T00:00:00Z'' AND ts < ''2025-09-01T02:00:00Z''
  GROUP BY 1
  ORDER BY 1;';

COMMENT ON FUNCTION public.time_bucket(interval, timestamp without time zone) IS
'用途：按固定宽度对 timestamp 时间戳进行对齐分桶（无时区）。
参数：bucket_width interval, ts timestamp
返回：timestamp（桶起始时间）
注意：建议统一在存储与计算层使用 timestamptz；若使用 timestamp，请自行处理时区。';

COMMENT ON FUNCTION public.time_bucket(interval, timestamp with time zone, interval) IS
'用途：带 offset 的分桶，对齐后整体平移。
参数：bucket_width interval, ts timestamptz, offset interval
返回：timestamptz
示例：
  SELECT time_bucket(INTERVAL ''1 hour'', ts, INTERVAL ''8 hour'')  -- 东八区视角的对齐
  FROM fact_measurements LIMIT 1;';

COMMENT ON FUNCTION public.time_bucket(interval, timestamp with time zone, timestamp with time zone) IS
'用途：以 origin 为对齐原点进行分桶。
参数：bucket_width interval, ts timestamptz, origin timestamptz
返回：timestamptz
说明：当需要对齐到某个特定起点（如自然日零点）时使用。';

COMMENT ON FUNCTION public.time_bucket_gapfill(interval, timestamp with time zone, timestamp with time zone, timestamp with time zone) IS
'用途：在时间序列聚合中对缺失的时间桶进行补全（gapfill）。
参数：bucket_width interval, ts timestamptz, start timestamptz, finish timestamptz
返回：timestamptz（桶起始时间）
示例：
  SELECT time_bucket_gapfill(INTERVAL ''1 minute'', ts, ''2025-09-01T00:00:00Z'', ''2025-09-01T01:00:00Z'') AS b,
         LOCF(avg(value)) AS avg_value
  FROM fact_measurements
  WHERE ts >= ''2025-09-01T00:00:00Z'' AND ts < ''2025-09-01T01:00:00Z''
  GROUP BY b
  ORDER BY b;
注意：gapfill 仅补齐时间桶，值需配合 LOCF/INTERPOLATE 等函数处理。';

COMMENT ON FUNCTION timescaledb_experimental.time_bucket_ng(interval, timestamp with time zone) IS
'用途：新一代分桶（ng），在某些场景下具备更高性能与灵活性。
参数：bucket_width interval, ts timestamptz
返回：timestamptz
提示：ng 系列仍属实验特性，升级/兼容性以官方文档为准。';

COMMENT ON FUNCTION timescaledb_experimental.time_bucket_ng(interval, timestamp with time zone, timestamp with time zone) IS
'用途：以 origin 为原点的 ng 分桶。
参数：bucket_width interval, ts timestamptz, origin timestamptz
返回：timestamptz';

COMMENT ON FUNCTION timescaledb_experimental.time_bucket_ng(interval, timestamp with time zone, timestamp with time zone, text) IS
'用途：指定 origin 与时区文本的 ng 分桶。
参数：bucket_width interval, ts timestamptz, origin timestamptz, timezone text
返回：timestamptz
注意：使用 timezone 文本需确保与业务统一的时区策略一致。';

/* ===== TimescaleDB：尺寸/管理常用函数（public）===== */
COMMENT ON FUNCTION public.hypertable_size(regclass) IS
'用途：返回超表占用的总字节数。
参数：hypertable regclass
返回：bigint（字节）
示例：SELECT pg_size_pretty(public.hypertable_size(''fact_measurements''::regclass));
提示：统计类查询可能较重，避免业务高峰期执行。';

COMMENT ON FUNCTION public.hypertable_detailed_size(regclass) IS
'用途：返回超表的详细尺寸构成（表/索引/TOAST/总计）。
参数：hypertable regclass
返回：TABLE(table_bytes bigint, index_bytes bigint, toast_bytes bigint, total_bytes bigint, node_name name)
示例：SELECT * FROM public.hypertable_detailed_size(''fact_measurements''::regclass);
提示：避免在业务高峰期频繁执行。';

COMMENT ON FUNCTION public.hypertable_approximate_size(regclass) IS
'用途：返回近似的超表大小（更快，精度略低）。
参数：relation regclass
返回：bigint';

COMMENT ON FUNCTION public.chunks_detailed_size(regclass) IS
'用途：按 chunk 粒度返回各分片的尺寸统计。
参数：hypertable regclass
返回：TABLE(chunk_schema name, chunk_name name, table_bytes bigint, index_bytes bigint, toast_bytes bigint, total_bytes bigint, node_name name)
示例：SELECT * FROM public.chunks_detailed_size(''fact_measurements''::regclass) LIMIT 20;';

COMMENT ON FUNCTION public.compress_chunk(regclass, boolean, boolean) IS
'用途：对指定 chunk 执行压缩或重压缩。
参数：uncompressed_chunk regclass, if_not_compressed boolean, recompress boolean
返回：regclass
注意：涉及写操作；请在离峰期执行并预估磁盘/CPU 影响。';

COMMENT ON FUNCTION public.decompress_chunk(regclass, boolean) IS
'用途：对指定 chunk 执行解压。
参数：uncompressed_chunk regclass, if_compressed boolean
返回：regclass
注意：涉及写操作；解压后尺寸上升，谨慎评估空间。';

COMMENT ON FUNCTION public.set_chunk_time_interval(regclass, anyelement, name) IS
'用途：设置超表时间维度的 chunk 时间间隔。
参数：hypertable regclass, chunk_time_interval anyelement, dimension_name name
返回：void
建议：结合业务写入速率与查询窗口选择合理的 chunk 间隔。';

COMMENT ON FUNCTION public.set_integer_now_func(regclass, regproc, boolean) IS
'用途：为整型时间列的超表设置 now() 函数（如基于序列的时间）。
参数：hypertable regclass, integer_now_func regproc, replace_if_exists boolean
返回：void';

COMMENT ON FUNCTION public.create_hypertable(regclass, name, name, integer, name, name, anyelement, boolean, boolean, regproc, boolean, text, regproc, regproc) IS
'用途：创建超表（高级签名，含分区/索引/迁移/目标尺寸/自定义分区函数等选项）。
参数：relation regclass, time_column_name name, partitioning_column name, number_partitions integer, associated_schema_name name, associated_table_prefix name, chunk_time_interval anyelement, create_default_indexes boolean, if_not_exists boolean, partitioning_func regproc, migrate_data boolean, chunk_target_size text, chunk_sizing_func regproc, time_partitioning_func regproc
返回：TABLE(hypertable_id integer, schema_name name, table_name name, created boolean)
注意：涉及 DDL；生产执行前请充分评估与变更审批。';

COMMENT ON FUNCTION public.hypertable_index_size(regclass) IS
'用途：返回指定索引占用的字节数。
参数：index_name regclass
返回：bigint
示例：SELECT pg_size_pretty(public.hypertable_index_size(''idx_fact_measurements_ts''::regclass));';

COMMENT ON FUNCTION public.generate_uuidv7() IS
'用途：生成 UUIDv7（时间序列友好）。
参数：无
返回：uuid
示例：SELECT public.generate_uuidv7();';

COMMENT ON FUNCTION public.to_uuidv7(timestamp with time zone) IS
'用途：将时间戳转换为 UUIDv7（编码时间）。
参数：ts timestamptz
返回：uuid';

COMMENT ON FUNCTION public.uuid_timestamp(uuid) IS
'用途：从 UUID 中解析时间戳（若版本与实现支持）。
参数：uuid uuid
返回：timestamptz';

