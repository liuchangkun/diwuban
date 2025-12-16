\encoding UTF8
SET client_encoding = 'UTF8';

-- 为各表字段添加中文注释（按信息架构列出的列）

-- completion_runs
COMMENT ON COLUMN public.completion_runs.run_id IS '运行ID';
COMMENT ON COLUMN public.completion_runs.station_id IS '泵站ID';
COMMENT ON COLUMN public.completion_runs.device_id IS '设备ID';
COMMENT ON COLUMN public.completion_runs.start_ts IS '运行时间窗起（timestamptz）';
COMMENT ON COLUMN public.completion_runs.end_ts IS '运行时间窗止（timestamptz）';
COMMENT ON COLUMN public.completion_runs.code_version IS '代码版本标识（如 git 哈希）';
COMMENT ON COLUMN public.completion_runs.imputation_version IS '补全过程版本/算法版本';
COMMENT ON COLUMN public.completion_runs.config_snapshot IS '配置快照（jsonb）';
COMMENT ON COLUMN public.completion_runs.thresholds_snapshot IS '阈值快照（jsonb）';
COMMENT ON COLUMN public.completion_runs.rows_read IS '读取的事实点数量';
COMMENT ON COLUMN public.completion_runs.duration_ms IS '运行耗时（毫秒）';
COMMENT ON COLUMN public.completion_runs.steps_total IS '步骤数量';
COMMENT ON COLUMN public.completion_runs.rerun_policy IS '复跑策略：append/overwrite/skip';
COMMENT ON COLUMN public.completion_runs.parent_run_id IS '父运行ID（复跑来源）';
COMMENT ON COLUMN public.completion_runs.superseded_by_run_id IS '被替代运行ID（被后续运行覆盖）';
COMMENT ON COLUMN public.completion_runs.idempotency_key IS '幂等键（避免重复写入）';
COMMENT ON COLUMN public.completion_runs.group_context IS '泵组上下文（jsonb）';
COMMENT ON COLUMN public.completion_runs.status_reason IS '状态原因摘要';
COMMENT ON COLUMN public.completion_runs.error_code IS '错误代码摘要';
COMMENT ON COLUMN public.completion_runs.created_at IS '创建时间';

-- completion_steps
COMMENT ON COLUMN public.completion_steps.id IS '步骤记录ID';
COMMENT ON COLUMN public.completion_steps.run_id IS '所属运行ID';
COMMENT ON COLUMN public.completion_steps.device_id IS '设备ID';
COMMENT ON COLUMN public.completion_steps.metric_id IS '指标ID';
COMMENT ON COLUMN public.completion_steps.gap_id IS '缺口段ID';
COMMENT ON COLUMN public.completion_steps.gap_start_ts IS '缺口开始时间';
COMMENT ON COLUMN public.completion_steps.gap_end_ts IS '缺口结束时间';
COMMENT ON COLUMN public.completion_steps.gap_len_sec IS '缺口时长（秒）';
COMMENT ON COLUMN public.completion_steps.gap_class IS '缺口分类（short/medium/long/in_startstop）';
COMMENT ON COLUMN public.completion_steps.in_startstop_window IS '是否位于启停窗口内';
COMMENT ON COLUMN public.completion_steps.methods_tried IS '尝试的方法列表（jsonb）';
COMMENT ON COLUMN public.completion_steps.fallback_path IS '回退路径';
COMMENT ON COLUMN public.completion_steps.confidence_reason IS '置信理由（数组）';
COMMENT ON COLUMN public.completion_steps.residual_stats IS '残差统计（jsonb，可选）';
COMMENT ON COLUMN public.completion_steps.step_duration_ms IS '步骤耗时（毫秒）';
COMMENT ON COLUMN public.completion_steps.rows_considered IS '考虑的点数量';
COMMENT ON COLUMN public.completion_steps.data_source IS '数据来源（original/derived）';
COMMENT ON COLUMN public.completion_steps.created_at IS '创建时间';

