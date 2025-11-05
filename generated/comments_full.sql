COMMENT ON FUNCTION "api"."delete_measurement"(p_station_id bigint, p_device_id bigint, p_metric_id bigint, p_ts_raw timestamp with time zone) IS $DOC$用途: 函数：请补充业务用途
参数: p_station_id bigint, p_device_id bigint, p_metric_id bigint, p_ts_raw timestamp with time zone
返回: integer
-- 示例：函数调用
SELECT * FROM api.delete_measurement(:p1, :p2, :p3, :p4);$DOC$;

COMMENT ON FUNCTION "api"."delete_measurements_by_filter"(p_station_ids bigint[], p_start_ts timestamp with time zone, p_end_ts timestamp with time zone, p_device_ids bigint[], p_metric_ids bigint[], p_batch_size integer) IS $DOC$用途: 函数：请补充业务用途
参数: p_station_ids bigint[], p_start_ts timestamp with time zone, p_end_ts timestamp with time zone, p_device_ids bigint[], p_metric_ids bigint[], p_batch_size integer
返回: TABLE(total_deleted integer)
-- 示例：函数调用
SELECT * FROM api.delete_measurements_by_filter(:p1, :p2, :p3, :p4, :p5, :p6);$DOC$;

COMMENT ON FUNCTION "api"."get_measurements"(p_station_ids bigint[], p_start_ts timestamp with time zone, p_end_ts timestamp with time zone, p_device_ids bigint[], p_metric_ids bigint[], p_limit integer, p_offset integer) IS $DOC$用途: 函数：请补充业务用途
参数: p_station_ids bigint[], p_start_ts timestamp with time zone, p_end_ts timestamp with time zone, p_device_ids bigint[], p_metric_ids bigint[], p_limit integer, p_offset integer
返回: TABLE(station_id bigint, device_id bigint, metric_id bigint, ts_raw timestamp with time zone, ts_bucket timestamp with time zone, value numeric, source_hint text, inserted_at timestamp with time zone)
-- 示例：函数调用
SELECT * FROM api.get_measurements(:p1, :p2, :p3, :p4, :p5, :p6, :p7);$DOC$;

COMMENT ON FUNCTION "api"."update_measurement_value"(p_station_id bigint, p_device_id bigint, p_metric_id bigint, p_ts_raw timestamp with time zone, p_new_value numeric, p_source_hint text) IS $DOC$用途: 函数：请补充业务用途
参数: p_station_id bigint, p_device_id bigint, p_metric_id bigint, p_ts_raw timestamp with time zone, p_new_value numeric, p_source_hint text
返回: integer
-- 示例：函数调用
SELECT * FROM api.update_measurement_value(:p1, :p2, :p3, :p4, :p5, :p6);$DOC$;

COMMENT ON FUNCTION "api"."upsert_measurement"(p_station_id bigint, p_device_id bigint, p_metric_id bigint, p_ts_raw timestamp with time zone, p_value numeric, p_source_hint text) IS $DOC$用途: 函数：请补充业务用途
参数: p_station_id bigint, p_device_id bigint, p_metric_id bigint, p_ts_raw timestamp with time zone, p_value numeric, p_source_hint text
返回: boolean
-- 示例：函数调用
SELECT * FROM api.upsert_measurement(:p1, :p2, :p3, :p4, :p5, :p6);$DOC$;

COMMENT ON FUNCTION "api"."upsert_measurements_json"(p_rows jsonb) IS $DOC$用途: 函数：请补充业务用途
参数: p_rows jsonb
返回: TABLE(processed integer, succeeded integer, failed integer)
-- 示例：函数调用
SELECT * FROM api.upsert_measurements_json(:p1);$DOC$;

COMMENT ON TABLE "monitoring"."ab_test_results" IS $DOC$用途: 数据表：monitoring.ab_test_results（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM monitoring.ab_test_results LIMIT 100;$DOC$;

COMMENT ON COLUMN "monitoring"."ab_test_results"."run_id" IS $DOC$字段：run_id（说明待补充）$DOC$;

COMMENT ON COLUMN "monitoring"."ab_test_results"."phase" IS $DOC$字段：phase（说明待补充）$DOC$;

COMMENT ON COLUMN "monitoring"."ab_test_results"."rows_count" IS $DOC$字段：rows_count（说明待补充）$DOC$;

COMMENT ON COLUMN "monitoring"."ab_test_results"."duration_ms" IS $DOC$字段：duration_ms（说明待补充）$DOC$;

COMMENT ON COLUMN "monitoring"."ab_test_results"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "monitoring"."ab_test_runs" IS $DOC$用途: 数据表：monitoring.ab_test_runs（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM monitoring.ab_test_runs LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM monitoring.ab_test_runs
WHERE station_id = :station_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "monitoring"."ab_test_runs"."id" IS $DOC$ID（主键或标识）$DOC$;

COMMENT ON COLUMN "monitoring"."ab_test_runs"."run_time" IS $DOC$字段：run_time（说明待补充）$DOC$;

COMMENT ON COLUMN "monitoring"."ab_test_runs"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "monitoring"."ab_test_runs"."start_ts" IS $DOC$字段：start_ts（说明待补充）$DOC$;

COMMENT ON COLUMN "monitoring"."ab_test_runs"."end_ts" IS $DOC$字段：end_ts（说明待补充）$DOC$;

COMMENT ON COLUMN "monitoring"."ab_test_runs"."metric_ids" IS $DOC$字段：metric_ids（说明待补充）$DOC$;

COMMENT ON TABLE "monitoring"."pgss_snapshot" IS $DOC$用途: 数据表：monitoring.pgss_snapshot（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM monitoring.pgss_snapshot LIMIT 100;$DOC$;

COMMENT ON COLUMN "monitoring"."pgss_snapshot"."snapshot_time" IS $DOC$字段：snapshot_time（说明待补充）$DOC$;

COMMENT ON COLUMN "monitoring"."pgss_snapshot"."dbname" IS $DOC$字段：dbname（说明待补充）$DOC$;

COMMENT ON COLUMN "monitoring"."pgss_snapshot"."userid" IS $DOC$字段：userid（说明待补充）$DOC$;

COMMENT ON COLUMN "monitoring"."pgss_snapshot"."queryid" IS $DOC$字段：queryid（说明待补充）$DOC$;

COMMENT ON COLUMN "monitoring"."pgss_snapshot"."calls" IS $DOC$字段：calls（说明待补充）$DOC$;

COMMENT ON COLUMN "monitoring"."pgss_snapshot"."rows" IS $DOC$字段：rows（说明待补充）$DOC$;

COMMENT ON COLUMN "monitoring"."pgss_snapshot"."blk_read_time" IS $DOC$字段：blk_read_time（说明待补充）$DOC$;

COMMENT ON COLUMN "monitoring"."pgss_snapshot"."blk_write_time" IS $DOC$字段：blk_write_time（说明待补充）$DOC$;

COMMENT ON COLUMN "monitoring"."pgss_snapshot"."temp_blks_read" IS $DOC$字段：temp_blks_read（说明待补充）$DOC$;

COMMENT ON COLUMN "monitoring"."pgss_snapshot"."temp_blks_written" IS $DOC$字段：temp_blks_written（说明待补充）$DOC$;

COMMENT ON VIEW "monitoring"."v_mv_hit_audit" IS $DOC$用途: 视图：用于聚合/便捷查询
使用方法: 直接查询
-- 示例：查看视图内容
SELECT * FROM monitoring.v_mv_hit_audit LIMIT 100;$DOC$;

COMMENT ON VIEW "monitoring"."v_query_coverage" IS $DOC$用途: 视图：用于聚合/便捷查询
使用方法: 直接查询
-- 示例：查看视图内容
SELECT * FROM monitoring.v_query_coverage LIMIT 100;$DOC$;

COMMENT ON FUNCTION "monitoring"."capture_pgss_snapshot"() IS $DOC$用途: 函数：请补充业务用途
参数: 
返回: integer
-- 示例：函数调用
SELECT * FROM monitoring.capture_pgss_snapshot();$DOC$;

COMMENT ON FUNCTION "monitoring"."cleanup_pgss_snapshot"(retention_days integer) IS $DOC$用途: 函数：请补充业务用途
参数: retention_days integer
返回: integer
-- 示例：函数调用
SELECT * FROM monitoring.cleanup_pgss_snapshot(:p1);$DOC$;

COMMENT ON FUNCTION "monitoring"."ensure_active_indexes"(window_days integer) IS $DOC$用途: 函数：请补充业务用途
参数: window_days integer
返回: integer
-- 示例：函数调用
SELECT * FROM monitoring.ensure_active_indexes(:p1);$DOC$;

COMMENT ON FUNCTION "monitoring"."run_ab_test"(p_station_id bigint, p_start_ts timestamp with time zone, p_end_ts timestamp with time zone, p_metric_ids bigint[]) IS $DOC$用途: 函数：请补充业务用途
参数: p_station_id bigint, p_start_ts timestamp with time zone, p_end_ts timestamp with time zone, p_metric_ids bigint[]
返回: bigint
-- 示例：函数调用
SELECT * FROM monitoring.run_ab_test(:p1, :p2, :p3, :p4);$DOC$;

COMMENT ON TABLE "public"."completion_audit" IS $DOC$用途: 数据表：public.completion_audit（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.completion_audit LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."completion_audit"."id" IS $DOC$审计记录ID$DOC$;

COMMENT ON COLUMN "public"."completion_audit"."run_id" IS $DOC$运行ID（唯一）$DOC$;

COMMENT ON COLUMN "public"."completion_audit"."coverage_before" IS $DOC$补全前覆盖率$DOC$;

COMMENT ON COLUMN "public"."completion_audit"."coverage_after" IS $DOC$补全后覆盖率$DOC$;

COMMENT ON COLUMN "public"."completion_audit"."missing_before" IS $DOC$补全前缺失点数$DOC$;

COMMENT ON COLUMN "public"."completion_audit"."missing_after" IS $DOC$补全后缺失点数$DOC$;

COMMENT ON COLUMN "public"."completion_audit"."max_gap_before_sec" IS $DOC$补全前最大缺口（秒）$DOC$;

COMMENT ON COLUMN "public"."completion_audit"."max_gap_after_sec" IS $DOC$补全后最大缺口（秒）$DOC$;

COMMENT ON COLUMN "public"."completion_audit"."count_ffill" IS $DOC$前向填充次数$DOC$;

COMMENT ON COLUMN "public"."completion_audit"."count_mean" IS $DOC$均值填充次数$DOC$;

COMMENT ON COLUMN "public"."completion_audit"."count_reg" IS $DOC$回归填充次数$DOC$;

COMMENT ON COLUMN "public"."completion_audit"."count_curve" IS $DOC$曲线填充次数$DOC$;

COMMENT ON COLUMN "public"."completion_audit"."count_skipped_long_gap" IS $DOC$跳过的长缺口次数$DOC$;

COMMENT ON COLUMN "public"."completion_audit"."startup_drop_ratio" IS $DOC$启停落点剔除比例$DOC$;

COMMENT ON COLUMN "public"."completion_audit"."rejects_counts" IS $DOC$拒绝计数（jsonb，按类别）$DOC$;

COMMENT ON COLUMN "public"."completion_audit"."thresholds_snapshot_ref" IS $DOC$阈值快照引用（文本）$DOC$;

COMMENT ON COLUMN "public"."completion_audit"."group_consistency" IS $DOC$组一致性审计（jsonb）$DOC$;

COMMENT ON COLUMN "public"."completion_audit"."audit_time" IS $DOC$审计时间$DOC$;

COMMENT ON TABLE "public"."completion_failures" IS $DOC$用途: 数据表：public.completion_failures（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.completion_failures LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."completion_failures"."id" IS $DOC$失败记录ID$DOC$;

COMMENT ON COLUMN "public"."completion_failures"."run_id" IS $DOC$运行ID$DOC$;

COMMENT ON COLUMN "public"."completion_failures"."object_key" IS $DOC$对象键（jsonb：station_id/device_id/metric_id）$DOC$;

COMMENT ON COLUMN "public"."completion_failures"."gap_id" IS $DOC$缺口段ID$DOC$;

COMMENT ON COLUMN "public"."completion_failures"."reason_code" IS $DOC$失败原因代码$DOC$;

COMMENT ON COLUMN "public"."completion_failures"."evidence_uri" IS $DOC$证据URI$DOC$;

COMMENT ON COLUMN "public"."completion_failures"."suggested_action" IS $DOC$建议动作$DOC$;

COMMENT ON COLUMN "public"."completion_failures"."created_at" IS $DOC$创建时间$DOC$;

COMMENT ON TABLE "public"."completion_runs" IS $DOC$用途: 数据表：public.completion_runs（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.completion_runs LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.completion_runs
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."completion_runs"."run_id" IS $DOC$运行ID$DOC$;

COMMENT ON COLUMN "public"."completion_runs"."station_id" IS $DOC$泵站ID$DOC$;

COMMENT ON COLUMN "public"."completion_runs"."device_id" IS $DOC$设备ID$DOC$;

COMMENT ON COLUMN "public"."completion_runs"."start_ts" IS $DOC$运行时间窗起（timestamptz）$DOC$;

COMMENT ON COLUMN "public"."completion_runs"."end_ts" IS $DOC$运行时间窗止（timestamptz）$DOC$;

COMMENT ON COLUMN "public"."completion_runs"."code_version" IS $DOC$代码版本标识（如 git 哈希）$DOC$;

COMMENT ON COLUMN "public"."completion_runs"."imputation_version" IS $DOC$补全过程版本/算法版本$DOC$;

COMMENT ON COLUMN "public"."completion_runs"."config_snapshot" IS $DOC$配置快照（jsonb）$DOC$;

COMMENT ON COLUMN "public"."completion_runs"."thresholds_snapshot" IS $DOC$阈值快照（jsonb）$DOC$;

COMMENT ON COLUMN "public"."completion_runs"."rows_read" IS $DOC$读取的事实点数量$DOC$;

COMMENT ON COLUMN "public"."completion_runs"."duration_ms" IS $DOC$运行耗时（毫秒）$DOC$;

COMMENT ON COLUMN "public"."completion_runs"."steps_total" IS $DOC$步骤数量$DOC$;

COMMENT ON COLUMN "public"."completion_runs"."rerun_policy" IS $DOC$复跑策略：append/overwrite/skip$DOC$;

COMMENT ON COLUMN "public"."completion_runs"."parent_run_id" IS $DOC$父运行ID（复跑来源）$DOC$;

COMMENT ON COLUMN "public"."completion_runs"."superseded_by_run_id" IS $DOC$被替代运行ID（被后续运行覆盖）$DOC$;

COMMENT ON COLUMN "public"."completion_runs"."idempotency_key" IS $DOC$幂等键（避免重复写入）$DOC$;

COMMENT ON COLUMN "public"."completion_runs"."group_context" IS $DOC$泵组上下文（jsonb）$DOC$;

COMMENT ON COLUMN "public"."completion_runs"."status_reason" IS $DOC$状态原因摘要$DOC$;

COMMENT ON COLUMN "public"."completion_runs"."error_code" IS $DOC$错误代码摘要$DOC$;

