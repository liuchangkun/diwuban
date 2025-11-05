\encoding UTF8
SET client_encoding = 'UTF8';

/*
函数名称: fn_running_state_1s
函数用途: 基于多指标（电流A/B/C、有功功率、频率）的综合标准分数，按 1 秒粒度判断是否“运行中”（is_running）。
输入参数:
  p_station_id  bigint        - 站点ID
  p_device_id   bigint        - 设备ID
  p_metric_ids  bigint[]      - 参与判定的指标ID数组（如 {pump_current_a,pump_current_b,pump_current_c,pump_active_power,pump_frequency} 的 id）
  p_start_ts    timestamptz   - 窗口起（UTC，含）
  p_end_ts      timestamptz   - 窗口止（UTC，含）
  p_run_z_thr   double precision - 运行阈值（综合标准分数 ≥ 此阈值判定为运行），建议 0.5~1.0 视场景调整
返回格式:
  ts_bucket     timestamptz   - 秒级 UTC 时间戳
  is_running    boolean       - 是否运行（true/false）
  composite_z   double precision - 当秒综合标准分数（可用于调参观测）
  z_count       integer       - 当秒参与计算的指标个数（可为 0，表示全部缺失）
  ramp          double precision - 当秒 |Δcomposite_z|（相邻秒差值的绝对值）
  jitter_3s     double precision - 近 3 秒的 composite_z 样本标准差（仅供观察）
使用示例:
  WITH ids AS (
    SELECT ARRAY_AGG(id ORDER BY metric_key) AS arr
    FROM public.dim_metric_config
    WHERE metric_key IN ('pump_current_a','pump_current_b','pump_current_c','pump_active_power','pump_frequency')
  )
  SELECT *
  FROM ids, LATERAL public.fn_running_state_1s(1,1,ids.arr,'2025-02-27T18:00:00Z','2025-02-27T19:00:00Z', 0.5)
  ORDER BY ts_bucket
  LIMIT 20;
创建时间: 2025-09-03
*/

CREATE OR REPLACE FUNCTION public.fn_running_state_1s(
  p_station_id  bigint,
  p_device_id   bigint,
  p_metric_ids  bigint[],
  p_start_ts    timestamptz,
  p_end_ts      timestamptz,
  p_run_z_thr   double precision
)
RETURNS TABLE (
  ts_bucket    timestamptz,
  is_running   boolean,
  composite_z  double precision,
  z_count      integer,
  ramp         double precision,
  jitter_3s    double precision
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
  /* 综合信号：可用指标的平均标准分数；记录参与个数 */
  SELECT ts_bucket,
         COUNT(z) FILTER (WHERE z IS NOT NULL) AS z_count,
         CASE WHEN COUNT(z) FILTER (WHERE z IS NOT NULL) = 0 THEN NULL
              ELSE AVG(z) FILTER (WHERE z IS NOT NULL) END AS composite_z
  FROM joined
  GROUP BY ts_bucket
), feat AS (
  SELECT ts_bucket,
         z_count,
         composite_z,
         ABS(composite_z - LAG(composite_z) OVER (ORDER BY ts_bucket)) AS ramp,
         CASE WHEN COUNT(composite_z) OVER (ORDER BY ts_bucket ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) >= 2
              THEN STDDEV_SAMP(composite_z) OVER (ORDER BY ts_bucket ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)
              ELSE NULL END AS jitter_3s
  FROM comp
)
SELECT ts_bucket,
       (composite_z IS NOT NULL AND composite_z >= p_run_z_thr) AS is_running,
       composite_z,
       z_count,
       ramp,
       jitter_3s
FROM feat
ORDER BY ts_bucket;
$fn$;

COMMENT ON FUNCTION public.fn_running_state_1s(bigint,bigint,bigint[],timestamptz,timestamptz,double precision) IS $DOC$
函数名称: fn_running_state_1s
函数用途: 基于多指标综合标准分数，按 1 秒粒度判断设备是否运行（is_running）。
输入参数: p_station_id bigint; p_device_id bigint; p_metric_ids bigint[]; p_start_ts timestamptz; p_end_ts timestamptz; p_run_z_thr double precision。
返回格式: (ts_bucket timestamptz, is_running boolean, composite_z double precision, z_count integer, ramp double precision, jitter_3s double precision)
创建时间: 2025-09-03
$DOC$;