-- completion_audit
COMMENT ON COLUMN public.completion_audit.id IS '审计记录ID';
COMMENT ON COLUMN public.completion_audit.run_id IS '运行ID（唯一）';
COMMENT ON COLUMN public.completion_audit.coverage_before IS '补全前覆盖率';
COMMENT ON COLUMN public.completion_audit.coverage_after IS '补全后覆盖率';
COMMENT ON COLUMN public.completion_audit.missing_before IS '补全前缺失点数';
COMMENT ON COLUMN public.completion_audit.missing_after IS '补全后缺失点数';
COMMENT ON COLUMN public.completion_audit.max_gap_before_sec IS '补全前最大缺口（秒）';
COMMENT ON COLUMN public.completion_audit.max_gap_after_sec IS '补全后最大缺口（秒）';
COMMENT ON COLUMN public.completion_audit.count_ffill IS '前向填充次数';
COMMENT ON COLUMN public.completion_audit.count_mean IS '均值填充次数';
COMMENT ON COLUMN public.completion_audit.count_reg IS '回归填充次数';
COMMENT ON COLUMN public.completion_audit.count_curve IS '曲线填充次数';
COMMENT ON COLUMN public.completion_audit.count_skipped_long_gap IS '跳过的长缺口次数';
COMMENT ON COLUMN public.completion_audit.startup_drop_ratio IS '启停落点剔除比例';
COMMENT ON COLUMN public.completion_audit.rejects_counts IS '拒绝计数（jsonb，按类别）';
COMMENT ON COLUMN public.completion_audit.thresholds_snapshot_ref IS '阈值快照引用（文本）';
COMMENT ON COLUMN public.completion_audit.group_consistency IS '组一致性审计（jsonb）';
COMMENT ON COLUMN public.completion_audit.audit_time IS '审计时间';

-- completion_failures
COMMENT ON COLUMN public.completion_failures.id IS '失败记录ID';
COMMENT ON COLUMN public.completion_failures.run_id IS '运行ID';
COMMENT ON COLUMN public.completion_failures.object_key IS '对象键（jsonb：station_id/device_id/metric_id）';
COMMENT ON COLUMN public.completion_failures.gap_id IS '缺口段ID';
COMMENT ON COLUMN public.completion_failures.reason_code IS '失败原因代码';
COMMENT ON COLUMN public.completion_failures.evidence_uri IS '证据URI';
COMMENT ON COLUMN public.completion_failures.suggested_action IS '建议动作';
COMMENT ON COLUMN public.completion_failures.created_at IS '创建时间';

-- device_running_thresholds
COMMENT ON COLUMN public.device_running_thresholds.device_id IS '设备ID（PK）';
COMMENT ON COLUMN public.device_running_thresholds.enable_i IS '是否启用电流判定（取三相最大）';
COMMENT ON COLUMN public.device_running_thresholds.enable_p IS '是否启用功率判定';
COMMENT ON COLUMN public.device_running_thresholds.enable_f IS '是否启用频率判定';
COMMENT ON COLUMN public.device_running_thresholds.i_on IS '电流开启阈值';
COMMENT ON COLUMN public.device_running_thresholds.i_off IS '电流关闭阈值';
COMMENT ON COLUMN public.device_running_thresholds.p_on IS '功率开启阈值';
COMMENT ON COLUMN public.device_running_thresholds.p_off IS '功率关闭阈值';
COMMENT ON COLUMN public.device_running_thresholds.f_on IS '频率开启阈值';
COMMENT ON COLUMN public.device_running_thresholds.f_off IS '频率关闭阈值';
COMMENT ON COLUMN public.device_running_thresholds.grace_hold_secs IS '缺报延续秒数';
COMMENT ON COLUMN public.device_running_thresholds.min_run_secs IS '最小运行段长度（用于窗口聚合）';
COMMENT ON COLUMN public.device_running_thresholds.min_stop_secs IS '最小停机段长度（用于窗口聚合）';
COMMENT ON COLUMN public.device_running_thresholds.smoothing_secs IS '平滑窗口秒数（可选）';
COMMENT ON COLUMN public.device_running_thresholds.updated_at IS '更新时间';
COMMENT ON COLUMN public.device_running_thresholds.updated_by IS '更新人/来源';

-- dim_devices
COMMENT ON COLUMN public.dim_devices.id IS '设备ID（PK）';
COMMENT ON COLUMN public.dim_devices.station_id IS '泵站ID';
COMMENT ON COLUMN public.dim_devices.name IS '设备名称（站内唯一）';
COMMENT ON COLUMN public.dim_devices.type IS '设备类型（pump 等）';
COMMENT ON COLUMN public.dim_devices.pump_type IS '泵类型（variable_frequency/soft_start 等）';
COMMENT ON COLUMN public.dim_devices.extra IS '额外信息（jsonb）';
COMMENT ON COLUMN public.dim_devices.created_at IS '创建时间';

