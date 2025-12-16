-- 迁移：为核心函数添加完整中文注释（仅注释，不改结构）
-- 范围：优先质量/运行/覆盖/统计/报表相关；其余扩展函数（TimescaleDB/pg_stat_statements）后续批次补齐
-- 口径：时间统一 UTC；时间窗半开区间 [start, end)

/* ===== 运行/启停识别 ===== */
COMMENT ON FUNCTION public.fn_running_state_1s(
  bigint, bigint, timestamp with time zone, timestamp with time zone
) IS
'用途：按阈值与滞回逐秒判定设备运行状态；返回每秒 is_running 及辅助特征（max_i、p、f、source）。
参数：station_id, device_id, start_ts, end_ts（UTC）
返回：(ts_bucket timestamptz, is_running bool, max_i double precision, p double precision, f double precision, source text)
示例：
  SELECT * FROM public.fn_running_state_1s(1, 101, ''2025-09-01T00:00:00Z'', ''2025-09-01T01:00:00Z'') LIMIT 5;';

COMMENT ON FUNCTION public.fn_startstop_windows(
  bigint, bigint, bigint[], timestamp with time zone, timestamp with time zone,
  double precision, double precision, integer, integer, integer
) IS
'用途：综合多指标信号识别启停/非稳态窗口（支持软启/变频），返回窗口起止。
参数：station_id, device_id, metric_ids[], start_ts, end_ts, ramp_thr, jitter_thr, startup_cooldown_sec, shutdown_cooldown_sec, hysteresis_sec
返回：(win_id bigint, win_type text, win_start_ts timestamptz, win_end_ts timestamptz)
示例：
  SELECT * FROM public.fn_startstop_windows(1,101,ARRAY[201,202,301],''2025-09-01T00:00:00Z'',''2025-09-01T02:00:00Z'',0.5,0.8,10,10,5);';

COMMENT ON FUNCTION public.fn_startstop_windows(
  bigint, timestamp with time zone, timestamp with time zone
) IS
'用途：按 device_id + 时间窗返回逐秒运行状态（内部委托 fn_running_state_1s）。
参数：device_id, start_ts, end_ts（UTC）
返回：(ts_bucket timestamptz, is_running bool, max_i double precision, p double precision, f double precision, source text)
示例：
  SELECT * FROM public.fn_startstop_windows(101, ''2025-09-01T00:00:00Z'', ''2025-09-01T01:00:00Z'') LIMIT 5;';

/* ===== 覆盖/可用性 ===== */
COMMENT ON FUNCTION public.metrics_presence_per_second(
  timestamp with time zone, timestamp with time zone, text, text
) IS
'用途：逐秒输出 站点/设备/时间点 的【需计算指标】与【已有指标】集合（按策略表与设备能力推导）。
参数：_start, _end（UTC），_station_name，可为空；_device_name，可为空
返回：(station text, device text, ts_utc timestamptz, need_compute_metrics text[], available_metrics text[])
示例：
  SELECT * FROM public.metrics_presence_per_second(''2025-09-01T00:00:00Z'',''2025-09-01T00:05:00Z'',''S-01'',''D-01'');';

COMMENT ON FUNCTION public.metrics_presence_per_second_original(
  timestamp with time zone, timestamp with time zone, text, text
) IS
'用途：presence 原始版本；含本地时间文本字段（向后兼容）。
参数：同上
返回：与当前版类似，附加 ts_local 文本
示例：
  SELECT * FROM public.metrics_presence_per_second_original(''2025-09-01T00:00:00Z'',''2025-09-01T00:05:00Z'',''S-01'',''D-01'');';

COMMENT ON FUNCTION public.metrics_availability_window(
  timestamp with time zone, timestamp with time zone
) IS
'用途：任意时间窗内设备×指标的覆盖率与分类，结合策略表给出 status 与 method_hint。
参数：_start, _end（UTC）
返回：(station_id int, device_id int, metric_id int, metric_key text, start_ts timestamptz, end_ts timestamptz,
       present_secs bigint, total_secs bigint, coverage_rate double precision, acquisition_status text, compute_flag text, status text, method_hint text)
示例：
  SELECT * FROM public.metrics_availability_window(''2025-09-01T00:00:00Z'',''2025-09-02T00:00:00Z'') LIMIT 50;
