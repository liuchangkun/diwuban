\encoding UTF8
SET client_encoding = 'UTF8';

/*
函数名称: fn_startstop_windows
函数用途: 基于多指标（电流A/B/C、有功功率、频率）的综合信号，按 1 秒步长识别启停/非稳态窗口，支持软启、变频等复杂场景。
输入参数:
  p_station_id  bigint        - 站点ID
  p_device_id   bigint        - 设备ID
  p_metric_ids  bigint[]      - 参与判定的指标ID数组（例如：{current_a,current_b,current_c,active_power,frequency} 对应的 metric_id）
  p_start_ts    timestamptz   - 窗口起（UTC，含）
  p_end_ts      timestamptz   - 窗口止（UTC，含）
  p_ramp_thr    double precision - 斜率阈值（基于标准分数后的单位/秒）
  p_jitter_thr  double precision - 抖动阈值（基于标准分数后的滚动波动）
  p_startup_cooldown_sec   integer - 启动冷却期（秒）
  p_shutdown_cooldown_sec  integer - 停止冷却期（秒）
  p_hysteresis_sec         integer - 滞回窗口（秒），用于合并相邻窗口与抑制抖动
返回格式:
  win_id       bigint        - 窗口编号
  win_type     text          - startup|shutdown|startstop
  win_start_ts timestamptz   - 窗口开始（UTC）
  win_end_ts   timestamptz   - 窗口结束（UTC）
使用示例:
  SELECT * FROM public.fn_startstop_windows(1,1,ARRAY[101,102,103,201,301], '2025-09-01T00:00:00Z','2025-09-01T01:00:00Z', 0.5, 0.8, 10, 10, 5);
创建时间: 2025-09-03
*/

