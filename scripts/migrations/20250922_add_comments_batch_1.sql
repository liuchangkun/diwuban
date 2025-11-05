-- 迁移：为核心表/视图添加完整中文注释（仅注释，无结构变更）
-- 对象：public.mv_device_running_1s、public.mv_presence_1s、public.mv_metric_60s_stats、public.quality_diagnosis_log、public.mv_presence_1s_any
-- 口径：时间统一使用 UTC；时间窗遵循半开区间 [start, end)
-- 验证方式：执行后可通过 pg_description / information_schema.columns 只读校验

/* ===== mv_device_running_1s ===== */
COMMENT ON TABLE public.mv_device_running_1s IS
'用途：按设备逐秒运行状态的物化结果。基于功率/电流等信号与阈值（滞回）判定 0/1。
使用方法：按站点/设备与时间窗查询，时间窗采用半开区间 [start,end)。
示例：
  SELECT ts_bucket, running
  FROM public.mv_device_running_1s
  WHERE station_id = :sid AND device_id = :did
    AND ts_bucket >= ''2025-09-01T00:00:00Z'' AND ts_bucket < ''2025-09-01T01:00:00Z''
  ORDER BY ts_bucket;
典型联表：
  SELECT r.ts_bucket, r.running, s.name AS station_name, d.name AS device_name
  FROM public.mv_device_running_1s r
  LEFT JOIN dim_stations s ON s.id = r.station_id
  LEFT JOIN dim_devices d ON d.id = r.device_id
  WHERE r.ts_bucket >= ''2025-09-01T00:00:00Z'' AND r.ts_bucket < ''2025-09-01T01:00:00Z'';
注意事项：
  - ts_bucket 为 UTC 秒级时间桶；查询请显式使用半开区间；
  - running 取值：0=停机，1=运行；
  - 数据为计算/刷新的产物，可能存在延迟。';

COMMENT ON COLUMN public.mv_device_running_1s.station_id IS '站点ID（维度表 dim_stations 主键）';
COMMENT ON COLUMN public.mv_device_running_1s.device_id IS '设备ID（维度表 dim_devices 主键）';
COMMENT ON COLUMN public.mv_device_running_1s.ts_bucket IS 'UTC 秒级时间桶（对齐到整秒）；查询统一使用 [start,end)';
COMMENT ON COLUMN public.mv_device_running_1s.running IS '运行标记（smallint）：0=停，1=运行';

/* ===== mv_presence_1s ===== */
COMMENT ON TABLE public.mv_presence_1s IS
'用途：按 设备×指标×秒 的覆盖结果（是否有有效采样）。
使用方法：用于覆盖率计算、按指标筛选待计算集合。
示例：
  SELECT p.ts_bucket, p.present
  FROM public.mv_presence_1s p
  WHERE p.station_id=:sid AND p.device_id=:did AND p.metric_id=:mid
    AND p.ts_bucket >= ''2025-09-01T00:00:00Z'' AND p.ts_bucket < ''2025-09-01T01:00:00Z''
  ORDER BY p.ts_bucket;
典型联表：
  SELECT p.ts_bucket, p.present, s.name AS station_name, d.name AS device_name, m.metric_key
  FROM public.mv_presence_1s p
  LEFT JOIN dim_stations s ON s.id = p.station_id
  LEFT JOIN dim_devices d ON d.id = p.device_id
  LEFT JOIN dim_metric_metadata m ON m.id = p.metric_id
  WHERE p.ts_bucket >= ''2025-09-01T00:00:00Z'' AND p.ts_bucket < ''2025-09-01T01:00:00Z'';
注意事项：
  - present：覆盖=1/缺失=0；
  - 判定口径：缺秒=该秒无任何采样；空值=存在样本但 value 为 NULL；拒绝样本=样本存在但被质量/过滤规则排除（不计入覆盖）；
  - ts_bucket 为 UTC 秒级时间桶；统一使用半开区间 [start,end)。';