COMMENT ON COLUMN "public"."completion_runs"."created_at" IS $DOC$创建时间$DOC$;

COMMENT ON TABLE "public"."completion_steps" IS $DOC$用途: 数据表：public.completion_steps（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.completion_steps LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.completion_steps
WHERE device_id = :device_id AND metric_id = :metric_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."completion_steps"."id" IS $DOC$步骤记录ID$DOC$;

COMMENT ON COLUMN "public"."completion_steps"."run_id" IS $DOC$所属运行ID$DOC$;

COMMENT ON COLUMN "public"."completion_steps"."device_id" IS $DOC$设备ID$DOC$;

COMMENT ON COLUMN "public"."completion_steps"."metric_id" IS $DOC$指标ID$DOC$;

COMMENT ON COLUMN "public"."completion_steps"."gap_id" IS $DOC$缺口段ID$DOC$;

COMMENT ON COLUMN "public"."completion_steps"."gap_start_ts" IS $DOC$缺口开始时间$DOC$;

COMMENT ON COLUMN "public"."completion_steps"."gap_end_ts" IS $DOC$缺口结束时间$DOC$;

COMMENT ON COLUMN "public"."completion_steps"."gap_len_sec" IS $DOC$缺口时长（秒）$DOC$;

COMMENT ON COLUMN "public"."completion_steps"."gap_class" IS $DOC$缺口分类（short/medium/long/in_startstop）$DOC$;

COMMENT ON COLUMN "public"."completion_steps"."in_startstop_window" IS $DOC$是否位于启停窗口内$DOC$;

COMMENT ON COLUMN "public"."completion_steps"."methods_tried" IS $DOC$尝试的方法列表（jsonb）$DOC$;

COMMENT ON COLUMN "public"."completion_steps"."fallback_path" IS $DOC$回退路径$DOC$;

COMMENT ON COLUMN "public"."completion_steps"."confidence_reason" IS $DOC$置信理由（数组）$DOC$;

COMMENT ON COLUMN "public"."completion_steps"."residual_stats" IS $DOC$残差统计（jsonb，可选）$DOC$;

COMMENT ON COLUMN "public"."completion_steps"."step_duration_ms" IS $DOC$步骤耗时（毫秒）$DOC$;

COMMENT ON COLUMN "public"."completion_steps"."rows_considered" IS $DOC$考虑的点数量$DOC$;

COMMENT ON COLUMN "public"."completion_steps"."data_source" IS $DOC$数据来源（original/derived）$DOC$;

COMMENT ON COLUMN "public"."completion_steps"."created_at" IS $DOC$创建时间$DOC$;

COMMENT ON TABLE "public"."device_metric_candidates" IS $DOC$用途: 数据表：public.device_metric_candidates（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.device_metric_candidates LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.device_metric_candidates
WHERE device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."device_metric_candidates"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."device_metric_candidates"."metrics" IS $DOC$字段：metrics（说明待补充）$DOC$;

COMMENT ON TABLE "public"."device_rated_params" IS $DOC$用途: 数据表：public.device_rated_params（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.device_rated_params LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.device_rated_params
WHERE device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."device_rated_params"."id" IS $DOC$ID（PK）$DOC$;

COMMENT ON COLUMN "public"."device_rated_params"."device_id" IS $DOC$设备ID$DOC$;

COMMENT ON COLUMN "public"."device_rated_params"."param_key" IS $DOC$参数键（如 rated_power）$DOC$;

COMMENT ON COLUMN "public"."device_rated_params"."value_numeric" IS $DOC$数值（numeric）$DOC$;

COMMENT ON COLUMN "public"."device_rated_params"."value_text" IS $DOC$文本值$DOC$;

COMMENT ON COLUMN "public"."device_rated_params"."unit" IS $DOC$单位$DOC$;

COMMENT ON COLUMN "public"."device_rated_params"."source" IS $DOC$来源$DOC$;

COMMENT ON COLUMN "public"."device_rated_params"."effective_from" IS $DOC$生效起$DOC$;

COMMENT ON COLUMN "public"."device_rated_params"."effective_to" IS $DOC$生效止$DOC$;

COMMENT ON COLUMN "public"."device_rated_params"."created_at" IS $DOC$创建时间$DOC$;

COMMENT ON COLUMN "public"."device_rated_params"."updated_at" IS $DOC$更新时间$DOC$;

COMMENT ON TABLE "public"."device_running_thresholds" IS $DOC$用途: 数据表：public.device_running_thresholds（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.device_running_thresholds LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.device_running_thresholds
WHERE device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."device_running_thresholds"."device_id" IS $DOC$设备ID（PK）$DOC$;

COMMENT ON COLUMN "public"."device_running_thresholds"."enable_i" IS $DOC$是否启用电流判定（取三相最大）$DOC$;

COMMENT ON COLUMN "public"."device_running_thresholds"."enable_p" IS $DOC$是否启用功率判定$DOC$;

COMMENT ON COLUMN "public"."device_running_thresholds"."enable_f" IS $DOC$是否启用频率判定$DOC$;

COMMENT ON COLUMN "public"."device_running_thresholds"."i_on" IS $DOC$电流开启阈值$DOC$;

COMMENT ON COLUMN "public"."device_running_thresholds"."i_off" IS $DOC$电流关闭阈值$DOC$;

COMMENT ON COLUMN "public"."device_running_thresholds"."p_on" IS $DOC$功率开启阈值$DOC$;

COMMENT ON COLUMN "public"."device_running_thresholds"."p_off" IS $DOC$功率关闭阈值$DOC$;

COMMENT ON COLUMN "public"."device_running_thresholds"."f_on" IS $DOC$频率开启阈值$DOC$;

COMMENT ON COLUMN "public"."device_running_thresholds"."f_off" IS $DOC$频率关闭阈值$DOC$;

COMMENT ON COLUMN "public"."device_running_thresholds"."grace_hold_secs" IS $DOC$缺报延续秒数$DOC$;

COMMENT ON COLUMN "public"."device_running_thresholds"."min_run_secs" IS $DOC$最小运行段长度（用于窗口聚合）$DOC$;

COMMENT ON COLUMN "public"."device_running_thresholds"."min_stop_secs" IS $DOC$最小停机段长度（用于窗口聚合）$DOC$;

COMMENT ON COLUMN "public"."device_running_thresholds"."smoothing_secs" IS $DOC$平滑窗口秒数（可选）$DOC$;

COMMENT ON COLUMN "public"."device_running_thresholds"."updated_at" IS $DOC$更新时间$DOC$;

COMMENT ON COLUMN "public"."device_running_thresholds"."updated_by" IS $DOC$更新人/来源$DOC$;

COMMENT ON TABLE "public"."dim_devices" IS $DOC$用途: 设备维表
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.dim_devices LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.dim_devices
WHERE station_id = :station_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."dim_devices"."id" IS $DOC$设备ID（PK）$DOC$;

COMMENT ON COLUMN "public"."dim_devices"."station_id" IS $DOC$泵站ID$DOC$;

COMMENT ON COLUMN "public"."dim_devices"."name" IS $DOC$设备名称（站内唯一）$DOC$;

COMMENT ON COLUMN "public"."dim_devices"."type" IS $DOC$设备类型（pump 等）$DOC$;

COMMENT ON COLUMN "public"."dim_devices"."pump_type" IS $DOC$泵类型（variable_frequency/soft_start 等）$DOC$;

COMMENT ON COLUMN "public"."dim_devices"."extra" IS $DOC$额外信息（jsonb）$DOC$;

COMMENT ON COLUMN "public"."dim_devices"."created_at" IS $DOC$创建时间$DOC$;

COMMENT ON TABLE "public"."dim_mapping_items" IS $DOC$用途: 数据表：public.dim_mapping_items（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.dim_mapping_items LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."dim_mapping_items"."id" IS $DOC$ID（PK）$DOC$;

COMMENT ON COLUMN "public"."dim_mapping_items"."mapping_hash" IS $DOC$映射哈希（用于快照一致性）$DOC$;

COMMENT ON COLUMN "public"."dim_mapping_items"."station_name" IS $DOC$站点名（源）$DOC$;

COMMENT ON COLUMN "public"."dim_mapping_items"."device_name" IS $DOC$设备名（源）$DOC$;

COMMENT ON COLUMN "public"."dim_mapping_items"."metric_key" IS $DOC$指标键（源）$DOC$;

COMMENT ON COLUMN "public"."dim_mapping_items"."source_hint" IS $DOC$来源提示$DOC$;

COMMENT ON COLUMN "public"."dim_mapping_items"."created_at" IS $DOC$创建时间$DOC$;

COMMENT ON TABLE "public"."dim_metric_config" IS $DOC$用途: 指标配置维表（指标ID/键/单位等）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.dim_metric_config LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."dim_metric_config"."id" IS $DOC$指标ID（PK）$DOC$;

COMMENT ON COLUMN "public"."dim_metric_config"."metric_key" IS $DOC$指标键（唯一，如 pump_frequency）$DOC$;

COMMENT ON COLUMN "public"."dim_metric_config"."unit" IS $DOC$单位（如 Hz、kW、A）$DOC$;

COMMENT ON COLUMN "public"."dim_metric_config"."unit_display" IS $DOC$单位显示$DOC$;

COMMENT ON COLUMN "public"."dim_metric_config"."decimals_policy" IS $DOC$小数策略（as_is 等）$DOC$;

COMMENT ON COLUMN "public"."dim_metric_config"."fixed_decimals" IS $DOC$固定小数位（可选）$DOC$;

COMMENT ON COLUMN "public"."dim_metric_config"."value_type" IS $DOC$值类型（number 等）$DOC$;

COMMENT ON COLUMN "public"."dim_metric_config"."valid_min" IS $DOC$有效最小值$DOC$;

COMMENT ON COLUMN "public"."dim_metric_config"."valid_max" IS $DOC$有效最大值$DOC$;

COMMENT ON COLUMN "public"."dim_metric_config"."created_at" IS $DOC$创建时间$DOC$;

COMMENT ON COLUMN "public"."dim_metric_config"."updated_at" IS $DOC$更新时间$DOC$;

COMMENT ON TABLE "public"."dim_stations" IS $DOC$用途: 泵站维表
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.dim_stations LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."dim_stations"."id" IS $DOC$泵站ID（PK）$DOC$;

COMMENT ON COLUMN "public"."dim_stations"."name" IS $DOC$泵站名称$DOC$;

COMMENT ON COLUMN "public"."dim_stations"."extra" IS $DOC$额外信息（jsonb，建议包含 tz）$DOC$;

COMMENT ON COLUMN "public"."dim_stations"."created_at" IS $DOC$创建时间$DOC$;

COMMENT ON TABLE "public"."fact_measurements" IS $DOC$用途: 时序事实表：每行表示某设备某指标在某一时间点的数值（整秒对齐）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.fact_measurements LIMIT 100;

-- 示例：按时间窗口查询
SELECT * FROM public.fact_measurements
WHERE ts_raw >= :start_ts AND ts_raw < :end_ts
ORDER BY ts_raw ASC
LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.fact_measurements
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."fact_measurements"."id" IS $DOC$ID（PK）$DOC$;

COMMENT ON COLUMN "public"."fact_measurements"."station_id" IS $DOC$泵站ID$DOC$;

COMMENT ON COLUMN "public"."fact_measurements"."device_id" IS $DOC$设备ID$DOC$;

COMMENT ON COLUMN "public"."fact_measurements"."metric_id" IS $DOC$指标ID$DOC$;

COMMENT ON COLUMN "public"."fact_measurements"."ts_raw" IS $DOC$原始时间（建议 UTC）$DOC$;

COMMENT ON COLUMN "public"."fact_measurements"."ts_bucket" IS $DOC$整秒对齐时间$DOC$;

COMMENT ON COLUMN "public"."fact_measurements"."value" IS $DOC$数值$DOC$;

COMMENT ON COLUMN "public"."fact_measurements"."source_hint" IS $DOC$来源提示$DOC$;

COMMENT ON COLUMN "public"."fact_measurements"."inserted_at" IS $DOC$插入时间$DOC$;

COMMENT ON TABLE "public"."metric_capability_policy" IS $DOC$用途: 数据表：public.metric_capability_policy（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.metric_capability_policy LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."metric_capability_policy"."metric_key" IS $DOC$指标键；与 dim_metric_config.metric_key 一一对应$DOC$;

COMMENT ON COLUMN "public"."metric_capability_policy"."acquisition_status" IS $DOC$获取情况：不能/可能/可以；不能=无法直接采集，可能=部分站点可采，
可以=肯定可采$DOC$;

COMMENT ON COLUMN "public"."metric_capability_policy"."compute_flag" IS $DOC$是否计算补充：需要=必须通过其他指标计算获得；不需要=不可计算或不需要计算$DOC$;

COMMENT ON COLUMN "public"."metric_capability_policy"."updated_at" IS $DOC$策略最后更新时间$DOC$;

COMMENT ON COLUMN "public"."metric_capability_policy"."updated_by" IS $DOC$最后更新人（可填 sys/脚本名）$DOC$;

