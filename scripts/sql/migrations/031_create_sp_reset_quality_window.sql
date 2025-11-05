BEGIN;

-- 重置窗口内事实行的质量标注字段（幂等）：将 quality_status/type/meta 置 NULL
-- 仅限给定时间窗，可选按站/设备过滤；避免误清全量
CREATE OR REPLACE PROCEDURE public.sp_reset_quality_window(
  IN p_start timestamptz,
  IN p_end   timestamptz,
  IN p_station_id bigint DEFAULT NULL,
  IN p_device_id  bigint DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
  UPDATE public.fact_measurements f
  SET quality_status = 0,         -- 列为 NOT NULL，用 0 还原“未标注”
      quality_type   = NULL,
      quality_meta   = NULL,
      quality_codes  = '{}'::int[]
  WHERE f.ts_bucket>=p_start AND f.ts_bucket<p_end
    AND (p_station_id IS NULL OR f.station_id=p_station_id)
    AND (p_device_id  IS NULL OR f.device_id=p_device_id);
END;
$$;

COMMENT ON PROCEDURE public.sp_reset_quality_window(timestamptz, timestamptz, bigint, bigint)
IS '重置给定时间窗内的质量标注（quality_* 置 NULL），可选按站/设备过滤。';

COMMIT;

