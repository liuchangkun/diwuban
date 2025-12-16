\encoding UTF8
SET client_encoding = 'UTF8';

/*
函数名称: fn_startstop_windows（重写）
函数用途: 仅传 device_id 与时间窗，自动读取 device_running_thresholds，并从 fact_measurements 获取信号，返回 1 秒粒度的运行状态。
重要变更: 与旧版不同，现函数返回逐秒状态而非“窗口段”。
输入参数:
  p_device_id  bigint           - 设备ID（dim_devices.id）
  p_start_ts   timestamptz      - 窗口起（UTC，含）
  p_end_ts     timestamptz      - 窗口止（UTC，含）
返回字段:
  ts_bucket    timestamptz      - 秒级 UTC 时间戳
  is_running   boolean          - 是否运行（滞回判定 + 缺报延续）
  max_i        double precision - 三相电流最大值（A）
  p            double precision - 有功功率（kW 或设备单位）
  f            double precision - 频率（Hz）
  source       text             - 判定来源：det（确定性）、hold（缺报延续）
创建时间: 2025-09-03
*/

CREATE OR REPLACE FUNCTION public.fn_startstop_windows(
  p_device_id  bigint,
  p_start_ts   timestamptz,
  p_end_ts     timestamptz
)
RETURNS TABLE (
  ts_bucket  timestamptz,
  is_running boolean,
  max_i      double precision,
  p          double precision,
  f          double precision,
  source     text
)
LANGUAGE sql
STABLE
AS $fn$
  SELECT *
  FROM public.fn_running_state_1s(
    /* 自动解析 station_id */
    (SELECT d.station_id FROM public.dim_devices d WHERE d.id = p_device_id),
    p_device_id,
    p_start_ts,
    p_end_ts
  );
$fn$;

COMMENT ON FUNCTION public.fn_startstop_windows(bigint,timestamptz,timestamptz) IS $DOC$
函数名称: fn_startstop_windows（重写）
函数用途: 仅传 device_id 与时间窗，返回逐秒运行状态（1s 间隔）。阈值来自 device_running_thresholds；信号来自 fact_measurements。
重要变更: 该函数不再返回窗口段，如需窗口段请联系使用逐秒结果做 islands 聚合。
$DOC$;