COMMENT ON TABLE "public"."metrics_presence_per_second_device" IS $DOC$用途: 设备-秒级指标可用性/需要计算标记
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.metrics_presence_per_second_device LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.metrics_presence_per_second_device
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."metrics_presence_per_second_device"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."metrics_presence_per_second_device"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."metrics_presence_per_second_device"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."metrics_presence_per_second_device"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."metrics_presence_per_second_device"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."metrics_presence_per_second_device"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."metrics_presence_per_second_device_legacy" IS $DOC$用途: 数据表：public.metrics_presence_per_second_device_legacy（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.metrics_presence_per_second_device_legacy LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.metrics_presence_per_second_device_legacy
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."metrics_presence_per_second_device_legacy"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."metrics_presence_per_second_device_legacy"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."metrics_presence_per_second_device_legacy"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."metrics_presence_per_second_device_legacy"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."metrics_presence_per_second_device_legacy"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."metrics_presence_per_second_device_legacy"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202507" IS $DOC$用途: 数据表：public.mpps_w_202507（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202507 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202507
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202507_0" IS $DOC$用途: 数据表：public.mpps_w_202507_0（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202507_0 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202507_0
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_0"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_0"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_0"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_0"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_0"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_0"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202507_1" IS $DOC$用途: 数据表：public.mpps_w_202507_1（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202507_1 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202507_1
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_1"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_1"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_1"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_1"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_1"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_1"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202507_10" IS $DOC$用途: 数据表：public.mpps_w_202507_10（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202507_10 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202507_10
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_10"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_10"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_10"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_10"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_10"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_10"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202507_11" IS $DOC$用途: 数据表：public.mpps_w_202507_11（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202507_11 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202507_11
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_11"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_11"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_11"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_11"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_11"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_11"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202507_12" IS $DOC$用途: 数据表：public.mpps_w_202507_12（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202507_12 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202507_12
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_12"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_12"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_12"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_12"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_12"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_12"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202507_13" IS $DOC$用途: 数据表：public.mpps_w_202507_13（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202507_13 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202507_13
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_13"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_13"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_13"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_13"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_13"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_13"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202507_14" IS $DOC$用途: 数据表：public.mpps_w_202507_14（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202507_14 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202507_14
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_14"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_14"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_14"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_14"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_14"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_14"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202507_15" IS $DOC$用途: 数据表：public.mpps_w_202507_15（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202507_15 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202507_15
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_15"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_15"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_15"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_15"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_15"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_15"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202507_2" IS $DOC$用途: 数据表：public.mpps_w_202507_2（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202507_2 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202507_2
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_2"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_2"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_2"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_2"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_2"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_2"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202507_3" IS $DOC$用途: 数据表：public.mpps_w_202507_3（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202507_3 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202507_3
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_3"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_3"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_3"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_3"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_3"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_3"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202507_4" IS $DOC$用途: 数据表：public.mpps_w_202507_4（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202507_4 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202507_4
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_4"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_4"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_4"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_4"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_4"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_4"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202507_5" IS $DOC$用途: 数据表：public.mpps_w_202507_5（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202507_5 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202507_5
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_5"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_5"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_5"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_5"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_5"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_5"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202507_6" IS $DOC$用途: 数据表：public.mpps_w_202507_6（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202507_6 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202507_6
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_6"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_6"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_6"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_6"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_6"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_6"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202507_7" IS $DOC$用途: 数据表：public.mpps_w_202507_7（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202507_7 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202507_7
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_7"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_7"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_7"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_7"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_7"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_7"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202507_8" IS $DOC$用途: 数据表：public.mpps_w_202507_8（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202507_8 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202507_8
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_8"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_8"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_8"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_8"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_8"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_8"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202507_9" IS $DOC$用途: 数据表：public.mpps_w_202507_9（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202507_9 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202507_9
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_9"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_9"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_9"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_9"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_9"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202507_9"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202508" IS $DOC$用途: 数据表：public.mpps_w_202508（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202508 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202508
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202508_0" IS $DOC$用途: 数据表：public.mpps_w_202508_0（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202508_0 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202508_0
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_0"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_0"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_0"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_0"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_0"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_0"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202508_1" IS $DOC$用途: 数据表：public.mpps_w_202508_1（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202508_1 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202508_1
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_1"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_1"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_1"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_1"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_1"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_1"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202508_10" IS $DOC$用途: 数据表：public.mpps_w_202508_10（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202508_10 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202508_10
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_10"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_10"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_10"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_10"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_10"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_10"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202508_11" IS $DOC$用途: 数据表：public.mpps_w_202508_11（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202508_11 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202508_11
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_11"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_11"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_11"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_11"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_11"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_11"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202508_12" IS $DOC$用途: 数据表：public.mpps_w_202508_12（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202508_12 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202508_12
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_12"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_12"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_12"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_12"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_12"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_12"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202508_13" IS $DOC$用途: 数据表：public.mpps_w_202508_13（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202508_13 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202508_13
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_13"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_13"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_13"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_13"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_13"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_13"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202508_14" IS $DOC$用途: 数据表：public.mpps_w_202508_14（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202508_14 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202508_14
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_14"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_14"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_14"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_14"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_14"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_14"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202508_15" IS $DOC$用途: 数据表：public.mpps_w_202508_15（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202508_15 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202508_15
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_15"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_15"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_15"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_15"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_15"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_15"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202508_2" IS $DOC$用途: 数据表：public.mpps_w_202508_2（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202508_2 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202508_2
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_2"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_2"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_2"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_2"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_2"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_2"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202508_3" IS $DOC$用途: 数据表：public.mpps_w_202508_3（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202508_3 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202508_3
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_3"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_3"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_3"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_3"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_3"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_3"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202508_4" IS $DOC$用途: 数据表：public.mpps_w_202508_4（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202508_4 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202508_4
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_4"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_4"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_4"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_4"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_4"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_4"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202508_5" IS $DOC$用途: 数据表：public.mpps_w_202508_5（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202508_5 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202508_5
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_5"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_5"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_5"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_5"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_5"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_5"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202508_6" IS $DOC$用途: 数据表：public.mpps_w_202508_6（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202508_6 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202508_6
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_6"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_6"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_6"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_6"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_6"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_6"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202508_7" IS $DOC$用途: 数据表：public.mpps_w_202508_7（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202508_7 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202508_7
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_7"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_7"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_7"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_7"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_7"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_7"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202508_8" IS $DOC$用途: 数据表：public.mpps_w_202508_8（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202508_8 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202508_8
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_8"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_8"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_8"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_8"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_8"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_8"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202508_9" IS $DOC$用途: 数据表：public.mpps_w_202508_9（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202508_9 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202508_9
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_9"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_9"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_9"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_9"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_9"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202508_9"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202509" IS $DOC$用途: 数据表：public.mpps_w_202509（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202509 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202509
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202509_0" IS $DOC$用途: 数据表：public.mpps_w_202509_0（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202509_0 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202509_0
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_0"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_0"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_0"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_0"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_0"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_0"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202509_1" IS $DOC$用途: 数据表：public.mpps_w_202509_1（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202509_1 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202509_1
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_1"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_1"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_1"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_1"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_1"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_1"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202509_10" IS $DOC$用途: 数据表：public.mpps_w_202509_10（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202509_10 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202509_10
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_10"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_10"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_10"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_10"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_10"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_10"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202509_11" IS $DOC$用途: 数据表：public.mpps_w_202509_11（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202509_11 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202509_11
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_11"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_11"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_11"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_11"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_11"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_11"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202509_12" IS $DOC$用途: 数据表：public.mpps_w_202509_12（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202509_12 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202509_12
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_12"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_12"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_12"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_12"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_12"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_12"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202509_13" IS $DOC$用途: 数据表：public.mpps_w_202509_13（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202509_13 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202509_13
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_13"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_13"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_13"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_13"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_13"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_13"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202509_14" IS $DOC$用途: 数据表：public.mpps_w_202509_14（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202509_14 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202509_14
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_14"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_14"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_14"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_14"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_14"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_14"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202509_15" IS $DOC$用途: 数据表：public.mpps_w_202509_15（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202509_15 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202509_15
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_15"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_15"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_15"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_15"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_15"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_15"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202509_2" IS $DOC$用途: 数据表：public.mpps_w_202509_2（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202509_2 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202509_2
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_2"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_2"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_2"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_2"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_2"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_2"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202509_3" IS $DOC$用途: 数据表：public.mpps_w_202509_3（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202509_3 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202509_3
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_3"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_3"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_3"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_3"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_3"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_3"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202509_4" IS $DOC$用途: 数据表：public.mpps_w_202509_4（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202509_4 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202509_4
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_4"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_4"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_4"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_4"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_4"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_4"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202509_5" IS $DOC$用途: 数据表：public.mpps_w_202509_5（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202509_5 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202509_5
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_5"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_5"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_5"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_5"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_5"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_5"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202509_6" IS $DOC$用途: 数据表：public.mpps_w_202509_6（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202509_6 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202509_6
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_6"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_6"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_6"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_6"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_6"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_6"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202509_7" IS $DOC$用途: 数据表：public.mpps_w_202509_7（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202509_7 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202509_7
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_7"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_7"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_7"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_7"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_7"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_7"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202509_8" IS $DOC$用途: 数据表：public.mpps_w_202509_8（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202509_8 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202509_8
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_8"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_8"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_8"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_8"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_8"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_8"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202509_9" IS $DOC$用途: 数据表：public.mpps_w_202509_9（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202509_9 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202509_9
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_9"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_9"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_9"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_9"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_9"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202509_9"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202510" IS $DOC$用途: 数据表：public.mpps_w_202510（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202510 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202510
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202510_0" IS $DOC$用途: 数据表：public.mpps_w_202510_0（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202510_0 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202510_0
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_0"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_0"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_0"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_0"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_0"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_0"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202510_1" IS $DOC$用途: 数据表：public.mpps_w_202510_1（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202510_1 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202510_1
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_1"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_1"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_1"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_1"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_1"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_1"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202510_10" IS $DOC$用途: 数据表：public.mpps_w_202510_10（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202510_10 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202510_10
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_10"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_10"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_10"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_10"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_10"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_10"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202510_11" IS $DOC$用途: 数据表：public.mpps_w_202510_11（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202510_11 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202510_11
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_11"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_11"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_11"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_11"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_11"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_11"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202510_12" IS $DOC$用途: 数据表：public.mpps_w_202510_12（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202510_12 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202510_12
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_12"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_12"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_12"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_12"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_12"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_12"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202510_13" IS $DOC$用途: 数据表：public.mpps_w_202510_13（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202510_13 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202510_13
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_13"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_13"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_13"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_13"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_13"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_13"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202510_14" IS $DOC$用途: 数据表：public.mpps_w_202510_14（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202510_14 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202510_14
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_14"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_14"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_14"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_14"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_14"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_14"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202510_15" IS $DOC$用途: 数据表：public.mpps_w_202510_15（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202510_15 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202510_15
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_15"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_15"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_15"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_15"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_15"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_15"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202510_2" IS $DOC$用途: 数据表：public.mpps_w_202510_2（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202510_2 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202510_2
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_2"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_2"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_2"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_2"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_2"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_2"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202510_3" IS $DOC$用途: 数据表：public.mpps_w_202510_3（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202510_3 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202510_3
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_3"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_3"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_3"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_3"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_3"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_3"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202510_4" IS $DOC$用途: 数据表：public.mpps_w_202510_4（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202510_4 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202510_4
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_4"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_4"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_4"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_4"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_4"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_4"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202510_5" IS $DOC$用途: 数据表：public.mpps_w_202510_5（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202510_5 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202510_5
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_5"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_5"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_5"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_5"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_5"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_5"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202510_6" IS $DOC$用途: 数据表：public.mpps_w_202510_6（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202510_6 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202510_6
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_6"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_6"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_6"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_6"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_6"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_6"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202510_7" IS $DOC$用途: 数据表：public.mpps_w_202510_7（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202510_7 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202510_7
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_7"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_7"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_7"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_7"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_7"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_7"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202510_8" IS $DOC$用途: 数据表：public.mpps_w_202510_8（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202510_8 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202510_8
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_8"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_8"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_8"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_8"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_8"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_8"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202510_9" IS $DOC$用途: 数据表：public.mpps_w_202510_9（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202510_9 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202510_9
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_9"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_9"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_9"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_9"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_9"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202510_9"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202511" IS $DOC$用途: 数据表：public.mpps_w_202511（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202511 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202511
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202511_0" IS $DOC$用途: 数据表：public.mpps_w_202511_0（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202511_0 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202511_0
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_0"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_0"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_0"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_0"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_0"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_0"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202511_1" IS $DOC$用途: 数据表：public.mpps_w_202511_1（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202511_1 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202511_1
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_1"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_1"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_1"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_1"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_1"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_1"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202511_10" IS $DOC$用途: 数据表：public.mpps_w_202511_10（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202511_10 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202511_10
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_10"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_10"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_10"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_10"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_10"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_10"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202511_11" IS $DOC$用途: 数据表：public.mpps_w_202511_11（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202511_11 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202511_11
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_11"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_11"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_11"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_11"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_11"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_11"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202511_12" IS $DOC$用途: 数据表：public.mpps_w_202511_12（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202511_12 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202511_12
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_12"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_12"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_12"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_12"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_12"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_12"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202511_13" IS $DOC$用途: 数据表：public.mpps_w_202511_13（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202511_13 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202511_13
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_13"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_13"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_13"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_13"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_13"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_13"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202511_14" IS $DOC$用途: 数据表：public.mpps_w_202511_14（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202511_14 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202511_14
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_14"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_14"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_14"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_14"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_14"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_14"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202511_15" IS $DOC$用途: 数据表：public.mpps_w_202511_15（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202511_15 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202511_15
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_15"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_15"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_15"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_15"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_15"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_15"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202511_2" IS $DOC$用途: 数据表：public.mpps_w_202511_2（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202511_2 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202511_2
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_2"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_2"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_2"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_2"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_2"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_2"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202511_3" IS $DOC$用途: 数据表：public.mpps_w_202511_3（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202511_3 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202511_3
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_3"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_3"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_3"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_3"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_3"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_3"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202511_4" IS $DOC$用途: 数据表：public.mpps_w_202511_4（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202511_4 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202511_4
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_4"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_4"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_4"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_4"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_4"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_4"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202511_5" IS $DOC$用途: 数据表：public.mpps_w_202511_5（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202511_5 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202511_5
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_5"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_5"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_5"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_5"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_5"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_5"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202511_6" IS $DOC$用途: 数据表：public.mpps_w_202511_6（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202511_6 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202511_6
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_6"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_6"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_6"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_6"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_6"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_6"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202511_7" IS $DOC$用途: 数据表：public.mpps_w_202511_7（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202511_7 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202511_7
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_7"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_7"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_7"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_7"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_7"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_7"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202511_8" IS $DOC$用途: 数据表：public.mpps_w_202511_8（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202511_8 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202511_8
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_8"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_8"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_8"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_8"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_8"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_8"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202511_9" IS $DOC$用途: 数据表：public.mpps_w_202511_9（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202511_9 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202511_9
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_9"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_9"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_9"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_9"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_9"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202511_9"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202512" IS $DOC$用途: 数据表：public.mpps_w_202512（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202512 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202512
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202512_0" IS $DOC$用途: 数据表：public.mpps_w_202512_0（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202512_0 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202512_0
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_0"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_0"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_0"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_0"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_0"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_0"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202512_1" IS $DOC$用途: 数据表：public.mpps_w_202512_1（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202512_1 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202512_1
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_1"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_1"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_1"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_1"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_1"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_1"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202512_10" IS $DOC$用途: 数据表：public.mpps_w_202512_10（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202512_10 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202512_10
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_10"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_10"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_10"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_10"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_10"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_10"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202512_11" IS $DOC$用途: 数据表：public.mpps_w_202512_11（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202512_11 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202512_11
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_11"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_11"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_11"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_11"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_11"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_11"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202512_12" IS $DOC$用途: 数据表：public.mpps_w_202512_12（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202512_12 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202512_12
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_12"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_12"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_12"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_12"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_12"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_12"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202512_13" IS $DOC$用途: 数据表：public.mpps_w_202512_13（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202512_13 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202512_13
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_13"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_13"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_13"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_13"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_13"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_13"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202512_14" IS $DOC$用途: 数据表：public.mpps_w_202512_14（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202512_14 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202512_14
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_14"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_14"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_14"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_14"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_14"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_14"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202512_15" IS $DOC$用途: 数据表：public.mpps_w_202512_15（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202512_15 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202512_15
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_15"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_15"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_15"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_15"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_15"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_15"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202512_2" IS $DOC$用途: 数据表：public.mpps_w_202512_2（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202512_2 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202512_2
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_2"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_2"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_2"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_2"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_2"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_2"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202512_3" IS $DOC$用途: 数据表：public.mpps_w_202512_3（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202512_3 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202512_3
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_3"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_3"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_3"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_3"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_3"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_3"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202512_4" IS $DOC$用途: 数据表：public.mpps_w_202512_4（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202512_4 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202512_4
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_4"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_4"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_4"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_4"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_4"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_4"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202512_5" IS $DOC$用途: 数据表：public.mpps_w_202512_5（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202512_5 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202512_5
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_5"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_5"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_5"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_5"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_5"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_5"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202512_6" IS $DOC$用途: 数据表：public.mpps_w_202512_6（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202512_6 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202512_6
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_6"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_6"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_6"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_6"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_6"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_6"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202512_7" IS $DOC$用途: 数据表：public.mpps_w_202512_7（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202512_7 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202512_7
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_7"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_7"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_7"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_7"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_7"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_7"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202512_8" IS $DOC$用途: 数据表：public.mpps_w_202512_8（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202512_8 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202512_8
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_8"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_8"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_8"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_8"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_8"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_8"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202512_9" IS $DOC$用途: 数据表：public.mpps_w_202512_9（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202512_9 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202512_9
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_9"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_9"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_9"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_9"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_9"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202512_9"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202513" IS $DOC$用途: 数据表：public.mpps_w_202513（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202513 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202513
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202513_0" IS $DOC$用途: 数据表：public.mpps_w_202513_0（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202513_0 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202513_0
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_0"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_0"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_0"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_0"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_0"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_0"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202513_1" IS $DOC$用途: 数据表：public.mpps_w_202513_1（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202513_1 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202513_1
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_1"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_1"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_1"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_1"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_1"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_1"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202513_10" IS $DOC$用途: 数据表：public.mpps_w_202513_10（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202513_10 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202513_10
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_10"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_10"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_10"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_10"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_10"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_10"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202513_11" IS $DOC$用途: 数据表：public.mpps_w_202513_11（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202513_11 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202513_11
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_11"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_11"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_11"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_11"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_11"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_11"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202513_12" IS $DOC$用途: 数据表：public.mpps_w_202513_12（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202513_12 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202513_12
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_12"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_12"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_12"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_12"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_12"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_12"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202513_13" IS $DOC$用途: 数据表：public.mpps_w_202513_13（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202513_13 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202513_13
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_13"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_13"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_13"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_13"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_13"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_13"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202513_14" IS $DOC$用途: 数据表：public.mpps_w_202513_14（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202513_14 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202513_14
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_14"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_14"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_14"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_14"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_14"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_14"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202513_15" IS $DOC$用途: 数据表：public.mpps_w_202513_15（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202513_15 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202513_15
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_15"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_15"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_15"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_15"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_15"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_15"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202513_2" IS $DOC$用途: 数据表：public.mpps_w_202513_2（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202513_2 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202513_2
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_2"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_2"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_2"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_2"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_2"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_2"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202513_3" IS $DOC$用途: 数据表：public.mpps_w_202513_3（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202513_3 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202513_3
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_3"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_3"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_3"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_3"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_3"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_3"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202513_4" IS $DOC$用途: 数据表：public.mpps_w_202513_4（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202513_4 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202513_4
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_4"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_4"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_4"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_4"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_4"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_4"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202513_5" IS $DOC$用途: 数据表：public.mpps_w_202513_5（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202513_5 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202513_5
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_5"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_5"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_5"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_5"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_5"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_5"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202513_6" IS $DOC$用途: 数据表：public.mpps_w_202513_6（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202513_6 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202513_6
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_6"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_6"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_6"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_6"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_6"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_6"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202513_7" IS $DOC$用途: 数据表：public.mpps_w_202513_7（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202513_7 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202513_7
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_7"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_7"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_7"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_7"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_7"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_7"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202513_8" IS $DOC$用途: 数据表：public.mpps_w_202513_8（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202513_8 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202513_8
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_8"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_8"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_8"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_8"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_8"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_8"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202513_9" IS $DOC$用途: 数据表：public.mpps_w_202513_9（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202513_9 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202513_9
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_9"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_9"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_9"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_9"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_9"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202513_9"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202514" IS $DOC$用途: 数据表：public.mpps_w_202514（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202514 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202514
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202514_0" IS $DOC$用途: 数据表：public.mpps_w_202514_0（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202514_0 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202514_0
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_0"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_0"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_0"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_0"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_0"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_0"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202514_1" IS $DOC$用途: 数据表：public.mpps_w_202514_1（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202514_1 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202514_1
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_1"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_1"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_1"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_1"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_1"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_1"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202514_10" IS $DOC$用途: 数据表：public.mpps_w_202514_10（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202514_10 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202514_10
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_10"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_10"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_10"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_10"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_10"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_10"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202514_11" IS $DOC$用途: 数据表：public.mpps_w_202514_11（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202514_11 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202514_11
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_11"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_11"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_11"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_11"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_11"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_11"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202514_12" IS $DOC$用途: 数据表：public.mpps_w_202514_12（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202514_12 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202514_12
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_12"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_12"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_12"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_12"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_12"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_12"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202514_13" IS $DOC$用途: 数据表：public.mpps_w_202514_13（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202514_13 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202514_13
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_13"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_13"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_13"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_13"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_13"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_13"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202514_14" IS $DOC$用途: 数据表：public.mpps_w_202514_14（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202514_14 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202514_14
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_14"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_14"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_14"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_14"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_14"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_14"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202514_15" IS $DOC$用途: 数据表：public.mpps_w_202514_15（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202514_15 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202514_15
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_15"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_15"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_15"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_15"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_15"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_15"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202514_2" IS $DOC$用途: 数据表：public.mpps_w_202514_2（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202514_2 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202514_2
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_2"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_2"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_2"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_2"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_2"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_2"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202514_3" IS $DOC$用途: 数据表：public.mpps_w_202514_3（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202514_3 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202514_3
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_3"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_3"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_3"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_3"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_3"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_3"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202514_4" IS $DOC$用途: 数据表：public.mpps_w_202514_4（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202514_4 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202514_4
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_4"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_4"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_4"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_4"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_4"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_4"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202514_5" IS $DOC$用途: 数据表：public.mpps_w_202514_5（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202514_5 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202514_5
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_5"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_5"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_5"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_5"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_5"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_5"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202514_6" IS $DOC$用途: 数据表：public.mpps_w_202514_6（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202514_6 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202514_6
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_6"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_6"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_6"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_6"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_6"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_6"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202514_7" IS $DOC$用途: 数据表：public.mpps_w_202514_7（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202514_7 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202514_7
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_7"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_7"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_7"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_7"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_7"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_7"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202514_8" IS $DOC$用途: 数据表：public.mpps_w_202514_8（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202514_8 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202514_8
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_8"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_8"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_8"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_8"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_8"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_8"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202514_9" IS $DOC$用途: 数据表：public.mpps_w_202514_9（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202514_9 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202514_9
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_9"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_9"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_9"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_9"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_9"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202514_9"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202515" IS $DOC$用途: 数据表：public.mpps_w_202515（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202515 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202515
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202515_0" IS $DOC$用途: 数据表：public.mpps_w_202515_0（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202515_0 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202515_0
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_0"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_0"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_0"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_0"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_0"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_0"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202515_1" IS $DOC$用途: 数据表：public.mpps_w_202515_1（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202515_1 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202515_1
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_1"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_1"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_1"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_1"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_1"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_1"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202515_10" IS $DOC$用途: 数据表：public.mpps_w_202515_10（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202515_10 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202515_10
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_10"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_10"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_10"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_10"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_10"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_10"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202515_11" IS $DOC$用途: 数据表：public.mpps_w_202515_11（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202515_11 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202515_11
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_11"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_11"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_11"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_11"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_11"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_11"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202515_12" IS $DOC$用途: 数据表：public.mpps_w_202515_12（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202515_12 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202515_12
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_12"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_12"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_12"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_12"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_12"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_12"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202515_13" IS $DOC$用途: 数据表：public.mpps_w_202515_13（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202515_13 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202515_13
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_13"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_13"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_13"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_13"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_13"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_13"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202515_14" IS $DOC$用途: 数据表：public.mpps_w_202515_14（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202515_14 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202515_14
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_14"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_14"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_14"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_14"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_14"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_14"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202515_15" IS $DOC$用途: 数据表：public.mpps_w_202515_15（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202515_15 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202515_15
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_15"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_15"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_15"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_15"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_15"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_15"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202515_2" IS $DOC$用途: 数据表：public.mpps_w_202515_2（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202515_2 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202515_2
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_2"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_2"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_2"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_2"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_2"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_2"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202515_3" IS $DOC$用途: 数据表：public.mpps_w_202515_3（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202515_3 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202515_3
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_3"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_3"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_3"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_3"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_3"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_3"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202515_4" IS $DOC$用途: 数据表：public.mpps_w_202515_4（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202515_4 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202515_4
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_4"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_4"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_4"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_4"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_4"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_4"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202515_5" IS $DOC$用途: 数据表：public.mpps_w_202515_5（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202515_5 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202515_5
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_5"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_5"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_5"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_5"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_5"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_5"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202515_6" IS $DOC$用途: 数据表：public.mpps_w_202515_6（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202515_6 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202515_6
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_6"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_6"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_6"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_6"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_6"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_6"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202515_7" IS $DOC$用途: 数据表：public.mpps_w_202515_7（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202515_7 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202515_7
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_7"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_7"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_7"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_7"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_7"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_7"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202515_8" IS $DOC$用途: 数据表：public.mpps_w_202515_8（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202515_8 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202515_8
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_8"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_8"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_8"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_8"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_8"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_8"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202515_9" IS $DOC$用途: 数据表：public.mpps_w_202515_9（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202515_9 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202515_9
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_9"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_9"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_9"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_9"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_9"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202515_9"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202516" IS $DOC$用途: 数据表：public.mpps_w_202516（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202516 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202516
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202516_0" IS $DOC$用途: 数据表：public.mpps_w_202516_0（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202516_0 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202516_0
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_0"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_0"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_0"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_0"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_0"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_0"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202516_1" IS $DOC$用途: 数据表：public.mpps_w_202516_1（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202516_1 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202516_1
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_1"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_1"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_1"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_1"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_1"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_1"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202516_10" IS $DOC$用途: 数据表：public.mpps_w_202516_10（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202516_10 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202516_10
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_10"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_10"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_10"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_10"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_10"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_10"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202516_11" IS $DOC$用途: 数据表：public.mpps_w_202516_11（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202516_11 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202516_11
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_11"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_11"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_11"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_11"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_11"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_11"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202516_12" IS $DOC$用途: 数据表：public.mpps_w_202516_12（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202516_12 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202516_12
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_12"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_12"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_12"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_12"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_12"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_12"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202516_13" IS $DOC$用途: 数据表：public.mpps_w_202516_13（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202516_13 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202516_13
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_13"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_13"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_13"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_13"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_13"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_13"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202516_14" IS $DOC$用途: 数据表：public.mpps_w_202516_14（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202516_14 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202516_14
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_14"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_14"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_14"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_14"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_14"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_14"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202516_15" IS $DOC$用途: 数据表：public.mpps_w_202516_15（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202516_15 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202516_15
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_15"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_15"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_15"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_15"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_15"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_15"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202516_2" IS $DOC$用途: 数据表：public.mpps_w_202516_2（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202516_2 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202516_2
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_2"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_2"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_2"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_2"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_2"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_2"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202516_3" IS $DOC$用途: 数据表：public.mpps_w_202516_3（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202516_3 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202516_3
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_3"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_3"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_3"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_3"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_3"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_3"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202516_4" IS $DOC$用途: 数据表：public.mpps_w_202516_4（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202516_4 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202516_4
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_4"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_4"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_4"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_4"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_4"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_4"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202516_5" IS $DOC$用途: 数据表：public.mpps_w_202516_5（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202516_5 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202516_5
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_5"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_5"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_5"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_5"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_5"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_5"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202516_6" IS $DOC$用途: 数据表：public.mpps_w_202516_6（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202516_6 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202516_6
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_6"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_6"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_6"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_6"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_6"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_6"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202516_7" IS $DOC$用途: 数据表：public.mpps_w_202516_7（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202516_7 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202516_7
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_7"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_7"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_7"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_7"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_7"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_7"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202516_8" IS $DOC$用途: 数据表：public.mpps_w_202516_8（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202516_8 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202516_8
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_8"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_8"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_8"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_8"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_8"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_8"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202516_9" IS $DOC$用途: 数据表：public.mpps_w_202516_9（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202516_9 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202516_9
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_9"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_9"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_9"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_9"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_9"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202516_9"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202537" IS $DOC$用途: 数据表：public.mpps_w_202537（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202537 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202537
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202537_0" IS $DOC$用途: 数据表：public.mpps_w_202537_0（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202537_0 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202537_0
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_0"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_0"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_0"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_0"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_0"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_0"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202537_1" IS $DOC$用途: 数据表：public.mpps_w_202537_1（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202537_1 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202537_1
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_1"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_1"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_1"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_1"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_1"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_1"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202537_10" IS $DOC$用途: 数据表：public.mpps_w_202537_10（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202537_10 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202537_10
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_10"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_10"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_10"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_10"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_10"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_10"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202537_11" IS $DOC$用途: 数据表：public.mpps_w_202537_11（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202537_11 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202537_11
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_11"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_11"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_11"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_11"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_11"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_11"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202537_12" IS $DOC$用途: 数据表：public.mpps_w_202537_12（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202537_12 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202537_12
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_12"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_12"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_12"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_12"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_12"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_12"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202537_13" IS $DOC$用途: 数据表：public.mpps_w_202537_13（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202537_13 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202537_13
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_13"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_13"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_13"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_13"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_13"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_13"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202537_14" IS $DOC$用途: 数据表：public.mpps_w_202537_14（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202537_14 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202537_14
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_14"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_14"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_14"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_14"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_14"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_14"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202537_15" IS $DOC$用途: 数据表：public.mpps_w_202537_15（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202537_15 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202537_15
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_15"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_15"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_15"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_15"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_15"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_15"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202537_2" IS $DOC$用途: 数据表：public.mpps_w_202537_2（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202537_2 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202537_2
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_2"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_2"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_2"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_2"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_2"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_2"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202537_3" IS $DOC$用途: 数据表：public.mpps_w_202537_3（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202537_3 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202537_3
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_3"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_3"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_3"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_3"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_3"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_3"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202537_4" IS $DOC$用途: 数据表：public.mpps_w_202537_4（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202537_4 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202537_4
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_4"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_4"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_4"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_4"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_4"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_4"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202537_5" IS $DOC$用途: 数据表：public.mpps_w_202537_5（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202537_5 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202537_5
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_5"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_5"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_5"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_5"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_5"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_5"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202537_6" IS $DOC$用途: 数据表：public.mpps_w_202537_6（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202537_6 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202537_6
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_6"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_6"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_6"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_6"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_6"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_6"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202537_7" IS $DOC$用途: 数据表：public.mpps_w_202537_7（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202537_7 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202537_7
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_7"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_7"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_7"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_7"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_7"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_7"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202537_8" IS $DOC$用途: 数据表：public.mpps_w_202537_8（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202537_8 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202537_8
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_8"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_8"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_8"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_8"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_8"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_8"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."mpps_w_202537_9" IS $DOC$用途: 数据表：public.mpps_w_202537_9（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.mpps_w_202537_9 LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.mpps_w_202537_9
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_9"."station_id" IS $DOC$泵站ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_9"."device_id" IS $DOC$设备ID（外键）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_9"."ts_second" IS $DOC$字段：ts_second（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_9"."available_metrics" IS $DOC$字段：available_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_9"."need_compute_metrics" IS $DOC$字段：need_compute_metrics（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."mpps_w_202537_9"."created_at" IS $DOC$字段：created_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."staging_raw" IS $DOC$用途: 导入暂存原始数据（未清洗/未对齐）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.staging_raw LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."staging_raw"."station_name" IS $DOC$泵站名称$DOC$;