COMMENT ON COLUMN public.mv_presence_1s.station_id IS '站点ID（dim_stations）';
COMMENT ON COLUMN public.mv_presence_1s.device_id IS '设备ID（dim_devices）';
COMMENT ON COLUMN public.mv_presence_1s.metric_id IS '指标ID（dim_metric_metadata/配置映射后的有效指标）';
COMMENT ON COLUMN public.mv_presence_1s.ts_bucket IS 'UTC 秒级时间桶（对齐到整秒）；查询统一使用 [start,end)';
COMMENT ON COLUMN public.mv_presence_1s.present IS '覆盖：覆盖=1/缺失=0';

/* ===== mv_metric_60s_stats ===== */
COMMENT ON TABLE public.mv_metric_60s_stats IS
'用途：按 设备×指标 的 60s 窗口基础统计（count/sum/sumsq/min/max），用于快速计算均值/方差等。
使用方法：
  - 平均值 avg = sum / count
  - 方差 var ≈ sumsq / count - (avg^2)
示例：
  SELECT ts_bucket, count, sum, sumsq, v_min, v_max
  FROM public.mv_metric_60s_stats
  WHERE station_id=:sid AND device_id=:did AND metric_id=:mid
    AND ts_bucket >= ''2025-09-01T00:00:00Z'' AND ts_bucket < ''2025-09-01T02:00:00Z''
  ORDER BY ts_bucket;
典型联表：
  SELECT t.ts_bucket, t.count, t.sum, t.sumsq, t.v_min, t.v_max, s.name AS station_name, d.name AS device_name, m.metric_key
  FROM public.mv_metric_60s_stats t
  LEFT JOIN dim_stations s ON s.id = t.station_id
  LEFT JOIN dim_devices d ON d.id = t.device_id
  LEFT JOIN dim_metric_metadata m ON m.id = t.metric_id
  WHERE t.ts_bucket >= ''2025-09-01T00:00:00Z'' AND t.ts_bucket < ''2025-09-01T02:00:00Z'';
注意事项：
  - 60s 时间桶为 UTC；查询统一使用半开区间 [start,end)；
  - 统计仅含有效样本；异常/缺报已在上游规则中过滤。';

COMMENT ON COLUMN public.mv_metric_60s_stats.station_id IS '站点ID（dim_stations）';
COMMENT ON COLUMN public.mv_metric_60s_stats.device_id IS '设备ID（dim_devices）';
COMMENT ON COLUMN public.mv_metric_60s_stats.metric_id IS '指标ID（dim_metric_metadata）';
COMMENT ON COLUMN public.mv_metric_60s_stats.ts_bucket IS 'UTC 60秒时间桶（对齐到分钟）；查询统一使用 [start,end)';
COMMENT ON COLUMN public.mv_metric_60s_stats.count IS '60秒窗口内有效样本数';
COMMENT ON COLUMN public.mv_metric_60s_stats.sum IS '60秒窗口内数值之和';
COMMENT ON COLUMN public.mv_metric_60s_stats.sumsq IS '60秒窗口内数值平方和';
COMMENT ON COLUMN public.mv_metric_60s_stats.v_min IS '60秒窗口内最小值';
COMMENT ON COLUMN public.mv_metric_60s_stats.v_max IS '60秒窗口内最大值';

/* ===== quality_diagnosis_log ===== */
COMMENT ON TABLE public.quality_diagnosis_log IS
'用途：质量标注/诊断日志表。记录在给定时间窗与过滤条件下的过程信息与摘要/明细。
字段要点：中文采用内部术语——阶段(stage)/粒度(level)/诊断详略(diag_level)；diag_level 取值 off|brief|full；detail 为 JSONB 结构化细节；run_id 用于关联一次运行。
使用方法：按时间窗/站点/设备或 run_id 检索，支持定位问题窗口与规则命中情况。
示例：
  SELECT created_at, window_start, window_end, stage, level, message
  FROM public.quality_diagnosis_log
  WHERE window_start >= ''2025-09-01T00:00:00Z'' AND window_end < ''2025-09-01T01:00:00Z''
  ORDER BY created_at;
