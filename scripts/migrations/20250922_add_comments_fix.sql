-- 增量修复：补齐视图列注释与 time_bucket 所有实际重载签名注释（仅注释，不改结构）
-- 口径：UTC/[start,end)；示例附过滤与 LIMIT 建议

/* ===== 修复：v_effective_metric_metadata 列注释 ===== */
COMMENT ON COLUMN public.v_effective_metric_metadata.station_id IS '站点 ID（维度键）';
COMMENT ON COLUMN public.v_effective_metric_metadata.device_id IS '设备 ID（维度键）';
COMMENT ON COLUMN public.v_effective_metric_metadata.metric_id IS '指标 ID（维度键）';
COMMENT ON COLUMN public.v_effective_metric_metadata.unit IS '计量单位（如 Pa、℃、%RH）';
COMMENT ON COLUMN public.v_effective_metric_metadata.resolution IS '采样/显示分辨率（数值最小步长）';
COMMENT ON COLUMN public.v_effective_metric_metadata.phys_min IS '物理下限（工程/机理边界，非质量阈值）';
COMMENT ON COLUMN public.v_effective_metric_metadata.phys_max IS '物理上限（工程/机理边界，非质量阈值）';
COMMENT ON COLUMN public.v_effective_metric_metadata.saturation_min IS '饱和下限（设备饱和/量程边界，非质量阈值）';
COMMENT ON COLUMN public.v_effective_metric_metadata.saturation_max IS '饱和上限（设备饱和/量程边界，非质量阈值）';

/* ===== 修复：public.time_bucket 全部已发现重载 ===== */
-- 通用说明：按固定宽度对时间轴进行对齐分桶；带 offset/origin/timezone 的变体用于对齐起点与时区。
-- 性能建议：聚合前先过滤时间窗与维度；必要时分批/分站执行；大结果集建议 LIMIT 抽样核对。

-- 整型/大整型/小整型变体（通常用于基于整数时间戳或序列的分桶）
COMMENT ON FUNCTION public.time_bucket(bigint, bigint) IS '用途：对整数时间戳按固定宽度分桶（单位与源数据一致）。参数：bucket_width bigint, ts bigint；返回：bigint（桶起点）。';
COMMENT ON FUNCTION public.time_bucket(bigint, bigint, "offset" bigint) IS '用途：带 offset 的整数分桶（整体平移）。参数：bucket_width bigint, ts bigint, offset bigint；返回：bigint。';
COMMENT ON FUNCTION public.time_bucket(integer, integer) IS '用途：对整数时间戳按固定宽度分桶（整型）。参数：bucket_width integer, ts integer；返回：integer。';
COMMENT ON FUNCTION public.time_bucket(integer, integer, "offset" integer) IS '用途：带 offset 的整数分桶（整型）。参数：bucket_width integer, ts integer, offset integer；返回：integer。';
COMMENT ON FUNCTION public.time_bucket(smallint, smallint) IS '用途：对整数时间戳按固定宽度分桶（小整型）。参数：bucket_width smallint, ts smallint；返回：smallint。';
COMMENT ON FUNCTION public.time_bucket(smallint, smallint, "offset" smallint) IS '用途：带 offset 的整数分桶（小整型）。参数：bucket_width smallint, ts smallint, offset smallint；返回：smallint。';

-- date 变体
COMMENT ON FUNCTION public.time_bucket(interval, date) IS '用途：按固定宽度对 date 分桶。参数：bucket_width interval, ts date；返回：date（桶起点）。';
COMMENT ON FUNCTION public.time_bucket(interval, date, "offset" interval) IS '用途：带 offset 的 date 分桶。参数：bucket_width interval, ts date, offset interval；返回：date。';
COMMENT ON FUNCTION public.time_bucket(interval, date, origin date) IS '用途：以 origin 为对齐原点的 date 分桶。参数：bucket_width interval, ts date, origin date；返回：date。';

-- timestamp with time zone 变体
COMMENT ON FUNCTION public.time_bucket(interval, timestamp with time zone) IS '用途：按固定宽度对 timestamptz 分桶（推荐）。参数：bucket_width interval, ts timestamptz；返回：timestamptz。';
COMMENT ON FUNCTION public.time_bucket(interval, timestamp with time zone, "offset" interval) IS '用途：带 offset 的 timestamptz 分桶。参数：bucket_width interval, ts timestamptz, offset interval；返回：timestamptz。';
COMMENT ON FUNCTION public.time_bucket(interval, timestamp with time zone, origin timestamp with time zone) IS '用途：以 origin 为对齐原点的 timestamptz 分桶。参数：bucket_width interval, ts timestamptz, origin timestamptz；返回：timestamptz。';
COMMENT ON FUNCTION public.time_bucket(interval, timestamp with time zone, timezone text, origin timestamp with time zone, "offset" interval) IS '用途：指定显示时区、原点与偏移的高级分桶；请确保与业务时区策略一致。参数：bucket_width interval, ts timestamptz, timezone text, origin timestamptz, offset interval；返回：timestamptz。';

-- timestamp without time zone 变体
COMMENT ON FUNCTION public.time_bucket(interval, timestamp without time zone) IS '用途：按固定宽度对 timestamp 分桶（无时区）；建议统一使用 timestamptz。参数：bucket_width interval, ts timestamp；返回：timestamp。';
COMMENT ON FUNCTION public.time_bucket(interval, timestamp without time zone, "offset" interval) IS '用途：带 offset 的 timestamp 分桶（无时区）。参数：bucket_width interval, ts timestamp, offset interval；返回：timestamp。';
COMMENT ON FUNCTION public.time_bucket(interval, timestamp without time zone, origin timestamp without time zone) IS '用途：以 origin 为对齐原点的 timestamp 分桶（无时区）。参数：bucket_width interval, ts timestamp, origin timestamp；返回：timestamp。';