COMMENT ON COLUMN "public"."staging_raw"."device_name" IS $DOC$设备名称$DOC$;

COMMENT ON COLUMN "public"."staging_raw"."metric_key" IS $DOC$指标键（唯一键）$DOC$;

COMMENT ON COLUMN "public"."staging_raw"."TagName" IS $DOC$字段：TagName（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."staging_raw"."DataTime" IS $DOC$字段：DataTime（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."staging_raw"."DataValue" IS $DOC$字段：DataValue（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."staging_raw"."source_hint" IS $DOC$来源提示/数据来源$DOC$;

COMMENT ON COLUMN "public"."staging_raw"."loaded_at" IS $DOC$字段：loaded_at（说明待补充）$DOC$;

COMMENT ON TABLE "public"."staging_rejects" IS $DOC$用途: 导入拒收记录（格式/校验失败）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.staging_rejects LIMIT 100;$DOC$;

COMMENT ON COLUMN "public"."staging_rejects"."station_name" IS $DOC$泵站名称$DOC$;

COMMENT ON COLUMN "public"."staging_rejects"."device_name" IS $DOC$设备名称$DOC$;

COMMENT ON COLUMN "public"."staging_rejects"."metric_key" IS $DOC$指标键（唯一键）$DOC$;

COMMENT ON COLUMN "public"."staging_rejects"."TagName" IS $DOC$字段：TagName（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."staging_rejects"."DataTime" IS $DOC$字段：DataTime（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."staging_rejects"."DataValue" IS $DOC$字段：DataValue（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."staging_rejects"."source_hint" IS $DOC$来源提示/数据来源$DOC$;