性能建议：
  - 必须限定时间窗并结合站/设/指标过滤；
  - 大窗口请分批/分桶处理，避免全表扫描。';

/* ===== 质量统计/训练 ===== */
COMMENT ON FUNCTION public.fn_quality_stats_1d(
  bigint, bigint, bigint, timestamp with time zone, timestamp with time zone
) IS
'用途：按日维度输出质量统计（覆盖率、越界/空值计数等）。
参数：station_id, device_id, metric_id, start_ts, end_ts（UTC）
返回：(date_bucket date, total_points bigint, null_count bigint, coverage_rate double precision, outlier_count bigint)
示例：
  SELECT * FROM public.fn_quality_stats_1d(1,101,301,''2025-09-01T00:00:00Z'',''2025-09-08T00:00:00Z'');
性能建议：
  - 建议按站/设/指标明确过滤，时间窗≤90天；
  - 横跨长区间请分段计算并 union all 汇总。';

COMMENT ON FUNCTION public.fn_training_timeseries_1s(
  bigint, bigint, bigint, timestamp with time zone, timestamp with time zone
) IS
'用途：统一 1s 粒度训练数据导出（长表返回）。
参数：station_id, device_id, metric_id, start_ts, end_ts（UTC）
返回：(ts_bucket timestamptz, value double precision, station_id bigint, device_id bigint, metric_id bigint)
示例：
  SELECT * FROM public.fn_training_timeseries_1s(1,101,301,''2025-09-01T00:00:00Z'',''2025-09-01T00:10:00Z'') LIMIT 10;
性能建议：
  - 强烈建议小窗口、带过滤、并分页导出；
  - 大体量导出请优先使用物化聚合或离线导出链路。';

/* ===== 质量标注过程 ===== */
COMMENT ON FUNCTION public.sp_mark_quality_window(
  timestamp with time zone, timestamp with time zone, bigint, bigint
) IS
'用途：在给定时间窗内按站/设过滤执行质量标注（按规则集）。
参数：p_start, p_end（UTC）, p_station_id 可空, p_device_id 可空
返回：void（过程）
示例：
  SELECT public.sp_mark_quality_window(''2025-09-01T00:00:00Z'',''2025-09-01T01:00:00Z'', NULL, 101);';

COMMENT ON FUNCTION public.sp_mark_quality_window(
  timestamp with time zone, timestamp with time zone, bigint, bigint, integer[]
) IS
'用途：同上，限定质量码集合 p_codes 执行。
参数：在基础参数上新增 p_codes int[]
返回：void
示例：
  SELECT public.sp_mark_quality_window(''2025-09-01T00:00:00Z'',''2025-09-01T01:00:00Z'', 1, 101, ARRAY[101,141,503]);';

COMMENT ON FUNCTION public.sp_mark_quality_window_vfast(
  timestamp with time zone, timestamp with time zone, bigint, bigint
) IS
'用途：质量标注加速版本（预筛候选+批量更新），语义与常规版一致。
参数：p_start, p_end（UTC）, p_station_id, p_device_id
返回：void
示例：
  SELECT public.sp_mark_quality_window_vfast(''2025-09-01T00:00:00Z'',''2025-09-01T02:00:00Z'', NULL, 101);';

COMMENT ON FUNCTION public.sp_mark_quality_window_vfast(
  timestamp with time zone, timestamp with time zone, bigint, bigint, integer[]
) IS
'用途：同上，限定 p_codes。
参数：新增 p_codes int[]
返回：void
示例：
  SELECT public.sp_mark_quality_window_vfast(''2025-09-01T00:00:00Z'',''2025-09-01T02:00:00Z'', 1, 101, ARRAY[701,702]);';

COMMENT ON FUNCTION public.sp_mark_quality_window_vfast_diag(
  timestamp with time zone, timestamp with time zone, bigint, bigint, integer[], text, text
) IS
'用途：标注同时记录诊断日志（diag_level=off|brief|full，run_id 关联一次运行）。
参数：在 p_codes 基础上新增 p_diag_level, p_run_id
返回：void
示例：
  SELECT public.sp_mark_quality_window_vfast_diag(''2025-09-01T00:00:00Z'',''2025-09-01T02:00:00Z'', 1, 101, NULL, ''brief'', ''RUN_X'');';

