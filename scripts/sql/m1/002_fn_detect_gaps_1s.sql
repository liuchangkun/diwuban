\encoding UTF8
SET client_encoding = 'UTF8';

/*
函数名称: fn_detect_gaps_1s
函数用途: 基于 1 秒步长 UTC 时间序列与事实表，识别窗口内的连续缺口段，输出缺口起止与时长，并给出缺口分类（short/medium/long）。
输入参数:
  p_station_id bigint      - 站点ID（维表 dim_stations.id）
  p_device_id  bigint      - 设备ID（维表 dim_devices.id）
  p_metric_id  bigint      - 指标ID（维表 dim_metric_config.id）
  p_start_ts   timestamptz - 窗口起（UTC，含）
  p_end_ts     timestamptz - 窗口止（UTC，含）
  p_max_gap_sec integer    - 缺口分类的阈值（秒）；>p_max_gap_sec 视为 long，<=p_max_gap_sec/3 视为 short，其余为 medium
返回格式:
  gap_id        bigint         - 缺口段编号（窗口内递增）
  gap_start_ts  timestamptz    - 缺口开始时间（UTC，秒对齐）
  gap_end_ts    timestamptz    - 缺口结束时间（UTC，秒对齐）
  gap_len_sec   integer        - 缺口长度（秒）
  gap_class     text           - 缺口分类: short|medium|long（依据 p_max_gap_sec）
使用示例:
  SELECT * FROM public.fn_detect_gaps_1s(1,1,1,'2025-09-01T00:00:00Z','2025-09-01T00:05:00Z', 300);
创建时间: 2025-09-03
*/

CREATE OR REPLACE FUNCTION public.fn_detect_gaps_1s(
  p_station_id  bigint,
  p_device_id   bigint,
  p_metric_id   bigint,
  p_start_ts    timestamptz,
  p_end_ts      timestamptz,
  p_max_gap_sec integer
)
RETURNS TABLE (
  gap_id       bigint,
  gap_start_ts timestamptz,
  gap_end_ts   timestamptz,
  gap_len_sec  integer,
  gap_class    text
)
LANGUAGE sql
STABLE
AS $fn$
/* 基于事实点的差分检测：避免大窗口 generate_series 带来的排序与临时文件开销 */
WITH points AS (
  /* 取窗口内的实际秒点 */
  SELECT fm.ts_bucket
  FROM public.fact_measurements fm
  WHERE fm.station_id = p_station_id
    AND fm.device_id  = p_device_id
    AND fm.metric_id  = p_metric_id
    AND fm.ts_bucket >= p_start_ts AND fm.ts_bucket < p_end_ts
  UNION ALL
  /* 起始边界锚点（起点-1s） */
  SELECT (p_start_ts - INTERVAL '1 second')
  UNION ALL
  /* 结束边界锚点（终点+1s） */
  SELECT (p_end_ts + INTERVAL '1 second')
), ordered AS (
  SELECT ts_bucket,
         LEAD(ts_bucket) OVER (ORDER BY ts_bucket) AS next_ts
  FROM (
    SELECT DISTINCT ts_bucket FROM points
  ) t
), gaps AS (
  /* 相邻点之间大于 1s 的间隔即为缺口段 */
  SELECT (ts_bucket + INTERVAL '1 second') AS gap_start_ts,
         (next_ts  - INTERVAL '1 second') AS gap_end_ts,
         EXTRACT(EPOCH FROM (next_ts - ts_bucket))::integer - 1 AS gap_len_sec
  FROM ordered
  WHERE next_ts IS NOT NULL
    AND next_ts > ts_bucket + INTERVAL '1 second'
)
SELECT ROW_NUMBER() OVER (ORDER BY g.gap_start_ts) AS gap_id,
       g.gap_start_ts,
       g.gap_end_ts,
       g.gap_len_sec,
       CASE
         WHEN g.gap_len_sec > p_max_gap_sec THEN 'long'
         WHEN g.gap_len_sec <= GREATEST(1, p_max_gap_sec/3) THEN 'short'
         ELSE 'medium'
       END AS gap_class
FROM gaps g
ORDER BY g.gap_start_ts;
$fn$;

COMMENT ON FUNCTION public.fn_detect_gaps_1s(bigint,bigint,bigint,timestamptz,timestamptz,integer) IS $DOC$
函数名称: fn_detect_gaps_1s
函数用途: 基于 1 秒步长 UTC 时间序列与事实表，识别窗口内的连续缺口段，输出缺口起止与时长，并给出缺口分类（short/medium/long）。
输入参数:
  p_station_id bigint; p_device_id bigint; p_metric_id bigint; p_start_ts timestamptz; p_end_ts timestamptz; p_max_gap_sec integer。
返回格式: (gap_id bigint, gap_start_ts timestamptz, gap_end_ts timestamptz, gap_len_sec integer, gap_class text)
使用示例: SELECT * FROM public.fn_detect_gaps_1s(1,1,1,'2025-09-01T00:00:00Z','2025-09-01T00:05:00Z',300);
创建时间: 2025-09-03
$DOC$;