COMMENT ON COLUMN "public"."staging_rejects"."error_msg" IS $DOC$字段：error_msg（说明待补充）$DOC$;

COMMENT ON COLUMN "public"."staging_rejects"."rejected_at" IS $DOC$字段：rejected_at（说明待补充）$DOC$;

COMMENT ON VIEW "public"."cagg_presence_per_second" IS $DOC$用途: 视图：用于聚合/便捷查询
使用方法: 直接查询
-- 示例：查看视图内容
SELECT * FROM public.cagg_presence_per_second LIMIT 100;$DOC$;

COMMENT ON VIEW "public"."pg_stat_statements" IS $DOC$用途: 视图：用于聚合/便捷查询
使用方法: 直接查询
-- 示例：查看视图内容
SELECT * FROM public.pg_stat_statements LIMIT 100;$DOC$;

COMMENT ON VIEW "public"."pg_stat_statements_info" IS $DOC$用途: 视图：用于聚合/便捷查询
使用方法: 直接查询
-- 示例：查看视图内容
SELECT * FROM public.pg_stat_statements_info LIMIT 100;$DOC$;

COMMENT ON VIEW "public"."station_device_rated_params_view" IS $DOC$用途: 站点-设备额定参数整合视图
使用方法: 直接查询
-- 示例：查看视图内容
SELECT * FROM public.station_device_rated_params_view LIMIT 100;$DOC$;

COMMENT ON VIEW "public"."v_coverage_gaps_1s" IS $DOC$用途: 覆盖/缺口概览（1s 粒度透视）
使用方法: 直接查询
-- 示例：查看视图内容
SELECT * FROM public.v_coverage_gaps_1s LIMIT 100;$DOC$;

COMMENT ON VIEW "public"."v_startstop_windows" IS $DOC$用途: 启停窗口快照视图（模板）
使用方法: 直接查询
-- 示例：查看视图内容
SELECT * FROM public.v_startstop_windows LIMIT 100;$DOC$;

COMMENT ON FUNCTION "public"."add_compression_policy"(hypertable regclass, compress_after "any", if_not_exists boolean, schedule_interval interval, initial_start timestamp with time zone, timezone text, compress_created_before interval) IS $DOC$用途: 函数：请补充业务用途
参数: hypertable regclass, compress_after "any", if_not_exists boolean, schedule_interval interval, initial_start timestamp with time zone, timezone text, compress_created_before interval
返回: integer
-- 示例：函数调用
SELECT * FROM public.add_compression_policy(:p1, :p2, :p3, :p4, :p5, :p6, :p7);$DOC$;

COMMENT ON FUNCTION "public"."add_continuous_aggregate_policy"(continuous_aggregate regclass, start_offset "any", end_offset "any", schedule_interval interval, if_not_exists boolean, initial_start timestamp with time zone, timezone text, include_tiered_data boolean, buckets_per_batch integer, max_batches_per_execution integer, refresh_newest_first boolean) IS $DOC$用途: 函数：请补充业务用途
参数: continuous_aggregate regclass, start_offset "any", end_offset "any", schedule_interval interval, if_not_exists boolean, initial_start timestamp with time zone, timezone text, include_tiered_data boolean, buckets_per_batch integer, max_batches_per_execution integer, refresh_newest_first boolean
返回: integer
-- 示例：函数调用
SELECT * FROM public.add_continuous_aggregate_policy(:p1, :p2, :p3, :p4, :p5, :p6, :p7, :p8, :p9, :p10, :p11);$DOC$;

COMMENT ON FUNCTION "public"."add_dimension"(hypertable regclass, column_name name, number_partitions integer, chunk_time_interval anyelement, partitioning_func regproc, if_not_exists boolean) IS $DOC$用途: 函数：请补充业务用途
参数: hypertable regclass, column_name name, number_partitions integer, chunk_time_interval anyelement, partitioning_func regproc, if_not_exists boolean
返回: TABLE(dimension_id integer, schema_name name, table_name name, column_name name, created boolean)
-- 示例：函数调用
SELECT * FROM public.add_dimension(:p1, :p2, :p3, :p4, :p5, :p6);$DOC$;

COMMENT ON FUNCTION "public"."add_job"(proc regproc, schedule_interval interval, config jsonb, initial_start timestamp with time zone, scheduled boolean, check_config regproc, fixed_schedule boolean, timezone text, job_name text) IS $DOC$用途: 函数：请补充业务用途
参数: proc regproc, schedule_interval interval, config jsonb, initial_start timestamp with time zone, scheduled boolean, check_config regproc, fixed_schedule boolean, timezone text, job_name text
返回: integer
-- 示例：函数调用
SELECT * FROM public.add_job(:p1, :p2, :p3, :p4, :p5, :p6, :p7, :p8, :p9);$DOC$;

COMMENT ON FUNCTION "public"."add_reorder_policy"(hypertable regclass, index_name name, if_not_exists boolean, initial_start timestamp with time zone, timezone text) IS $DOC$用途: 函数：请补充业务用途
参数: hypertable regclass, index_name name, if_not_exists boolean, initial_start timestamp with time zone, timezone text
返回: integer
-- 示例：函数调用
SELECT * FROM public.add_reorder_policy(:p1, :p2, :p3, :p4, :p5);$DOC$;

COMMENT ON FUNCTION "public"."add_retention_policy"(relation regclass, drop_after "any", if_not_exists boolean, schedule_interval interval, initial_start timestamp with time zone, timezone text, drop_created_before interval) IS $DOC$用途: 函数：请补充业务用途
参数: relation regclass, drop_after "any", if_not_exists boolean, schedule_interval interval, initial_start timestamp with time zone, timezone text, drop_created_before interval
返回: integer
-- 示例：函数调用
SELECT * FROM public.add_retention_policy(:p1, :p2, :p3, :p4, :p5, :p6, :p7);$DOC$;

COMMENT ON FUNCTION "public"."alter_job"(job_id integer, schedule_interval interval, max_runtime interval, max_retries integer, retry_period interval, scheduled boolean, config jsonb, next_start timestamp with time zone, if_exists boolean, check_config regproc, fixed_schedule boolean, initial_start timestamp with time zone, timezone text, job_name text) IS $DOC$用途: 函数：请补充业务用途
参数: job_id integer, schedule_interval interval, max_runtime interval, max_retries integer, retry_period interval, scheduled boolean, config jsonb, next_start timestamp with time zone, if_exists boolean, check_config regproc, fixed_schedule boolean, initial_start timestamp with time zone, timezone text, job_name text
返回: TABLE(job_id integer, schedule_interval interval, max_runtime interval, max_retries integer, retry_period interval, scheduled boolean, config jsonb, next_start timestamp with time zone, check_config text, fixed_schedule boolean, initial_start timestamp with time zone, timezone text, application_name name)
-- 示例：函数调用
SELECT * FROM public.alter_job(:p1, :p2, :p3, :p4, :p5, :p6, :p7, :p8, :p9, :p10, :p11, :p12, :p13, :p14);$DOC$;

COMMENT ON FUNCTION "public"."approximate_row_count"(relation regclass) IS $DOC$用途: 函数：请补充业务用途
参数: relation regclass
返回: bigint
-- 示例：函数调用
SELECT * FROM public.approximate_row_count(:p1);$DOC$;

COMMENT ON FUNCTION "public"."attach_tablespace"(tablespace name, hypertable regclass, if_not_attached boolean) IS $DOC$用途: 函数：请补充业务用途
参数: tablespace name, hypertable regclass, if_not_attached boolean
返回: void
-- 示例：函数调用
SELECT * FROM public.attach_tablespace(:p1, :p2, :p3);$DOC$;

COMMENT ON FUNCTION "public"."auto_performance_tuning"() IS $DOC$用途: 自动性能调优（示意）
参数: 
返回: text
-- 示例：函数调用
SELECT * FROM public.auto_performance_tuning();$DOC$;

COMMENT ON FUNCTION "public"."auto_space_reclaim"() IS $DOC$用途: 空间回收（示意）
参数: 
返回: text
-- 示例：函数调用
SELECT * FROM public.auto_space_reclaim();$DOC$;

COMMENT ON FUNCTION "public"."batch_delete_old_data"(p_cutoff_date timestamp with time zone, p_batch_size integer) IS $DOC$用途: 分批删除历史数据（示意）
参数: p_cutoff_date timestamp with time zone, p_batch_size integer
返回: text
-- 示例：函数调用
SELECT * FROM public.batch_delete_old_data(:p1, :p2);$DOC$;

COMMENT ON FUNCTION "public"."by_hash"(column_name name, number_partitions integer, partition_func regproc) IS $DOC$用途: 函数：请补充业务用途
参数: column_name name, number_partitions integer, partition_func regproc
返回: _timescaledb_internal.dimension_info
-- 示例：函数调用
SELECT * FROM public.by_hash(:p1, :p2, :p3);$DOC$;

COMMENT ON FUNCTION "public"."by_range"(column_name name, partition_interval anyelement, partition_func regproc) IS $DOC$用途: 函数：请补充业务用途
参数: column_name name, partition_interval anyelement, partition_func regproc
返回: _timescaledb_internal.dimension_info
-- 示例：函数调用
SELECT * FROM public.by_range(:p1, :p2, :p3);$DOC$;

COMMENT ON FUNCTION "public"."check_data_consistency"() IS $DOC$用途: 数据一致性检查函数：检查数据库中的数据一致性问题，返回发现的问题类型和详细信息。
    
    功能说明：
    - 检查维度表和事实表之间的外键约束
    - 检查时间戳字段的有效性
    - 检查数值字段的合理范围
    - 检查重复记录
    
    返回值：
    - TABLE(issue_type text, details text): 问题类型和详细信息的表
    
    使用示例：
    SELECT * FROM check_data_consistency();
    
    返回字段说明：
    - issue_type: 问题类型，如"外键约束违反"、"时间戳异常"等
    - details: 问题的详细描述，包括涉及的表、记录等信息
    
    注意事项：
    - 该函数只进行检查，不会修改数据
    - 建议定期执行此函数以确保数据质量
参数: 
返回: TABLE(issue_type text, details text)
-- 示例：函数调用
SELECT * FROM public.check_data_consistency();$DOC$;

COMMENT ON FUNCTION "public"."check_performance_alerts"() IS $DOC$用途: 性能告警检查函数：检查数据库性能指标，返回性能告警信息。
    
    功能说明：
    - 检查慢查询日志
    - 检查连接数是否接近上限
    - 检查锁等待情况
    - 检查磁盘空间使用率
    
    返回值：
    - text: 性能告警信息
    
    使用示例：
    SELECT check_performance_alerts();
    
    注意事项：
    - 该函数基于pg_stat_statements扩展，请确保已启用
    - 建议设置定期任务执行此函数
参数: 
返回: text
-- 示例：函数调用
SELECT * FROM public.check_performance_alerts();$DOC$;

COMMENT ON FUNCTION "public"."chunk_columnstore_stats"(hypertable regclass) IS $DOC$用途: 函数：请补充业务用途
参数: hypertable regclass
返回: TABLE(chunk_schema name, chunk_name name, compression_status text, before_compression_table_bytes bigint, before_compression_index_bytes bigint, before_compression_toast_bytes bigint, before_compression_total_bytes bigint, after_compression_table_bytes bigint, after_compression_index_bytes bigint, after_compression_toast_bytes bigint, after_compression_total_bytes bigint, node_name name)
-- 示例：函数调用
SELECT * FROM public.chunk_columnstore_stats(:p1);$DOC$;

COMMENT ON FUNCTION "public"."chunk_compression_stats"(hypertable regclass) IS $DOC$用途: 函数：请补充业务用途
参数: hypertable regclass
返回: TABLE(chunk_schema name, chunk_name name, compression_status text, before_compression_table_bytes bigint, before_compression_index_bytes bigint, before_compression_toast_bytes bigint, before_compression_total_bytes bigint, after_compression_table_bytes bigint, after_compression_index_bytes bigint, after_compression_toast_bytes bigint, after_compression_total_bytes bigint, node_name name)
-- 示例：函数调用
SELECT * FROM public.chunk_compression_stats(:p1);$DOC$;

COMMENT ON FUNCTION "public"."chunks_detailed_size"(hypertable regclass) IS $DOC$用途: 函数：请补充业务用途
参数: hypertable regclass
返回: TABLE(chunk_schema name, chunk_name name, table_bytes bigint, index_bytes bigint, toast_bytes bigint, total_bytes bigint, node_name name)
-- 示例：函数调用
SELECT * FROM public.chunks_detailed_size(:p1);$DOC$;

COMMENT ON FUNCTION "public"."compress_chunk"(uncompressed_chunk regclass, if_not_compressed boolean, recompress boolean) IS $DOC$用途: 函数：请补充业务用途
参数: uncompressed_chunk regclass, if_not_compressed boolean, recompress boolean
返回: regclass
-- 示例：函数调用
SELECT * FROM public.compress_chunk(:p1, :p2, :p3);$DOC$;