-- dim_stations
COMMENT ON COLUMN public.dim_stations.id IS '泵站ID（PK）';
COMMENT ON COLUMN public.dim_stations.name IS '泵站名称';
COMMENT ON COLUMN public.dim_stations.extra IS '额外信息（jsonb，建议包含 tz）';
COMMENT ON COLUMN public.dim_stations.created_at IS '创建时间';

-- dim_metric_config
COMMENT ON COLUMN public.dim_metric_config.id IS '指标ID（PK）';
COMMENT ON COLUMN public.dim_metric_config.metric_key IS '指标键（唯一，如 pump_frequency）';
COMMENT ON COLUMN public.dim_metric_config.unit IS '单位（如 Hz、kW、A）';
COMMENT ON COLUMN public.dim_metric_config.unit_display IS '单位显示';
COMMENT ON COLUMN public.dim_metric_config.decimals_policy IS '小数策略（as_is 等）';
COMMENT ON COLUMN public.dim_metric_config.fixed_decimals IS '固定小数位（可选）';
COMMENT ON COLUMN public.dim_metric_config.value_type IS '值类型（number 等）';
COMMENT ON COLUMN public.dim_metric_config.valid_min IS '有效最小值';
COMMENT ON COLUMN public.dim_metric_config.valid_max IS '有效最大值';
COMMENT ON COLUMN public.dim_metric_config.created_at IS '创建时间';
COMMENT ON COLUMN public.dim_metric_config.updated_at IS '更新时间';

-- dim_mapping_items
COMMENT ON COLUMN public.dim_mapping_items.id IS 'ID（PK）';
COMMENT ON COLUMN public.dim_mapping_items.mapping_hash IS '映射哈希（用于快照一致性）';
COMMENT ON COLUMN public.dim_mapping_items.station_name IS '站点名（源）';
COMMENT ON COLUMN public.dim_mapping_items.device_name IS '设备名（源）';
COMMENT ON COLUMN public.dim_mapping_items.metric_key IS '指标键（源）';
COMMENT ON COLUMN public.dim_mapping_items.source_hint IS '来源提示';
COMMENT ON COLUMN public.dim_mapping_items.created_at IS '创建时间';

-- device_rated_params
COMMENT ON COLUMN public.device_rated_params.id IS 'ID（PK）';
COMMENT ON COLUMN public.device_rated_params.device_id IS '设备ID';
COMMENT ON COLUMN public.device_rated_params.param_key IS '参数键（如 rated_power）';
COMMENT ON COLUMN public.device_rated_params.value_numeric IS '数值（numeric）';
COMMENT ON COLUMN public.device_rated_params.value_text IS '文本值';
COMMENT ON COLUMN public.device_rated_params.unit IS '单位';
COMMENT ON COLUMN public.device_rated_params.source IS '来源';
COMMENT ON COLUMN public.device_rated_params.effective_from IS '生效起';
COMMENT ON COLUMN public.device_rated_params.effective_to IS '生效止';
COMMENT ON COLUMN public.device_rated_params.created_at IS '创建时间';
COMMENT ON COLUMN public.device_rated_params.updated_at IS '更新时间';

-- fact_measurements（父表列注释，分区继承）
COMMENT ON COLUMN public.fact_measurements.id IS 'ID（PK）';
COMMENT ON COLUMN public.fact_measurements.station_id IS '泵站ID';
COMMENT ON COLUMN public.fact_measurements.device_id IS '设备ID';
COMMENT ON COLUMN public.fact_measurements.metric_id IS '指标ID';
COMMENT ON COLUMN public.fact_measurements.ts_raw IS '原始时间（建议 UTC）';
COMMENT ON COLUMN public.fact_measurements.ts_bucket IS '整秒对齐时间';
COMMENT ON COLUMN public.fact_measurements.value IS '数值';
COMMENT ON COLUMN public.fact_measurements.source_hint IS '来源提示';
COMMENT ON COLUMN public.fact_measurements.inserted_at IS '插入时间';