典型联表：
  SELECT q.created_at, q.stage, q.level, s.name AS station_name, d.name AS device_name
  FROM public.quality_diagnosis_log q
  LEFT JOIN dim_stations s ON s.id = q.station_id
  LEFT JOIN dim_devices d ON d.id = q.device_id
  WHERE q.window_start >= ''2025-09-01T00:00:00Z'' AND q.window_end < ''2025-09-01T01:00:00Z'';
注意事项：
  - 仅记录过程与摘要，不直接影响事实表；
  - full 级别会写入样例级细节，体量较大，仅在排障时开启。';

COMMENT ON COLUMN public.quality_diagnosis_log.id IS '主键（bigserial/uuidv7 等）';
COMMENT ON COLUMN public.quality_diagnosis_log.created_at IS '写入时间（UTC）';
COMMENT ON COLUMN public.quality_diagnosis_log.window_start IS '诊断窗口起（UTC，半开区间 [start,end)）';
COMMENT ON COLUMN public.quality_diagnosis_log.window_end IS '诊断窗口止（UTC，半开区间 [start,end)）';
COMMENT ON COLUMN public.quality_diagnosis_log.station_id IS '可选：站点ID';
COMMENT ON COLUMN public.quality_diagnosis_log.device_id IS '可选：设备ID';
COMMENT ON COLUMN public.quality_diagnosis_log.stage IS '流程阶段（如 compute/merge/mark 等）';
COMMENT ON COLUMN public.quality_diagnosis_log.level IS '阶段内级别/粒度（实现自定义）';
COMMENT ON COLUMN public.quality_diagnosis_log.message IS '摘要信息（文本）';
COMMENT ON COLUMN public.quality_diagnosis_log.detail IS '结构化细节（JSONB）';
COMMENT ON COLUMN public.quality_diagnosis_log.diag_level IS '诊断详略级别：off|brief|full';
COMMENT ON COLUMN public.quality_diagnosis_log.run_id IS '运行ID（用于一次调用/作业的关联）';

/* ===== mv_presence_1s_any（视图） ===== */
COMMENT ON VIEW public.mv_presence_1s_any IS
'用途：按 设备×秒 聚合“任一指标是否有样本”的覆盖视图；等价于在 mv_presence_1s 上按设备与秒做 ANY(present=1)。
使用方法：用于设备级覆盖率/缺口段识别等快速判断。
示例：
  SELECT ts_bucket, present
  FROM public.mv_presence_1s_any
  WHERE station_id=:sid AND device_id=:did
    AND ts_bucket >= ''2025-09-01T00:00:00Z'' AND ts_bucket < ''2025-09-01T01:00:00Z''
  ORDER BY ts_bucket;
典型联表：
  SELECT a.ts_bucket, a.present, s.name AS station_name, d.name AS device_name
  FROM public.mv_presence_1s_any a
  LEFT JOIN dim_stations s ON s.id = a.station_id
  LEFT JOIN dim_devices d ON d.id = a.device_id
  WHERE a.ts_bucket >= ''2025-09-01T00:00:00Z'' AND a.ts_bucket < ''2025-09-01T01:00:00Z'';
注意事项：
  - present：覆盖=1/缺失=0；
  - 判定口径：与 mv_presence_1s 一致（对任一指标存在有效样本即判为覆盖=1）；
  - ts_bucket 为 UTC 秒级时间桶，查询统一使用半开区间 [start,end)。';

COMMENT ON COLUMN public.mv_presence_1s_any.station_id IS '站点ID（dim_stations）';
COMMENT ON COLUMN public.mv_presence_1s_any.device_id IS '设备ID（dim_devices）';
COMMENT ON COLUMN public.mv_presence_1s_any.metric_id IS '指标ID（若以设备级汇总则可能为空）';
COMMENT ON COLUMN public.mv_presence_1s_any.ts_bucket IS 'UTC 秒级时间桶（对齐到整秒）；查询统一使用 [start,end)';
COMMENT ON COLUMN public.mv_presence_1s_any.present IS '覆盖：覆盖=1/缺失=0';