COMMENT ON FUNCTION "public"."create_hypertable"(relation regclass, time_column_name name, partitioning_column name, number_partitions integer, associated_schema_name name, associated_table_prefix name, chunk_time_interval anyelement, create_default_indexes boolean, if_not_exists boolean, partitioning_func regproc, migrate_data boolean, chunk_target_size text, chunk_sizing_func regproc, time_partitioning_func regproc) IS $DOC$用途: 函数：请补充业务用途
参数: relation regclass, time_column_name name, partitioning_column name, number_partitions integer, associated_schema_name name, associated_table_prefix name, chunk_time_interval anyelement, create_default_indexes boolean, if_not_exists boolean, partitioning_func regproc, migrate_data boolean, chunk_target_size text, chunk_sizing_func regproc, time_partitioning_func regproc
返回: TABLE(hypertable_id integer, schema_name name, table_name name, created boolean)
-- 示例：函数调用
SELECT * FROM public.create_hypertable(:p1, :p2, :p3, :p4, :p5, :p6, :p7, :p8, :p9, :p10, :p11, :p12, :p13, :p14);$DOC$;

COMMENT ON FUNCTION "public"."database_health_check"() IS $DOC$用途: 数据库健康体检（只读）
参数: 
返回: TABLE(check_category text, check_name text, status text, details text)
-- 示例：函数调用
SELECT * FROM public.database_health_check();$DOC$;

COMMENT ON FUNCTION "public"."decompress_chunk"(uncompressed_chunk regclass, if_compressed boolean) IS $DOC$用途: 函数：请补充业务用途
参数: uncompressed_chunk regclass, if_compressed boolean
返回: regclass
-- 示例：函数调用
SELECT * FROM public.decompress_chunk(:p1, :p2);$DOC$;

COMMENT ON FUNCTION "public"."delete_job"(job_id integer) IS $DOC$用途: 函数：请补充业务用途
参数: job_id integer
返回: void
-- 示例：函数调用
SELECT * FROM public.delete_job(:p1);$DOC$;

COMMENT ON FUNCTION "public"."detach_tablespace"(tablespace name, hypertable regclass, if_attached boolean) IS $DOC$用途: 函数：请补充业务用途
参数: tablespace name, hypertable regclass, if_attached boolean
返回: integer
-- 示例：函数调用
SELECT * FROM public.detach_tablespace(:p1, :p2, :p3);$DOC$;

COMMENT ON FUNCTION "public"."detach_tablespaces"(hypertable regclass) IS $DOC$用途: 函数：请补充业务用途
参数: hypertable regclass
返回: integer
-- 示例：函数调用
SELECT * FROM public.detach_tablespaces(:p1);$DOC$;

COMMENT ON FUNCTION "public"."disable_chunk_skipping"(hypertable regclass, column_name name, if_not_exists boolean) IS $DOC$用途: 函数：请补充业务用途
参数: hypertable regclass, column_name name, if_not_exists boolean
返回: TABLE(hypertable_id integer, column_name name, disabled boolean)
-- 示例：函数调用
SELECT * FROM public.disable_chunk_skipping(:p1, :p2, :p3);$DOC$;

COMMENT ON FUNCTION "public"."drop_chunks"(relation regclass, older_than "any", newer_than "any", "verbose" boolean, created_before "any", created_after "any") IS $DOC$用途: 函数：请补充业务用途
参数: relation regclass, older_than "any", newer_than "any", "verbose" boolean, created_before "any", created_after "any"
返回: SETOF text
-- 示例：函数调用
SELECT * FROM public.drop_chunks(:p1, :p2, :p3, :p4, :p5, :p6);$DOC$;

COMMENT ON FUNCTION "public"."enable_chunk_skipping"(hypertable regclass, column_name name, if_not_exists boolean) IS $DOC$用途: 函数：请补充业务用途
参数: hypertable regclass, column_name name, if_not_exists boolean
返回: TABLE(column_stats_id integer, enabled boolean)
-- 示例：函数调用
SELECT * FROM public.enable_chunk_skipping(:p1, :p2, :p3);$DOC$;

COMMENT ON FUNCTION "public"."ensure_mpps_partitions"(p_ts timestamp with time zone) IS $DOC$用途: 函数：请补充业务用途
参数: p_ts timestamp with time zone
返回: void
-- 示例：函数调用
SELECT * FROM public.ensure_mpps_partitions(:p1);$DOC$;

COMMENT ON FUNCTION "public"."ensure_mpps_partitions_range"(p_start timestamp with time zone, p_end timestamp with time zone) IS $DOC$用途: 函数：请补充业务用途
参数: p_start timestamp with time zone, p_end timestamp with time zone
返回: void
-- 示例：函数调用
SELECT * FROM public.ensure_mpps_partitions_range(:p1, :p2);$DOC$;

COMMENT ON FUNCTION "public"."ensure_week_partition"(p_week_start date, p_modulus integer, p_schema text) IS $DOC$用途: 确保周分区与 HASH 子分区存在
参数: p_week_start date, p_modulus integer, p_schema text
返回: void
-- 示例：函数调用
SELECT * FROM public.ensure_week_partition(:p1, :p2, :p3);$DOC$;

COMMENT ON FUNCTION "public"."fn_detect_gaps_1s"(p_station_id bigint, p_device_id bigint, p_metric_id bigint, p_start_ts timestamp with time zone, p_end_ts timestamp with time zone, p_max_gap_sec integer) IS $DOC$用途: 缺口段识别（基于秒级对齐）
参数: p_station_id bigint, p_device_id bigint, p_metric_id bigint, p_start_ts timestamp with time zone, p_end_ts timestamp with time zone, p_max_gap_sec integer
返回: TABLE(gap_id bigint, gap_start_ts timestamp with time zone, gap_end_ts timestamp with time zone, gap_len_sec integer, gap_class text)
-- 示例：函数调用
SELECT * FROM public.fn_detect_gaps_1s(:p1, :p2, :p3, :p4, :p5, :p6);$DOC$;

COMMENT ON FUNCTION "public"."fn_quality_stats_1d"(p_station_id bigint, p_device_id bigint, p_metric_id bigint, p_start_ts timestamp with time zone, p_end_ts timestamp with time zone) IS $DOC$用途: 按日质量统计（只读）
参数: p_station_id bigint, p_device_id bigint, p_metric_id bigint, p_start_ts timestamp with time zone, p_end_ts timestamp with time zone
返回: TABLE(date_bucket date, total_points bigint, null_count bigint, coverage_rate double precision, outlier_count bigint)
-- 示例：函数调用
SELECT * FROM public.fn_quality_stats_1d(:p1, :p2, :p3, :p4, :p5);$DOC$;

COMMENT ON FUNCTION "public"."fn_running_state_1s"(p_station_id bigint, p_device_id bigint, p_start_ts timestamp with time zone, p_end_ts timestamp with time zone) IS $DOC$用途: 逐秒运行判定：按 device_running_thresholds 阈值，on/off 滞回 + 缺报延续
参数: p_station_id bigint, p_device_id bigint, p_start_ts timestamp with time zone, p_end_ts timestamp with time zone
返回: TABLE(ts_bucket timestamp with time zone, is_running boolean, max_i double precision, p double precision, f double precision, source text)
-- 示例：函数调用
SELECT * FROM public.fn_running_state_1s(:p1, :p2, :p3, :p4);$DOC$;

COMMENT ON FUNCTION "public"."fn_startstop_windows"(p_device_id bigint, p_start_ts timestamp with time zone, p_end_ts timestamp with time zone) IS $DOC$用途: 仅 device_id + 时间窗 → 返回逐秒状态（1s 粒度），内部委托 fn_running_state_1s
参数: p_device_id bigint, p_start_ts timestamp with time zone, p_end_ts timestamp with time zone
返回: TABLE(ts_bucket timestamp with time zone, is_running boolean, max_i double precision, p double precision, f double precision, source text)
-- 示例：函数调用
SELECT * FROM public.fn_startstop_windows(:p1, :p2, :p3);$DOC$;

COMMENT ON FUNCTION "public"."fn_training_timeseries_1s"(p_station_id bigint, p_device_id bigint, p_metric_id bigint, p_start_ts timestamp with time zone, p_end_ts timestamp with time zone) IS $DOC$用途: 统一 1s 训练口径（长表返回）
参数: p_station_id bigint, p_device_id bigint, p_metric_id bigint, p_start_ts timestamp with time zone, p_end_ts timestamp with time zone
返回: TABLE(ts_bucket timestamp with time zone, value double precision, station_id bigint, device_id bigint, metric_id bigint)
-- 示例：函数调用
SELECT * FROM public.fn_training_timeseries_1s(:p1, :p2, :p3, :p4, :p5);$DOC$;

COMMENT ON FUNCTION "public"."generate_uuidv7"() IS $DOC$用途: 函数：请补充业务用途
参数: 
返回: uuid
-- 示例：函数调用
SELECT * FROM public.generate_uuidv7();$DOC$;

COMMENT ON FUNCTION "public"."get_device_metrics_by_time_range"(p_device_id bigint, p_start_time timestamp with time zone, p_end_time timestamp with time zone, p_limit integer) IS $DOC$用途: 设备指标时间窗查询（JSON 聚合）
参数: p_device_id bigint, p_start_time timestamp with time zone, p_end_time timestamp with time zone, p_limit integer
返回: TABLE(record_timestamp timestamp with time zone, metrics_data jsonb, total_records bigint)
-- 示例：函数调用
SELECT * FROM public.get_device_metrics_by_time_range(:p1, :p2, :p3, :p4);$DOC$;

COMMENT ON FUNCTION "public"."get_full_horizontal_data"(p_limit integer) IS $DOC$用途: 获取完整水平数据函数：返回完整的水平数据透视结果，包含所有设备和指标。
    
    参数说明：
    - p_limit: 返回记录数限制，默认为10
    
    功能说明：
    - 查询所有泵站、设备和指标的完整数据
    - 将数据透视为水平格式，每个时间戳一行
    - 包含所有设备的所有指标数据
    
    返回值：
    - TABLE(result_timestamp timestamptz, result_station_id bigint, result_station_name text, result_data jsonb)
    
    使用示例：
    SELECT * FROM get_full_horizontal_data(100);
    
    注意事项：
    - 该函数可能返回大量数据，请谨慎使用limit参数
参数: p_limit integer
返回: TABLE(result_timestamp timestamp with time zone, result_station_id bigint, result_station_name text, result_data jsonb)
-- 示例：函数调用
SELECT * FROM public.get_full_horizontal_data(:p1);$DOC$;

COMMENT ON FUNCTION "public"."get_performance_metrics"() IS $DOC$用途: 性能指标视图（示意）
参数: 
返回: TABLE(metric_name text, current_value numeric, threshold_value numeric, status text)
-- 示例：函数调用
SELECT * FROM public.get_performance_metrics();$DOC$;

COMMENT ON FUNCTION "public"."get_station_devices_metrics_by_time_range"(p_station_id bigint, p_start_time timestamp with time zone, p_end_time timestamp with time zone, p_limit integer) IS $DOC$用途: 按站点查询设备指标（JSON 聚合）
参数: p_station_id bigint, p_start_time timestamp with time zone, p_end_time timestamp with time zone, p_limit integer
返回: TABLE(record_timestamp timestamp with time zone, metrics_data jsonb, total_records bigint)
-- 示例：函数调用
SELECT * FROM public.get_station_devices_metrics_by_time_range(:p1, :p2, :p3, :p4);$DOC$;

COMMENT ON FUNCTION "public"."get_telemetry_report"() IS $DOC$用途: 函数：请补充业务用途
参数: 
返回: jsonb
-- 示例：函数调用
SELECT * FROM public.get_telemetry_report();$DOC$;

COMMENT ON FUNCTION "public"."hypertable_approximate_detailed_size"(relation regclass) IS $DOC$用途: 函数：请补充业务用途
参数: relation regclass
返回: TABLE(table_bytes bigint, index_bytes bigint, toast_bytes bigint, total_bytes bigint)
-- 示例：函数调用
SELECT * FROM public.hypertable_approximate_detailed_size(:p1);$DOC$;

COMMENT ON FUNCTION "public"."hypertable_approximate_size"(hypertable regclass) IS $DOC$用途: 函数：请补充业务用途
参数: hypertable regclass
返回: bigint
-- 示例：函数调用
SELECT * FROM public.hypertable_approximate_size(:p1);$DOC$;

COMMENT ON FUNCTION "public"."hypertable_columnstore_stats"(hypertable regclass) IS $DOC$用途: 函数：请补充业务用途
参数: hypertable regclass
返回: TABLE(total_chunks bigint, number_compressed_chunks bigint, before_compression_table_bytes bigint, before_compression_index_bytes bigint, before_compression_toast_bytes bigint, before_compression_total_bytes bigint, after_compression_table_bytes bigint, after_compression_index_bytes bigint, after_compression_toast_bytes bigint, after_compression_total_bytes bigint, node_name name)
-- 示例：函数调用
SELECT * FROM public.hypertable_columnstore_stats(:p1);$DOC$;

COMMENT ON FUNCTION "public"."hypertable_compression_stats"(hypertable regclass) IS $DOC$用途: 函数：请补充业务用途
参数: hypertable regclass
返回: TABLE(total_chunks bigint, number_compressed_chunks bigint, before_compression_table_bytes bigint, before_compression_index_bytes bigint, before_compression_toast_bytes bigint, before_compression_total_bytes bigint, after_compression_table_bytes bigint, after_compression_index_bytes bigint, after_compression_toast_bytes bigint, after_compression_total_bytes bigint, node_name name)
-- 示例：函数调用
SELECT * FROM public.hypertable_compression_stats(:p1);$DOC$;

COMMENT ON FUNCTION "public"."hypertable_detailed_size"(hypertable regclass) IS $DOC$用途: 函数：请补充业务用途
参数: hypertable regclass
返回: TABLE(table_bytes bigint, index_bytes bigint, toast_bytes bigint, total_bytes bigint, node_name name)
-- 示例：函数调用
SELECT * FROM public.hypertable_detailed_size(:p1);$DOC$;

COMMENT ON FUNCTION "public"."hypertable_index_size"(index_name regclass) IS $DOC$用途: 函数：请补充业务用途
参数: index_name regclass
返回: bigint
-- 示例：函数调用
SELECT * FROM public.hypertable_index_size(:p1);$DOC$;

COMMENT ON FUNCTION "public"."hypertable_size"(hypertable regclass) IS $DOC$用途: 函数：请补充业务用途
参数: hypertable regclass
返回: bigint
-- 示例：函数调用
SELECT * FROM public.hypertable_size(:p1);$DOC$;

COMMENT ON FUNCTION "public"."interpolate"(value real, prev record, next record) IS $DOC$用途: 函数：请补充业务用途
参数: value real, prev record, next record
返回: real
-- 示例：函数调用
SELECT * FROM public.interpolate(:p1, :p2, :p3);$DOC$;

COMMENT ON FUNCTION "public"."locf"(value anyelement, prev anyelement, treat_null_as_missing boolean) IS $DOC$用途: 函数：请补充业务用途
参数: value anyelement, prev anyelement, treat_null_as_missing boolean
返回: anyelement
-- 示例：函数调用
SELECT * FROM public.locf(:p1, :p2, :p3);$DOC$;

