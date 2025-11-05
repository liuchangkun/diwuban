\encoding UTF8
SET client_encoding = 'UTF8';

/*
视图名称: v_startstop_windows
视图用途: 展示启停窗口的统一口径（基于多指标综合信号）。
数据来源: fn_startstop_windows（函数）
字段映射与说明:
  - station_id/device_id/metric_ids（文本展示）
  - win_type, win_start_ts, win_end_ts: 来自函数返回
过滤逻辑: 建议在查询时追加 WHERE 条件传入对象与时间窗口、阈值、冷却期、滞回参数
创建时间: 2025-09-03
*/

-- 说明：视图仅提供字段口径。PostgreSQL 视图不支持参数。
CREATE OR REPLACE VIEW public.v_startstop_windows AS
SELECT NULL::bigint AS station_id,
       NULL::bigint AS device_id,
       NULL::text   AS metric_ids_text,
       NULL::text   AS win_type,
       NULL::timestamptz AS win_start_ts,
       NULL::timestamptz AS win_end_ts
WHERE false;

COMMENT ON VIEW public.v_startstop_windows IS $DOC$
视图名称: v_startstop_windows
视图用途: 展示启停窗口的统一口径（字段定义与函数一致；使用时请参照注释中示例SQL携带参数调用函数）
创建时间: 2025-09-03
$DOC$;