COMMENT ON FUNCTION public.sp_reset_quality_window(
  timestamp with time zone, timestamp with time zone, bigint, bigint
) IS
'用途：重置时间窗内质量标注（quality_* 置 NULL）。
参数：p_start, p_end（UTC）, p_station_id, p_device_id
返回：void
示例：
  SELECT public.sp_reset_quality_window(''2025-09-01T00:00:00Z'',''2025-09-01T01:00:00Z'', NULL, 101);';

COMMENT ON FUNCTION public.sp_generate_quality_eval_by_device_metric(
  timestamp with time zone, timestamp with time zone, bigint, bigint
) IS
'用途：生成窗口内 设备×指标×质量码 的行数统计，写入评价表。
参数：p_start, p_end（UTC）, p_station_id, p_device_id
返回：void
示例：
  SELECT public.sp_generate_quality_eval_by_device_metric(''2025-09-01T00:00:00Z'',''2025-09-02T00:00:00Z'', 1, NULL);';

/* ===== 运行阈值/基线刷新 ===== */
COMMENT ON FUNCTION public.sp_refresh_device_running_thresholds_otsu(
  timestamp with time zone, timestamp with time zone, bigint, bigint
) IS
'用途：按窗口用 Otsu 法估计设备运行阈值（样本不足回退稳健分位）。
参数：p_start_ts, p_end_ts（UTC）, p_station_id, p_device_id
返回：void
示例：
  SELECT public.sp_refresh_device_running_thresholds_otsu(''2025-09-01T00:00:00Z'',''2025-09-07T00:00:00Z'', NULL, 101);';

COMMENT ON FUNCTION public.sp_refresh_metric_rule_auto_baseline(
  integer, bigint, bigint
) IS
'用途：基于近 N 天稳态且质量=0 的数据自动计算规则基线，写入表。
参数：p_lookback_days, p_station_id, p_device_id
返回：void
示例：
  SELECT public.sp_refresh_metric_rule_auto_baseline(30, 1, NULL);';

COMMENT ON FUNCTION public.sp_refresh_metric_rule_auto_baseline_win(
  timestamp with time zone, timestamp with time zone, bigint, bigint
) IS
'用途：带时间窗的自动基线刷新。
参数：p_start_ts, p_end_ts（UTC）, p_station_id, p_device_id
返回：void
示例：
  SELECT public.sp_refresh_metric_rule_auto_baseline_win(''2025-09-01T00:00:00Z'',''2025-09-15T00:00:00Z'', 1, NULL);';

/* ===== 统计物化刷新 ===== */
COMMENT ON FUNCTION public.sp_refresh_mv_metric_60s_stats(
  timestamp with time zone, timestamp with time zone, bigint, bigint
) IS
'用途：刷新 60s 统计物化表。
参数：p_start, p_end（UTC）, p_station_id, p_device_id
返回：void
示例：
  SELECT public.sp_refresh_mv_metric_60s_stats(''2025-09-01T00:00:00Z'',''2025-09-02T00:00:00Z'', 1, 101);';

COMMENT ON FUNCTION public.sp_refresh_mv_running_presence(
  timestamp with time zone, timestamp with time zone, bigint, bigint
) IS
'用途：刷新运行/覆盖相关物化结果。
参数：p_start, p_end（UTC）, p_station_id, p_device_id
返回：void
示例：
  SELECT public.sp_refresh_mv_running_presence(''2025-09-01T00:00:00Z'',''2025-09-02T00:00:00Z'', NULL, 101);';

/* ===== 报表/聚合（reporting 架构） ===== */
COMMENT ON FUNCTION reporting.ensure_mpps_partitions(
  timestamp with time zone
) IS
'用途：确保 mpps_* 分区存在（按周/HASH）。
参数：p_ts（UTC）
返回：void
示例：
  SELECT reporting.ensure_mpps_partitions(''2025-09-01T00:00:00Z'');';