COMMENT ON FUNCTION "public"."metrics_availability_window"(_start timestamp with time zone, _end timestamp with time zone) IS $DOC$用途: 按任意开始/结束时间窗口计算设备×指标的覆盖率与分类（阈值0.99；结合策略表返回 status 与 method_hint）。\n使用示例：\nSELECT * FROM public.metrics_availability_window('2025-02-27 00:00:00+00','2025-02-28 00:00:00+00')\nORDER BY station_id, device_id, metric_id LIMIT 100;
参数: _start timestamp with time zone, _end timestamp with time zone
返回: TABLE(station_id integer, device_id integer, metric_id integer, metric_key text, start_ts timestamp with time zone, end_ts timestamp with time zone, present_secs bigint, total_secs bigint, coverage_rate double precision, acquisition_status text, compute_flag text, status text, method_hint text)
-- 示例：函数调用
SELECT * FROM public.metrics_availability_window(:p1, :p2);$DOC$;

COMMENT ON FUNCTION "public"."metrics_presence_per_second"(_start timestamp with time zone, _end timestamp with time zone, _station_name text, _device_name text) IS $DOC$用途: 按秒输出：泵站×设备×时间点 的 {需要计算补齐的指标} 与 {已有指标}；不再依赖 dim_mapping_items，基于 metric_capability_policy（compute_flag=需要）与设备家族决定候选集合；时间为北京时间(+08)文本。
参数: _start timestamp with time zone, _end timestamp with time zone, _station_name text, _device_name text
返回: TABLE(station text, device text, ts_utc timestamp with time zone, ts_local text, need_compute_metrics text[], available_metrics text[])
-- 示例：函数调用
SELECT * FROM public.metrics_presence_per_second(:p1, :p2, :p3, :p4);$DOC$;

COMMENT ON FUNCTION "public"."metrics_presence_per_second_original"(_start timestamp with time zone, _end timestamp with time zone, _station_name text, _device_name text) IS $DOC$用途: 函数：请补充业务用途
参数: _start timestamp with time zone, _end timestamp with time zone, _station_name text, _device_name text
返回: TABLE(station text, device text, ts_utc timestamp with time zone, ts_local text, need_compute_metrics text[], available_metrics text[])
-- 示例：函数调用
SELECT * FROM public.metrics_presence_per_second_original(:p1, :p2, :p3, :p4);$DOC$;

COMMENT ON FUNCTION "public"."move_chunk"(chunk regclass, destination_tablespace name, index_destination_tablespace name, reorder_index regclass, "verbose" boolean) IS $DOC$用途: 函数：请补充业务用途
参数: chunk regclass, destination_tablespace name, index_destination_tablespace name, reorder_index regclass, "verbose" boolean
返回: void
-- 示例：函数调用
SELECT * FROM public.move_chunk(:p1, :p2, :p3, :p4, :p5);$DOC$;

COMMENT ON FUNCTION "public"."pg_stat_statements"(showtext boolean, OUT userid oid, OUT dbid oid, OUT toplevel boolean, OUT queryid bigint, OUT query text, OUT plans bigint, OUT total_plan_time double precision, OUT min_plan_time double precision, OUT max_plan_time double precision, OUT mean_plan_time double precision, OUT stddev_plan_time double precision, OUT calls bigint, OUT total_exec_time double precision, OUT min_exec_time double precision, OUT max_exec_time double precision, OUT mean_exec_time double precision, OUT stddev_exec_time double precision, OUT rows bigint, OUT shared_blks_hit bigint, OUT shared_blks_read bigint, OUT shared_blks_dirtied bigint, OUT shared_blks_written bigint, OUT local_blks_hit bigint, OUT local_blks_read bigint, OUT local_blks_dirtied bigint, OUT local_blks_written bigint, OUT temp_blks_read bigint, OUT temp_blks_written bigint, OUT blk_read_time double precision, OUT blk_write_time double precision, OUT temp_blk_read_time double precision, OUT temp_blk_write_time double precision, OUT wal_records bigint, OUT wal_fpi bigint, OUT wal_bytes numeric, OUT jit_functions bigint, OUT jit_generation_time double precision, OUT jit_inlining_count bigint, OUT jit_inlining_time double precision, OUT jit_optimization_count bigint, OUT jit_optimization_time double precision, OUT jit_emission_count bigint, OUT jit_emission_time double precision) IS $DOC$用途: 函数：请补充业务用途
参数: showtext boolean, OUT userid oid, OUT dbid oid, OUT toplevel boolean, OUT queryid bigint, OUT query text, OUT plans bigint, OUT total_plan_time double precision, OUT min_plan_time double precision, OUT max_plan_time double precision, OUT mean_plan_time double precision, OUT stddev_plan_time double precision, OUT calls bigint, OUT total_exec_time double precision, OUT min_exec_time double precision, OUT max_exec_time double precision, OUT mean_exec_time double precision, OUT stddev_exec_time double precision, OUT rows bigint, OUT shared_blks_hit bigint, OUT shared_blks_read bigint, OUT shared_blks_dirtied bigint, OUT shared_blks_written bigint, OUT local_blks_hit bigint, OUT local_blks_read bigint, OUT local_blks_dirtied bigint, OUT local_blks_written bigint, OUT temp_blks_read bigint, OUT temp_blks_written bigint, OUT blk_read_time double precision, OUT blk_write_time double precision, OUT temp_blk_read_time double precision, OUT temp_blk_write_time double precision, OUT wal_records bigint, OUT wal_fpi bigint, OUT wal_bytes numeric, OUT jit_functions bigint, OUT jit_generation_time double precision, OUT jit_inlining_count bigint, OUT jit_inlining_time double precision, OUT jit_optimization_count bigint, OUT jit_optimization_time double precision, OUT jit_emission_count bigint, OUT jit_emission_time double precision
返回: SETOF record
-- 示例：函数调用
SELECT * FROM public.pg_stat_statements(:p1, :p2, :p3, :p4, :p5, :p6, :p7, :p8, :p9, :p10, :p11, :p12, :p13, :p14, :p15, :p16, :p17, :p18, :p19, :p20, :p21, :p22, :p23, :p24, :p25, :p26, :p27, :p28, :p29, :p30, :p31, :p32, :p33, :p34, :p35, :p36, :p37, :p38, :p39, :p40, :p41, :p42, :p43, :p44);$DOC$;

COMMENT ON FUNCTION "public"."pg_stat_statements_info"(OUT dealloc bigint, OUT stats_reset timestamp with time zone) IS $DOC$用途: 函数：请补充业务用途
参数: OUT dealloc bigint, OUT stats_reset timestamp with time zone
返回: record
-- 示例：函数调用
SELECT * FROM public.pg_stat_statements_info(:p1, :p2);$DOC$;

COMMENT ON FUNCTION "public"."pg_stat_statements_reset"(userid oid, dbid oid, queryid bigint) IS $DOC$用途: 函数：请补充业务用途
参数: userid oid, dbid oid, queryid bigint
返回: void
-- 示例：函数调用
SELECT * FROM public.pg_stat_statements_reset(:p1, :p2, :p3);$DOC$;

COMMENT ON FUNCTION "public"."pldbg_abort_target"(session integer) IS $DOC$用途: 函数：请补充业务用途
参数: session integer
返回: SETOF boolean
-- 示例：函数调用
SELECT * FROM public.pldbg_abort_target(:p1);$DOC$;

COMMENT ON FUNCTION "public"."pldbg_attach_to_port"(portnumber integer) IS $DOC$用途: 函数：请补充业务用途
参数: portnumber integer
返回: integer
-- 示例：函数调用
SELECT * FROM public.pldbg_attach_to_port(:p1);$DOC$;

COMMENT ON FUNCTION "public"."pldbg_continue"(session integer) IS $DOC$用途: 函数：请补充业务用途
参数: session integer
返回: breakpoint
-- 示例：函数调用
SELECT * FROM public.pldbg_continue(:p1);$DOC$;

COMMENT ON FUNCTION "public"."pldbg_create_listener"() IS $DOC$用途: 函数：请补充业务用途
参数: 
返回: integer
-- 示例：函数调用
SELECT * FROM public.pldbg_create_listener();$DOC$;

COMMENT ON FUNCTION "public"."pldbg_deposit_value"(session integer, varname text, linenumber integer, value text) IS $DOC$用途: 函数：请补充业务用途
参数: session integer, varname text, linenumber integer, value text
返回: boolean
-- 示例：函数调用
SELECT * FROM public.pldbg_deposit_value(:p1, :p2, :p3, :p4);$DOC$;

COMMENT ON FUNCTION "public"."pldbg_drop_breakpoint"(session integer, func oid, linenumber integer) IS $DOC$用途: 函数：请补充业务用途
参数: session integer, func oid, linenumber integer
返回: boolean
-- 示例：函数调用
SELECT * FROM public.pldbg_drop_breakpoint(:p1, :p2, :p3);$DOC$;

COMMENT ON FUNCTION "public"."pldbg_get_breakpoints"(session integer) IS $DOC$用途: 函数：请补充业务用途
参数: session integer
返回: SETOF breakpoint
-- 示例：函数调用
SELECT * FROM public.pldbg_get_breakpoints(:p1);$DOC$;

COMMENT ON FUNCTION "public"."pldbg_get_proxy_info"() IS $DOC$用途: 函数：请补充业务用途
参数: 
返回: proxyinfo
-- 示例：函数调用
SELECT * FROM public.pldbg_get_proxy_info();$DOC$;

COMMENT ON FUNCTION "public"."pldbg_get_source"(session integer, func oid) IS $DOC$用途: 函数：请补充业务用途
参数: session integer, func oid
返回: text
-- 示例：函数调用
SELECT * FROM public.pldbg_get_source(:p1, :p2);$DOC$;

COMMENT ON FUNCTION "public"."pldbg_get_stack"(session integer) IS $DOC$用途: 函数：请补充业务用途
参数: session integer
返回: SETOF frame
-- 示例：函数调用
SELECT * FROM public.pldbg_get_stack(:p1);$DOC$;

COMMENT ON FUNCTION "public"."pldbg_get_target_info"(signature text, targettype "char") IS $DOC$用途: 函数：请补充业务用途
参数: signature text, targettype "char"
返回: targetinfo
-- 示例：函数调用
SELECT * FROM public.pldbg_get_target_info(:p1, :p2);$DOC$;

COMMENT ON FUNCTION "public"."pldbg_get_variables"(session integer) IS $DOC$用途: 函数：请补充业务用途
参数: session integer
返回: SETOF var
-- 示例：函数调用
SELECT * FROM public.pldbg_get_variables(:p1);$DOC$;

COMMENT ON FUNCTION "public"."pldbg_oid_debug"(functionoid oid) IS $DOC$用途: 函数：请补充业务用途
参数: functionoid oid
返回: integer
-- 示例：函数调用
SELECT * FROM public.pldbg_oid_debug(:p1);$DOC$;

COMMENT ON FUNCTION "public"."pldbg_select_frame"(session integer, frame integer) IS $DOC$用途: 函数：请补充业务用途
参数: session integer, frame integer
返回: breakpoint
-- 示例：函数调用
SELECT * FROM public.pldbg_select_frame(:p1, :p2);$DOC$;

COMMENT ON FUNCTION "public"."pldbg_set_breakpoint"(session integer, func oid, linenumber integer) IS $DOC$用途: 函数：请补充业务用途
参数: session integer, func oid, linenumber integer
返回: boolean
-- 示例：函数调用
SELECT * FROM public.pldbg_set_breakpoint(:p1, :p2, :p3);$DOC$;

COMMENT ON FUNCTION "public"."pldbg_set_global_breakpoint"(session integer, func oid, linenumber integer, targetpid integer) IS $DOC$用途: 函数：请补充业务用途
参数: session integer, func oid, linenumber integer, targetpid integer
返回: boolean
-- 示例：函数调用
SELECT * FROM public.pldbg_set_global_breakpoint(:p1, :p2, :p3, :p4);$DOC$;

COMMENT ON FUNCTION "public"."pldbg_step_into"(session integer) IS $DOC$用途: 函数：请补充业务用途
参数: session integer
返回: breakpoint
-- 示例：函数调用
SELECT * FROM public.pldbg_step_into(:p1);$DOC$;

COMMENT ON FUNCTION "public"."pldbg_step_over"(session integer) IS $DOC$用途: 函数：请补充业务用途
参数: session integer
返回: breakpoint
-- 示例：函数调用
SELECT * FROM public.pldbg_step_over(:p1);$DOC$;

COMMENT ON FUNCTION "public"."pldbg_wait_for_breakpoint"(session integer) IS $DOC$用途: 函数：请补充业务用途
参数: session integer
返回: breakpoint
-- 示例：函数调用
SELECT * FROM public.pldbg_wait_for_breakpoint(:p1);$DOC$;

COMMENT ON FUNCTION "public"."pldbg_wait_for_target"(session integer) IS $DOC$用途: 函数：请补充业务用途
参数: session integer
返回: integer
-- 示例：函数调用
SELECT * FROM public.pldbg_wait_for_target(:p1);$DOC$;

COMMENT ON FUNCTION "public"."plpgsql_oid_debug"(functionoid oid) IS $DOC$用途: 函数：请补充业务用途
参数: functionoid oid
返回: integer
-- 示例：函数调用
SELECT * FROM public.plpgsql_oid_debug(:p1);$DOC$;

COMMENT ON FUNCTION "public"."remove_compression_policy"(hypertable regclass, if_exists boolean) IS $DOC$用途: 函数：请补充业务用途
参数: hypertable regclass, if_exists boolean
返回: boolean
-- 示例：函数调用
SELECT * FROM public.remove_compression_policy(:p1, :p2);$DOC$;

COMMENT ON FUNCTION "public"."remove_continuous_aggregate_policy"(continuous_aggregate regclass, if_not_exists boolean, if_exists boolean) IS $DOC$用途: 函数：请补充业务用途
参数: continuous_aggregate regclass, if_not_exists boolean, if_exists boolean
返回: void
-- 示例：函数调用
SELECT * FROM public.remove_continuous_aggregate_policy(:p1, :p2, :p3);$DOC$;

COMMENT ON FUNCTION "public"."remove_reorder_policy"(hypertable regclass, if_exists boolean) IS $DOC$用途: 函数：请补充业务用途
参数: hypertable regclass, if_exists boolean
返回: void
-- 示例：函数调用
SELECT * FROM public.remove_reorder_policy(:p1, :p2);$DOC$;

COMMENT ON FUNCTION "public"."remove_retention_policy"(relation regclass, if_exists boolean) IS $DOC$用途: 函数：请补充业务用途
参数: relation regclass, if_exists boolean
返回: void
-- 示例：函数调用
SELECT * FROM public.remove_retention_policy(:p1, :p2);$DOC$;

COMMENT ON FUNCTION "public"."reorder_chunk"(chunk regclass, index regclass, "verbose" boolean) IS $DOC$用途: 函数：请补充业务用途
参数: chunk regclass, index regclass, "verbose" boolean
返回: void
-- 示例：函数调用
SELECT * FROM public.reorder_chunk(:p1, :p2, :p3);$DOC$;