CREATE OR REPLACE FUNCTION public.fn_startstop_windows(
  p_station_id  bigint,
  p_device_id   bigint,
  p_metric_ids  bigint[],
  p_start_ts    timestamptz,
  p_end_ts      timestamptz,
  p_ramp_thr    double precision,
  p_jitter_thr  double precision,
  p_startup_cooldown_sec   integer,
  p_shutdown_cooldown_sec  integer,
  p_hysteresis_sec         integer
)
RETURNS TABLE (
  win_id       bigint,
  win_type     text,
  win_start_ts timestamptz,
  win_end_ts   timestamptz
)
LANGUAGE sql
STABLE
AS $fn$
WITH raw AS (
  SELECT fm.ts_bucket, fm.metric_id, fm.value::double precision AS value
  FROM public.fact_measurements fm
  WHERE fm.station_id = p_station_id
    AND fm.device_id  = p_device_id
    AND fm.metric_id = ANY(p_metric_ids)
    AND fm.ts_bucket >= p_start_ts AND fm.ts_bucket < p_end_ts
), stats AS (
  /* 每个指标在窗口内的均值/标准差（标准分数归一化，避免不同单位直接相加） */
  SELECT metric_id, avg(value) AS mu, stddev_samp(value) AS sigma
  FROM raw
  GROUP BY metric_id
), series AS (
  SELECT generate_series(p_start_ts, p_end_ts - INTERVAL '1 second', INTERVAL '1 second')::timestamptz AS ts_bucket
), joined AS (
  /* 按秒对齐，按可用指标计算标准分数 */
  SELECT s.ts_bucket,
         r.metric_id,
         CASE WHEN st.sigma IS NULL OR st.sigma = 0 THEN NULL
              ELSE (r.value - st.mu) / st.sigma END AS z
  FROM series s
  LEFT JOIN raw r ON r.ts_bucket = s.ts_bucket
  LEFT JOIN stats st ON st.metric_id = r.metric_id
), comp AS (
  /* 综合信号：可用指标的平均标准分数；若某秒无任何指标，则为 NULL */
  SELECT ts_bucket,
         CASE WHEN count(z) FILTER (WHERE z IS NOT NULL) = 0 THEN NULL
              ELSE avg(z) FILTER (WHERE z IS NOT NULL) END AS composite
  FROM joined
  GROUP BY ts_bucket
), feat AS (
  /* ramp: 每秒差分的绝对值；jitter: 近3秒的标准差（仅对非空值计算） */
  SELECT ts_bucket,
         composite,
         abs(composite - lag(composite) OVER (ORDER BY ts_bucket)) AS ramp,
         CASE WHEN count(composite) OVER (ORDER BY ts_bucket ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) >= 2
              THEN stddev_samp(composite) OVER (ORDER BY ts_bucket ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)
              ELSE NULL END AS jitter
  FROM comp
), unstable AS (
  /* 判定非稳态：ramp > 阈值 或 jitter > 阈值；要求与前值可比（NULL 则不命中） */
  SELECT ts_bucket,
         composite,
         ( (ramp IS NOT NULL AND ramp > p_ramp_thr)
           OR (jitter IS NOT NULL AND jitter > p_jitter_thr) ) AS is_unstable
  FROM feat
), marks AS (
  /* 连续 is_unstable 片段分组 */
  SELECT ts_bucket,
         is_unstable,
         (ROW_NUMBER() OVER (ORDER BY ts_bucket)
          - ROW_NUMBER() OVER (PARTITION BY is_unstable ORDER BY ts_bucket))::bigint AS grp
  FROM unstable
), wins AS (
  SELECT grp,
         MIN(ts_bucket) AS win_start,
         MAX(ts_bucket) AS win_end
  FROM marks
  WHERE is_unstable
  GROUP BY grp
), expanded AS (
  /* 冷却期扩展：窗口前扩 p_startup_cooldown_sec、后扩 p_shutdown_cooldown_sec */
  SELECT ROW_NUMBER() OVER (ORDER BY win_start) AS id0,
         win_start - make_interval(secs => GREATEST(0,p_startup_cooldown_sec)) AS start0,
         win_end   + make_interval(secs => GREATEST(0,p_shutdown_cooldown_sec)) AS end0
  FROM wins
), ordered AS (
  SELECT id0, start0, end0
  FROM expanded
  ORDER BY start0, end0
), with_prev AS (
  /* 计算相邻窗口的间隙与是否需要开新组（避免嵌套窗口函数） */
  SELECT o1.id0, o1.start0, o1.end0,
         LAG(o1.end0) OVER (ORDER BY o1.start0, o1.end0) AS prev_end,
         CASE
           WHEN LAG(o1.end0) OVER (ORDER BY o1.start0, o1.end0) IS NULL THEN 0
           WHEN o1.start0 <= LAG(o1.end0) OVER (ORDER BY o1.start0, o1.end0) + make_interval(secs=>GREATEST(0,p_hysteresis_sec)) THEN 0
           ELSE 1
         END AS new_group
  FROM ordered o1
), grouped AS (
  SELECT id0, start0, end0,
         SUM(new_group) OVER (ORDER BY start0, end0 ROWS UNBOUNDED PRECEDING) AS grp
  FROM with_prev
), merged AS (
  /* 基于计算得到的 grp 合并相邻/重叠窗口 */
  SELECT MIN(id0) AS id0,
         MIN(start0) AS start0,
         MAX(end0) AS end0
  FROM grouped
  GROUP BY grp
), typed AS (
  /* 依据综合信号在窗口内的首末差判定类型 */
  SELECT ROW_NUMBER() OVER (ORDER BY m.start0) AS win_id,
         CASE
           WHEN (SELECT c2.composite FROM comp c2 WHERE c2.ts_bucket >= m.start0 ORDER BY c2.ts_bucket ASC LIMIT 1) IS NULL
             OR (SELECT c3.composite FROM comp c3 WHERE c3.ts_bucket <= m.end0   ORDER BY c3.ts_bucket DESC LIMIT 1) IS NULL
           THEN 'startstop'
           ELSE (
             CASE WHEN (
               (SELECT c3.composite FROM comp c3 WHERE c3.ts_bucket <= m.end0   ORDER BY c3.ts_bucket DESC LIMIT 1)
               -
               (SELECT c2.composite FROM comp c2 WHERE c2.ts_bucket >= m.start0 ORDER BY c2.ts_bucket ASC  LIMIT 1)
             ) > 0 THEN 'startup'
             WHEN (
               (SELECT c3.composite FROM comp c3 WHERE c3.ts_bucket <= m.end0   ORDER BY c3.ts_bucket DESC LIMIT 1)
               -
               (SELECT c2.composite FROM comp c2 WHERE c2.ts_bucket >= m.start0 ORDER BY c2.ts_bucket ASC  LIMIT 1)
             ) < 0 THEN 'shutdown'
             ELSE 'startstop' END
           )
           END AS win_type,
         m.start0 AS win_start_ts,
         m.end0   AS win_end_ts
  FROM merged m
)
SELECT * FROM typed
ORDER BY win_start_ts;
$fn$;

COMMENT ON FUNCTION public.fn_startstop_windows(bigint,bigint,bigint[],timestamptz,timestamptz,double precision,double precision,integer,integer,integer) IS $DOC$
函数名称: fn_startstop_windows
函数用途: 基于多指标（电流A/B/C、有功功率、频率）的综合信号，按 1 秒步长识别启停/非稳态窗口，支持软启、变频等复杂场景。
输入参数: p_station_id bigint; p_device_id bigint; p_metric_ids bigint[]; p_start_ts timestamptz; p_end_ts timestamptz; p_ramp_thr double precision; p_jitter_thr double precision; p_startup_cooldown_sec integer; p_shutdown_cooldown_sec integer; p_hysteresis_sec integer。
返回格式: (win_id bigint, win_type text, win_start_ts timestamptz, win_end_ts timestamptz)
使用示例: SELECT * FROM public.fn_startstop_windows(1,1,ARRAY[101,102,103,201,301],'2025-09-01T00:00:00Z','2025-09-01T01:00:00Z',0.5,0.8,10,10,5);
创建时间: 2025-09-03
$DOC$;

