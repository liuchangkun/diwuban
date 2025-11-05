\encoding UTF8
SET client_encoding = 'UTF8';

-- 为 public 架构中主要对象添加“用途/字段/参数/返回/示例 SQL”注释（仅 COMMENT，不改对象定义）

-- 表：核心维/事实/配置/追踪（维持原简要注释）
COMMENT ON TABLE public.dim_stations IS '泵站维表';
COMMENT ON TABLE public.dim_devices IS '设备维表';
COMMENT ON TABLE public.dim_metric_config IS '指标配置';
COMMENT ON TABLE public.fact_measurements IS '时序事实（秒对齐）';
COMMENT ON TABLE public.device_running_thresholds IS '设备运行判定阈值（集中配置）';
COMMENT ON TABLE public.device_rated_params IS '设备额定参数（可选）';
COMMENT ON TABLE public.dim_mapping_items IS '映射快照（导入时使用）';
COMMENT ON TABLE public.completion_runs IS '追踪-运行级';
COMMENT ON TABLE public.completion_steps IS '追踪-步骤级';
COMMENT ON TABLE public.completion_audit IS '追踪-审计级';
COMMENT ON TABLE public.completion_failures IS '追踪-失败清单';

-- 视图（含用途/字段/示例 SQL）：
COMMENT ON VIEW public.v_training_timeseries_1s IS $DOC$
用途: 统一 1s 读取口径（训练/分析）。
字段: ts_bucket, station_id, station_name, device_id, device_name, metric_id, metric_key, unit_display, value。
示例:
-- 单设备单指标 1 小时明细
SELECT ts_bucket, value
FROM public.v_training_timeseries_1s
WHERE station_id=1 AND device_id=1 AND metric_id=101
  AND ts_bucket BETWEEN '2025-09-01 00:00+00' AND '2025-09-01 01:00+00'
ORDER BY ts_bucket
LIMIT 1000;
-- 按小时聚合
SELECT date_trunc('hour', ts_bucket) AS ts_hour, avg(value) AS avg_v
FROM public.v_training_timeseries_1s
WHERE station_id=1 AND device_id=1 AND metric_id=101
  AND ts_bucket >= now() - interval '24 hours'
GROUP BY 1 ORDER BY 1;
$DOC$;

COMMENT ON VIEW public.v_data_quality_stats IS $DOC$
用途: 按日数据质量统计。
字段: date_bucket, total_points, null_count, coverage_rate, outlier_count。
示例:
SELECT * FROM public.v_data_quality_stats
WHERE station_id=1 AND device_id=1 AND metric_id=101
  AND date_bucket BETWEEN current_date-7 AND current_date-1
ORDER BY date_bucket;
$DOC$;

COMMENT ON VIEW public.v_coverage_gaps_1s IS $DOC$
用途: 覆盖/缺口概览（1s 粒度），提供基于 fn_detect_gaps_1s 的查询模板。
示例（推荐直接调函数）:
SELECT *
FROM public.fn_detect_gaps_1s(1,1,101,'2025-09-01 00:00+00','2025-09-01 01:00+00', 300)
ORDER BY gap_start_ts;
$DOC$;

COMMENT ON VIEW public.v_startstop_windows IS $DOC$
用途: 启停窗口快照视图（字段口径模板；视图无参）。
示例（请用函数产出明细窗口后查询）:
SELECT * FROM public.fn_startstop_windows(
  p_station_id=>1,
  p_device_id=>1,
  p_metric_ids=>ARRAY[201,202],
  p_start_ts=>'2025-09-01 00:00+00',
  p_end_ts=>'2025-09-01 06:00+00',
  p_ramp_thr=>5.0, p_jitter_thr=>0.5,
  p_startup_cooldown_sec=>60, p_shutdown_cooldown_sec=>60,
  p_hysteresis_sec=>10
) ORDER BY win_start_ts;
$DOC$;

COMMENT ON VIEW public.station_device_rated_params_view IS $DOC$
用途: 站点-设备额定参数整合视图。
示例:
SELECT * FROM public.station_device_rated_params_view
WHERE station_id=1 AND device_id=1;
$DOC$;

