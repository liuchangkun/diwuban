\encoding UTF8
SET client_encoding = 'UTF8';

/*
视图名称: v_coverage_gaps_1s
视图用途: 直接展示按对象的 1 秒覆盖缺口（开始、结束、时长、分类），用于质量体检和抽查。
数据来源: fn_detect_gaps_1s（函数）
字段映射:
  - station_id/device_id/metric_id: 通过查询侧传入；视图本身不内置对象过滤
  - gap_start_ts/gap_end_ts/gap_len_sec/gap_class: 来自函数返回
过滤逻辑: 建议在查询时追加 WHERE 条件传入对象与时间窗口、max_gap_sec
创建时间: 2025-09-03
*/

-- 说明：PostgreSQL 视图不支持参数。该视图提供调用模板与字段口径。
-- 使用方式示例：
-- SELECT * FROM public.v_coverage_gaps_1s WHERE station_id=1 AND device_id=1 AND metric_id=1 AND start_ts='2025-09-01T00:00:00Z' AND end_ts='2025-09-01T01:00:00Z' AND max_gap_sec=300;

CREATE OR REPLACE VIEW public.v_coverage_gaps_1s AS
SELECT NULL::bigint  AS station_id,
       NULL::bigint  AS device_id,
       NULL::bigint  AS metric_id,
       NULL::timestamptz AS start_ts,
       NULL::timestamptz AS end_ts,
       NULL::integer AS max_gap_sec,
       NULL::bigint  AS gap_id,
       NULL::timestamptz AS gap_start_ts,
       NULL::timestamptz AS gap_end_ts,
       NULL::integer AS gap_len_sec,
       NULL::text    AS gap_class
WHERE false;

COMMENT ON VIEW public.v_coverage_gaps_1s IS $DOC$
视图名称: v_coverage_gaps_1s
视图用途: 基于 fn_detect_gaps_1s 的输出口径，提供查询模板（视图本身不带参数，使用时请参考注释中示例SQL）
创建时间: 2025-09-03
$DOC$;