COMMENT ON FUNCTION reporting.get_metrics_hourly(
  bigint, timestamp with time zone, timestamp with time zone, bigint[]
) IS
'用途：按小时聚合设备×指标统计。
参数：p_station_id, p_start_ts, p_end_ts（UTC）, p_metric_ids[] 可空
返回：(station_id, device_id, metric_id, ts_hour timestamptz, cnt bigint, avg_value double precision, min_value double precision, max_value double precision, sum_value double precision)
示例：
  SELECT * FROM reporting.get_metrics_hourly(1,''2025-09-01T00:00:00Z'',''2025-09-03T00:00:00Z'',NULL) LIMIT 100;
性能建议：
  - 必须限定时间窗（建议≤31天）与站/设/指标过滤，避免全表扫描；
  - 大查询请分站/分设备/分时间分批执行；必要时使用 LIMIT 抽样核对。';

COMMENT ON FUNCTION reporting.get_metrics_hourly_multi(
  bigint[], timestamp with time zone, timestamp with time zone, bigint[], bigint[]
) IS
'用途：多站/多设备/多指标的小时聚合。
参数：p_station_ids[], p_start_ts, p_end_ts（UTC）, p_device_ids[] 可空, p_metric_ids[] 可空
返回：同上
示例：
  SELECT * FROM reporting.get_metrics_hourly_multi(ARRAY[1,2],''2025-09-01T00:00:00Z'',''2025-09-02T00:00:00Z'',NULL,NULL);
性能建议：
  - 建议拆分为多次单站/小时间窗批量查询，合并结果；
  - 设备/指标集合过大时，请使用数组限制与分批。';

COMMENT ON FUNCTION reporting.get_metrics_daily(
  bigint, date, date, bigint[]
) IS
'用途：按日聚合设备×指标统计。
参数：p_station_id, p_start_date, p_end_date, p_metric_ids[] 可空
返回：(station_id, device_id, metric_id, ts date, cnt bigint, avg_value double precision, min_value double precision, max_value double precision, sum_value double precision)
示例：
  SELECT * FROM reporting.get_metrics_daily(1, DATE ''2025-09-01'', DATE ''2025-09-07'', NULL);
性能建议：
  - 日期跨度建议≤90天；更长周期请分段聚合后汇总；
  - 指标集合大时，按分组/分页批量处理。';

COMMENT ON FUNCTION reporting.get_metrics_daily_multi(
  bigint[], date, date, bigint[], bigint[]
) IS
'用途：多站/多设备/多指标的日聚合。
参数：p_station_ids[], p_start_date, p_end_date, p_device_ids[] 可空, p_metric_ids[] 可空
返回：同上
示例：
  SELECT * FROM reporting.get_metrics_daily_multi(ARRAY[1,2], DATE ''2025-09-01'', DATE ''2025-09-07'', NULL, NULL);
性能建议：
  - 多站/多设备请拆分批量请求；
  - 建议对大时间跨度分段执行并并行化处理。';

COMMENT ON FUNCTION reporting.get_metrics_auto(
  bigint, timestamp with time zone, timestamp with time zone, bigint[], integer
) IS
'用途：在覆盖阈值内自动选择最优聚合窗口返回统计。
参数：p_station_id, p_start_ts, p_end_ts（UTC）, p_metric_ids[] 可空, p_threshold_days 默认 3
返回：与 hourly/daily 类似
示例：
  SELECT * FROM reporting.get_metrics_auto(1,''2025-09-01T00:00:00Z'',''2025-09-05T00:00:00Z'',NULL,3);
性能建议：
  - 阈值过大可能导致扫描范围过广；
  - 优先对小时间窗使用 auto 模式，对大窗口选择固定粒度。';

COMMENT ON FUNCTION reporting.get_metrics_auto_multi(
  bigint[], timestamp with time zone, timestamp with time zone, bigint[], bigint[], integer
) IS
'用途：多站版本的自动聚合。
参数：p_station_ids[], p_start_ts, p_end_ts（UTC）, p_device_ids[] 可空, p_metric_ids[] 可空, p_threshold_days 默认 3
返回：同上
示例：
  SELECT * FROM reporting.get_metrics_auto_multi(ARRAY[1,2],''2025-09-01T00:00:00Z'',''2025-09-05T00:00:00Z'',NULL,NULL,3);
性能建议：
  - 建议先按站点/时间拆分任务，分批或并行跑；
  - 大集合请限制 device_ids/metric_ids 数组规模并分批。';