COMMENT ON VIEW public.station_devices_pivot_view IS $DOC$
用途: 站点设备透视视图（示例）。
示例:
SELECT * FROM public.station_devices_pivot_view
WHERE station_id=1
ORDER BY device_name;
$DOC$;

COMMENT ON VIEW public.metrics_availability_v_weekly IS $DOC$
用途: 逐周可用性统计（覆盖率与状态标记）。
示例:
SELECT * FROM public.metrics_availability_v_weekly
WHERE week_start >= date_trunc('week', now()) - interval '8 weeks'
ORDER BY station_id, device_id, metric_id, week_start
LIMIT 200;
$DOC$;

-- 函数（含用途/参数/返回/示例）：
COMMENT ON FUNCTION public.fn_running_state_1s(bigint,bigint,timestamptz,timestamptz) IS $DOC$
用途: 逐秒运行判定（按 device_running_thresholds 阈值，on/off 滞回 + 缺报延续）。
参数: p_station_id, p_device_id, p_start_ts, p_end_ts。
返回: ts_bucket, is_running, max_i, p, f, source。
示例:
SELECT * FROM public.fn_running_state_1s(1,1,'2025-09-01 00:00+00','2025-09-01 02:00+00')
ORDER BY ts_bucket;
$DOC$;

COMMENT ON FUNCTION public.fn_startstop_windows(bigint,timestamptz,timestamptz) IS $DOC$
用途: 仅 device_id + 时间窗 → 返回逐秒运行状态（1s 粒度），内部委托 fn_running_state_1s。
参数: p_device_id, p_start_ts, p_end_ts。
返回: ts_bucket, is_running, max_i, p, f, source。
示例:
SELECT * FROM public.fn_startstop_windows(1,'2025-09-01 00:00+00','2025-09-01 00:10+00');
$DOC$;

COMMENT ON FUNCTION public.fn_training_timeseries_1s(bigint,bigint,bigint,timestamptz,timestamptz) IS $DOC$
用途: 统一 1s 训练口径（长表返回）。
参数: p_station_id, p_device_id, p_metric_id, p_start_ts, p_end_ts。
返回: ts_bucket, value, station_id, device_id, metric_id。
示例:
SELECT ts_bucket, value FROM public.fn_training_timeseries_1s(1,1,101, now()-interval '10 minutes', now());
$DOC$;

COMMENT ON FUNCTION public.fn_detect_gaps_1s(bigint,bigint,bigint,timestamptz,timestamptz,integer) IS $DOC$
用途: 缺口段识别（基于秒级对齐）。
参数: p_station_id, p_device_id, p_metric_id, p_start_ts, p_end_ts, p_max_gap_sec。
返回: gap_id, gap_start_ts, gap_end_ts, gap_len_sec, gap_class。
示例:
SELECT * FROM public.fn_detect_gaps_1s(1,1,101,'2025-09-01 00:00+00','2025-09-01 03:00+00', 300);
$DOC$;

COMMENT ON FUNCTION public.fn_quality_stats_1d(bigint,bigint,bigint,timestamptz,timestamptz) IS $DOC$
用途: 按日质量统计（只读）。
参数: p_station_id, p_device_id, p_metric_id, p_start_ts, p_end_ts。
返回: date_bucket, total_points, null_count, coverage_rate, outlier_count。
示例:
SELECT * FROM public.fn_quality_stats_1d(1,1,101, now()-interval '30 days', now());
$DOC$;

COMMENT ON FUNCTION public.metrics_availability_window(timestamptz,timestamptz) IS $DOC$
用途: 计算对象在时间窗内的可用性与覆盖率。
参数: _start, _end。
返回: station_id, device_id, metric_id, metric_key, start_ts, end_ts, present_secs, total_secs, coverage_rate, acquisition_status, compute_flag, status, method_hint。
示例:
SELECT * FROM public.metrics_availability_window(now()-interval '1 day', now())
ORDER BY station_id, device_id, metric_id, start_ts
LIMIT 200;
$DOC$;