COMMENT ON FUNCTION "public"."safe_upsert_measurement"(p_station_id bigint, p_device_id bigint, p_metric_id bigint, p_ts_raw timestamp with time zone, p_value numeric, p_source_hint text) IS $DOC$用途: 安全写入（UTC/秒对齐/主键合并）
参数: p_station_id bigint, p_device_id bigint, p_metric_id bigint, p_ts_raw timestamp with time zone, p_value numeric, p_source_hint text
返回: boolean
-- 示例：函数调用
SELECT * FROM public.safe_upsert_measurement(:p1, :p2, :p3, :p4, :p5, :p6);$DOC$;

COMMENT ON FUNCTION "public"."safe_upsert_measurement_local"(p_station_id bigint, p_device_id bigint, p_metric_id bigint, p_ts_local timestamp without time zone, p_value numeric, p_source_hint text) IS $DOC$用途: 本地时间写入（按站点 tz 转 UTC 并秒对齐）
参数: p_station_id bigint, p_device_id bigint, p_metric_id bigint, p_ts_local timestamp without time zone, p_value numeric, p_source_hint text
返回: boolean
-- 示例：函数调用
SELECT * FROM public.safe_upsert_measurement_local(:p1, :p2, :p3, :p4, :p5, :p6);$DOC$;

COMMENT ON FUNCTION "public"."set_adaptive_chunking"(hypertable regclass, chunk_target_size text, INOUT chunk_sizing_func regproc, OUT chunk_target_size bigint) IS $DOC$用途: 函数：请补充业务用途
参数: hypertable regclass, chunk_target_size text, INOUT chunk_sizing_func regproc, OUT chunk_target_size bigint
返回: record
-- 示例：函数调用
SELECT * FROM public.set_adaptive_chunking(:p1, :p2, :p3, :p4);$DOC$;

COMMENT ON FUNCTION "public"."set_chunk_time_interval"(hypertable regclass, chunk_time_interval anyelement, dimension_name name) IS $DOC$用途: 函数：请补充业务用途
参数: hypertable regclass, chunk_time_interval anyelement, dimension_name name
返回: void
-- 示例：函数调用
SELECT * FROM public.set_chunk_time_interval(:p1, :p2, :p3);$DOC$;

COMMENT ON FUNCTION "public"."set_integer_now_func"(hypertable regclass, integer_now_func regproc, replace_if_exists boolean) IS $DOC$用途: 函数：请补充业务用途
参数: hypertable regclass, integer_now_func regproc, replace_if_exists boolean
返回: void
-- 示例：函数调用
SELECT * FROM public.set_integer_now_func(:p1, :p2, :p3);$DOC$;

COMMENT ON FUNCTION "public"."set_number_partitions"(hypertable regclass, number_partitions integer, dimension_name name) IS $DOC$用途: 函数：请补充业务用途
参数: hypertable regclass, number_partitions integer, dimension_name name
返回: void
-- 示例：函数调用
SELECT * FROM public.set_number_partitions(:p1, :p2, :p3);$DOC$;

COMMENT ON FUNCTION "public"."set_partitioning_interval"(hypertable regclass, partition_interval anyelement, dimension_name name) IS $DOC$用途: 函数：请补充业务用途
参数: hypertable regclass, partition_interval anyelement, dimension_name name
返回: void
-- 示例：函数调用
SELECT * FROM public.set_partitioning_interval(:p1, :p2, :p3);$DOC$;

COMMENT ON FUNCTION "public"."show_chunks"(relation regclass, older_than "any", newer_than "any", created_before "any", created_after "any") IS $DOC$用途: 函数：请补充业务用途
参数: relation regclass, older_than "any", newer_than "any", created_before "any", created_after "any"
返回: SETOF regclass
-- 示例：函数调用
SELECT * FROM public.show_chunks(:p1, :p2, :p3, :p4, :p5);$DOC$;

COMMENT ON FUNCTION "public"."show_tablespaces"(hypertable regclass) IS $DOC$用途: 函数：请补充业务用途
参数: hypertable regclass
返回: SETOF name
-- 示例：函数调用
SELECT * FROM public.show_tablespaces(:p1);$DOC$;

COMMENT ON FUNCTION "public"."smart_vacuum_strategy"() IS $DOC$用途: 真空策略建议
参数: 
返回: text
-- 示例：函数调用
SELECT * FROM public.smart_vacuum_strategy();$DOC$;

COMMENT ON FUNCTION "public"."time_bucket"(bucket_width interval, ts date, "offset" interval) IS $DOC$用途: 函数：请补充业务用途
参数: bucket_width interval, ts date, "offset" interval
返回: date
-- 示例：函数调用
SELECT * FROM public.time_bucket(:p1, :p2, :p3);$DOC$;

COMMENT ON FUNCTION "public"."time_bucket_gapfill"(bucket_width interval, ts timestamp with time zone, start timestamp with time zone, finish timestamp with time zone) IS $DOC$用途: 函数：请补充业务用途
参数: bucket_width interval, ts timestamp with time zone, start timestamp with time zone, finish timestamp with time zone
返回: timestamp with time zone
-- 示例：函数调用
SELECT * FROM public.time_bucket_gapfill(:p1, :p2, :p3, :p4);$DOC$;

COMMENT ON FUNCTION "public"."timescaledb_post_restore"() IS $DOC$用途: 函数：请补充业务用途
参数: 
返回: boolean
-- 示例：函数调用
SELECT * FROM public.timescaledb_post_restore();$DOC$;

COMMENT ON FUNCTION "public"."timescaledb_pre_restore"() IS $DOC$用途: 函数：请补充业务用途
参数: 
返回: boolean
-- 示例：函数调用
SELECT * FROM public.timescaledb_pre_restore();$DOC$;

COMMENT ON FUNCTION "public"."to_uuidv7"(ts timestamp with time zone) IS $DOC$用途: 函数：请补充业务用途
参数: ts timestamp with time zone
返回: uuid
-- 示例：函数调用
SELECT * FROM public.to_uuidv7(:p1);$DOC$;

COMMENT ON FUNCTION "public"."to_uuidv7_boundary"(ts timestamp with time zone) IS $DOC$用途: 函数：请补充业务用途
参数: ts timestamp with time zone
返回: uuid
-- 示例：函数调用
SELECT * FROM public.to_uuidv7_boundary(:p1);$DOC$;

COMMENT ON FUNCTION "public"."uuid_timestamp"(uuid uuid) IS $DOC$用途: 函数：请补充业务用途
参数: uuid uuid
返回: timestamp with time zone
-- 示例：函数调用
SELECT * FROM public.uuid_timestamp(:p1);$DOC$;

COMMENT ON FUNCTION "public"."uuid_timestamp_micros"(uuid uuid) IS $DOC$用途: 函数：请补充业务用途
参数: uuid uuid
返回: timestamp with time zone
-- 示例：函数调用
SELECT * FROM public.uuid_timestamp_micros(:p1);$DOC$;

COMMENT ON FUNCTION "public"."uuid_version"(uuid uuid) IS $DOC$用途: 函数：请补充业务用途
参数: uuid uuid
返回: integer
-- 示例：函数调用
SELECT * FROM public.uuid_version(:p1);$DOC$;

COMMENT ON FUNCTION "reporting"."ensure_mpps_partitions"(p_ts timestamp with time zone) IS $DOC$用途: 函数：请补充业务用途
参数: p_ts timestamp with time zone
返回: void
-- 示例：函数调用
SELECT * FROM reporting.ensure_mpps_partitions(:p1);$DOC$;

COMMENT ON FUNCTION "reporting"."get_metrics_auto"(p_station_id bigint, p_start_ts timestamp with time zone, p_end_ts timestamp with time zone, p_metric_ids bigint[], p_threshold_days integer) IS $DOC$用途: 函数：请补充业务用途
参数: p_station_id bigint, p_start_ts timestamp with time zone, p_end_ts timestamp with time zone, p_metric_ids bigint[], p_threshold_days integer
返回: TABLE(station_id bigint, device_id bigint, metric_id bigint, ts timestamp with time zone, cnt bigint, avg_value double precision, min_value double precision, max_value double precision, sum_value double precision)
-- 示例：函数调用
SELECT * FROM reporting.get_metrics_auto(:p1, :p2, :p3, :p4, :p5);$DOC$;

COMMENT ON FUNCTION "reporting"."get_metrics_auto_multi"(p_station_ids bigint[], p_start_ts timestamp with time zone, p_end_ts timestamp with time zone, p_device_ids bigint[], p_metric_ids bigint[], p_threshold_days integer) IS $DOC$用途: 函数：请补充业务用途
参数: p_station_ids bigint[], p_start_ts timestamp with time zone, p_end_ts timestamp with time zone, p_device_ids bigint[], p_metric_ids bigint[], p_threshold_days integer
返回: TABLE(station_id bigint, device_id bigint, metric_id bigint, ts timestamp with time zone, cnt bigint, avg_value double precision, min_value double precision, max_value double precision, sum_value double precision)
-- 示例：函数调用
SELECT * FROM reporting.get_metrics_auto_multi(:p1, :p2, :p3, :p4, :p5, :p6);$DOC$;

COMMENT ON FUNCTION "reporting"."get_metrics_daily"(p_station_id bigint, p_start_date date, p_end_date date, p_metric_ids bigint[]) IS $DOC$用途: 函数：请补充业务用途
参数: p_station_id bigint, p_start_date date, p_end_date date, p_metric_ids bigint[]
返回: TABLE(station_id bigint, device_id bigint, metric_id bigint, ts date, cnt bigint, avg_value double precision, min_value double precision, max_value double precision, sum_value double precision)
-- 示例：函数调用
SELECT * FROM reporting.get_metrics_daily(:p1, :p2, :p3, :p4);$DOC$;

COMMENT ON FUNCTION "reporting"."get_metrics_daily_multi"(p_station_ids bigint[], p_start_date date, p_end_date date, p_device_ids bigint[], p_metric_ids bigint[]) IS $DOC$用途: 函数：请补充业务用途
参数: p_station_ids bigint[], p_start_date date, p_end_date date, p_device_ids bigint[], p_metric_ids bigint[]
返回: TABLE(station_id bigint, device_id bigint, metric_id bigint, ts date, cnt bigint, avg_value double precision, min_value double precision, max_value double precision, sum_value double precision)
-- 示例：函数调用
SELECT * FROM reporting.get_metrics_daily_multi(:p1, :p2, :p3, :p4, :p5);$DOC$;

COMMENT ON FUNCTION "reporting"."get_metrics_hourly"(p_station_id bigint, p_start_ts timestamp with time zone, p_end_ts timestamp with time zone, p_metric_ids bigint[]) IS $DOC$用途: 函数：请补充业务用途
参数: p_station_id bigint, p_start_ts timestamp with time zone, p_end_ts timestamp with time zone, p_metric_ids bigint[]
返回: TABLE(station_id bigint, device_id bigint, metric_id bigint, ts_hour timestamp with time zone, cnt bigint, avg_value double precision, min_value double precision, max_value double precision, sum_value double precision)
-- 示例：函数调用
SELECT * FROM reporting.get_metrics_hourly(:p1, :p2, :p3, :p4);$DOC$;

COMMENT ON FUNCTION "reporting"."get_metrics_hourly_multi"(p_station_ids bigint[], p_start_ts timestamp with time zone, p_end_ts timestamp with time zone, p_device_ids bigint[], p_metric_ids bigint[]) IS $DOC$用途: 函数：请补充业务用途
参数: p_station_ids bigint[], p_start_ts timestamp with time zone, p_end_ts timestamp with time zone, p_device_ids bigint[], p_metric_ids bigint[]
返回: TABLE(station_id bigint, device_id bigint, metric_id bigint, ts_hour timestamp with time zone, cnt bigint, avg_value double precision, min_value double precision, max_value double precision, sum_value double precision)
-- 示例：函数调用
SELECT * FROM reporting.get_metrics_hourly_multi(:p1, :p2, :p3, :p4, :p5);$DOC$;

COMMENT ON FUNCTION "reporting"."refresh_mv_measurements"(p_days integer) IS $DOC$用途: 函数：请补充业务用途
参数: p_days integer
返回: void
-- 示例：函数调用
SELECT * FROM reporting.refresh_mv_measurements(:p1);$DOC$;

COMMENT ON VIEW "timescaledb_experimental"."policies" IS $DOC$用途: 视图：用于聚合/便捷查询
使用方法: 直接查询
-- 示例：查看视图内容
SELECT * FROM timescaledb_experimental.policies LIMIT 100;$DOC$;

COMMENT ON FUNCTION "timescaledb_experimental"."add_policies"(relation regclass, if_not_exists boolean, refresh_start_offset "any", refresh_end_offset "any", compress_after "any", drop_after "any") IS $DOC$用途: 函数：请补充业务用途
参数: relation regclass, if_not_exists boolean, refresh_start_offset "any", refresh_end_offset "any", compress_after "any", drop_after "any"
返回: boolean
-- 示例：函数调用
SELECT * FROM timescaledb_experimental.add_policies(:p1, :p2, :p3, :p4, :p5, :p6);$DOC$;

COMMENT ON FUNCTION "timescaledb_experimental"."alter_policies"(relation regclass, if_exists boolean, refresh_start_offset "any", refresh_end_offset "any", compress_after "any", drop_after "any") IS $DOC$用途: 函数：请补充业务用途
参数: relation regclass, if_exists boolean, refresh_start_offset "any", refresh_end_offset "any", compress_after "any", drop_after "any"
返回: boolean
-- 示例：函数调用
SELECT * FROM timescaledb_experimental.alter_policies(:p1, :p2, :p3, :p4, :p5, :p6);$DOC$;

COMMENT ON FUNCTION "timescaledb_experimental"."remove_all_policies"(relation regclass, if_exists boolean) IS $DOC$用途: 函数：请补充业务用途
参数: relation regclass, if_exists boolean
返回: boolean
-- 示例：函数调用
SELECT * FROM timescaledb_experimental.remove_all_policies(:p1, :p2);$DOC$;

COMMENT ON FUNCTION "timescaledb_experimental"."remove_policies"(relation regclass, if_exists boolean, VARIADIC policy_names text[]) IS $DOC$用途: 函数：请补充业务用途
参数: relation regclass, if_exists boolean, VARIADIC policy_names text[]
返回: boolean
-- 示例：函数调用
SELECT * FROM timescaledb_experimental.remove_policies(:p1, :p2, :p3);$DOC$;

COMMENT ON FUNCTION "timescaledb_experimental"."show_policies"(relation regclass) IS $DOC$用途: 函数：请补充业务用途
参数: relation regclass
返回: SETOF jsonb
-- 示例：函数调用
SELECT * FROM timescaledb_experimental.show_policies(:p1);$DOC$;

COMMENT ON FUNCTION "timescaledb_experimental"."time_bucket_ng"(bucket_width interval, ts date) IS $DOC$用途: 函数：请补充业务用途
参数: bucket_width interval, ts date
返回: date
-- 示例：函数调用
SELECT * FROM timescaledb_experimental.time_bucket_ng(:p1, :p2);$DOC$;
