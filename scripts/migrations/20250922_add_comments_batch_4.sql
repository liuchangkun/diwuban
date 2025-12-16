-- 迁移（批次四）：为视图/字典补充中文注释（仅注释，不改结构）
-- 覆盖：public.v_effective_metric_rules、public.v_effective_metric_metadata、public.quality_code_dict
-- 口径：UTC 与 [start,end) 半开区间；与前两批保持一致；示例加入典型维表联接

/* ===== v_effective_metric_metadata ===== */
COMMENT ON VIEW public.v_effective_metric_metadata IS
'用途：设备×指标的“有效元数据”视图，用于获取单位、分辨率与物理/饱和区间等。
典型联表：与 dim_stations、dim_devices、dim_metric_metadata 进行 LEFT JOIN 获取名称/层级。
示例：
  SELECT m.station_id, m.device_id, m.metric_id, mm.metric_name, m.unit, m.resolution
  FROM public.v_effective_metric_metadata m
  LEFT JOIN dim_metric_metadata mm USING (metric_id)
  WHERE m.station_id = :sid AND m.device_id = :did AND m.metric_id = :mid;
注意事项：
  - 建议按站/设/指标过滤，避免全表扫描；
  - 单位与区间用于前置检测与报表解释，不直接代表质量判定结果。';

COMMENT ON COLUMN public.v_effective_metric_metadata.station_id IS '站点 ID（维度键）';
COMMENT ON COLUMN public.v_effective_metric_metadata.device_id IS '设备 ID（维度键）';
COMMENT ON COLUMN public.v_effective_metric_metadata.metric_id IS '指标 ID（维度键）';
COMMENT ON COLUMN public.v_effective_metric_metadata.unit IS '计量单位（如 Pa、℃、%RH）';
COMMENT ON COLUMN public.v_effective_metric_metadata.resolution IS '采样/显示分辨率（数值最小步长）';
COMMENT ON COLUMN public.v_effective_metric_metadata.phys_min IS '物理下限（工程/机理边界，非质量阈值）';
COMMENT ON COLUMN public.v_effective_metric_metadata.phys_max IS '物理上限（工程/机理边界，非质量阈值）';
COMMENT ON COLUMN public.v_effective_metric_metadata.saturation_min IS '饱和下限（设备饱和/量程边界，非质量阈值）';
COMMENT ON COLUMN public.v_effective_metric_metadata.saturation_max IS '饱和上限（设备饱和/量程边界，非质量阈值）';

/* ===== v_effective_metric_rules ===== */
COMMENT ON VIEW public.v_effective_metric_rules IS
'用途：设备×指标的“有效规则”视图，提供数值范围、突变/斜率、持平等质量检测参数。
典型联表：与 dim_* 维表或 v_effective_metric_metadata 联表，生成质量/报表使用的解释性信息。
示例：
  SELECT r.station_id, r.device_id, r.metric_id,
         r.value_min, r.value_max, r.spike_abs, r.roc_abs, r.roc_ratio,
         r.flatline_eps, r.flatline_delta, r.flatline_secs
  FROM public.v_effective_metric_rules r
  WHERE r.station_id = :sid AND r.device_id = :did AND r.metric_id = :mid;
注意事项：
  - 这些规则参数用于质量判定过程（如缺陷筛查、告警前置过滤），并非直接用于报表展示；
  - 具体阈值口径以运行时配置与任务参数为准。';

COMMENT ON COLUMN public.v_effective_metric_rules.station_id IS '站点 ID（维度键）';
COMMENT ON COLUMN public.v_effective_metric_rules.device_id IS '设备 ID（维度键）';
COMMENT ON COLUMN public.v_effective_metric_rules.metric_id IS '指标 ID（维度键）';
COMMENT ON COLUMN public.v_effective_metric_rules.value_min IS '允许的数值最小值（越界可能判定为异常）';
COMMENT ON COLUMN public.v_effective_metric_rules.value_max IS '允许的数值最大值（越界可能判定为异常）';
COMMENT ON COLUMN public.v_effective_metric_rules.spike_abs IS '突变绝对阈值（相邻样本差的上限）';
COMMENT ON COLUMN public.v_effective_metric_rules.roc_abs IS '斜率绝对阈值（单位时间变化量上限）';
COMMENT ON COLUMN public.v_effective_metric_rules.roc_ratio IS '斜率相对阈值（相对前值的变化比例上限）';
COMMENT ON COLUMN public.v_effective_metric_rules.flatline_eps IS '持平判定 epsilon（允许微小抖动）';
COMMENT ON COLUMN public.v_effective_metric_rules.flatline_delta IS '持平判定最小变化量阈值';
COMMENT ON COLUMN public.v_effective_metric_rules.flatline_secs IS '持平判定最小时长（秒）';

/* ===== quality_code_dict ===== */
COMMENT ON TABLE public.quality_code_dict IS
'用途：质量代码字典（101–751 等），用于质量标注/诊断输出的统一编码与中文释义。
典型联表：与 quality_diagnosis_log、mv_* 统计或报表查询联接，用于把 code 映射为中文文本与类别。
示例：
  SELECT q.ts, q.station_id, q.device_id, q.metric_id, q.code, d.label_zh, d.category
  FROM public.quality_diagnosis_log q
  LEFT JOIN public.quality_code_dict d ON q.code = d.code
  WHERE q.station_id = :sid AND q.device_id = :did AND q.metric_id = :mid
    AND q.ts >= ''2025-09-01T00:00:00Z'' AND q.ts < ''2025-09-02T00:00:00Z''
  ORDER BY q.ts
  LIMIT 200;
注意事项：
  - code 的语义与分组（category/severity）以此表为准；
  - 覆盖 present 口径在覆盖相关对象中为：覆盖=1/缺失=0（缺秒=无采样；空值=有样本但 value 为 NULL；拒绝样本=样本存在但被质量/过滤规则排除，不计入覆盖）。';