COMMENT ON FUNCTION public.metrics_presence_per_second(timestamptz,timestamptz,text,text) IS $DOC$
用途: 秒级时间点 × 泵站 × 设备：需要计算补齐的指标与已有指标清单。
参数: _start, _end, _station_name=NULL, _device_name=NULL。
返回: station, device, ts_local(+08), need_compute_metrics[], available_metrics[]。
示例:
SELECT * FROM public.metrics_presence_per_second(now()-interval '5 minutes', now(), '站点A', '设备1')
ORDER BY ts_local;
$DOC$;

COMMENT ON FUNCTION public.get_full_horizontal_data(integer) IS $DOC$
用途: 返回完整横向数据（示例返回 JSON 列）。
参数: p_limit。
示例:
SELECT * FROM public.get_full_horizontal_data(100);
$DOC$;

-- 其他函数（用途与示例）
COMMENT ON FUNCTION public.safe_upsert_measurement(bigint,bigint,bigint,timestamptz,numeric,text) IS $DOC$
用途: 安全写入（UTC/秒对齐/主键合并）。
示例:
SELECT public.safe_upsert_measurement(1,1,101, '2025-09-01 00:00:00+00', 12.34, 'manual');
$DOC$;

COMMENT ON FUNCTION public.safe_upsert_measurement_local(bigint,bigint,bigint,timestamp,numeric,text) IS $DOC$
用途: 本地时间写入（按站点 tz 转 UTC 并秒对齐）。
示例:
SELECT public.safe_upsert_measurement_local(1,1,101, '2025-09-01 08:00:00', 12.34, 'manual');
$DOC$;

COMMENT ON FUNCTION public.ensure_week_partition(date,integer,text) IS $DOC$
用途: 确保周分区与 HASH 子分区存在。
示例:
SELECT public.ensure_week_partition(date_trunc('week', now())::date, 16, 'public');
$DOC$;

COMMENT ON FUNCTION public.database_health_check() IS $DOC$
用途: 数据库健康体检（只读）。
示例:
SELECT * FROM public.database_health_check();
$DOC$;

COMMENT ON FUNCTION public.smart_vacuum_strategy() IS $DOC$
用途: 真空策略建议。
示例:
SELECT public.smart_vacuum_strategy();
$DOC$;

COMMENT ON FUNCTION public.auto_performance_tuning() IS $DOC$
用途: 自动性能调优（示意）。
示例:
SELECT public.auto_performance_tuning();
$DOC$;

COMMENT ON FUNCTION public.auto_space_reclaim() IS $DOC$
用途: 空间回收（示意）。
示例:
SELECT public.auto_space_reclaim();
$DOC$;

COMMENT ON FUNCTION public.get_device_metrics_by_time_range(bigint,timestamptz,timestamptz,integer) IS $DOC$
用途: 设备指标时间窗查询（JSON 聚合）。
参数: p_device_id, p_start_time, p_end_time, p_limit。
示例:
SELECT * FROM public.get_device_metrics_by_time_range(1, now()-interval '1 day', now(), 1000);
$DOC$;

COMMENT ON FUNCTION public.get_station_devices_metrics_by_time_range(bigint,timestamptz,timestamptz,integer) IS $DOC$
用途: 按站点查询设备指标（JSON 聚合）。
参数: p_station_id, p_start_time, p_end_time, p_limit。
示例:
SELECT * FROM public.get_station_devices_metrics_by_time_range(1, now()-interval '1 day', now(), 1000);
$DOC$;

COMMENT ON FUNCTION public.get_performance_metrics() IS $DOC$
用途: 性能指标视图（示意）。
示例:
SELECT * FROM public.get_performance_metrics();
$DOC$;

COMMENT ON FUNCTION public.batch_delete_old_data(timestamptz,integer) IS $DOC$
用途: 分批删除历史数据（示意）。
参数: p_cutoff_date, p_batch_size。
示例:
SELECT public.batch_delete_old_data(now()-interval '365 days', 10000);
$DOC$;

