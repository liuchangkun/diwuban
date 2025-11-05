-- =====================================================================
-- 迁移脚本：删除 mv_presence_1s 表
-- 用途：彻底删除 mv_presence_1s 表及其相关依赖
-- 原因：该表已被 metrics_presence_per_second_device 表完全替代
-- 创建日期：2025-11-04
-- =====================================================================

BEGIN;

-- 步骤1：简化 mv_presence_1s_any 视图（移除对 mv_presence_1s 的依赖）
DROP VIEW IF EXISTS public.mv_presence_1s_any;

CREATE OR REPLACE VIEW public.mv_presence_1s_any AS
SELECT mpps.station_id,
       mpps.device_id,
       mc.id AS metric_id,
       mpps.ts_second AS ts_bucket,
       (1)::smallint AS present
FROM public.metrics_presence_per_second_device mpps
CROSS JOIN LATERAL unnest(mpps.available_metrics) u(metric_key)
JOIN public.dim_metric_config mc ON mc.metric_key = u.metric_key;

COMMENT ON VIEW public.mv_presence_1s_any IS '1秒存在性聚合视图

用途：聚合1秒级指标存在性，支持快速查询

数据来源：metrics_presence_per_second_device（展开 available_metrics 数组）

使用场景：数据完整性监控、覆盖率统计

使用示例：
  SELECT * FROM mv_presence_1s_any
  WHERE device_id = 121
    AND ts_bucket >= ''2025-09-01T00:00:00Z''::timestamptz
  ORDER BY ts_bucket;

注意事项：
  - 本视图已简化，仅基于 metrics_presence_per_second_device 表
  - mv_presence_1s 表已废弃并删除
';

-- 步骤2：修改 sp_refresh_mv_running_presence 存储过程（移除对 mv_presence_1s 的写入）
CREATE OR REPLACE PROCEDURE public.sp_refresh_mv_running_presence(
  IN p_start timestamptz,
  IN p_end   timestamptz,
  IN p_station_id bigint DEFAULT NULL,
  IN p_device_id  bigint DEFAULT NULL
)
LANGUAGE sql
AS $procedure$
  -- 运行态（device_running==1）
  INSERT INTO public.mv_device_running_1s(station_id, device_id, ts_bucket, running)
  SELECT f.station_id, f.device_id, f.ts_bucket, 1
  FROM public.fact_measurements f
  JOIN public.dim_metric_config mc ON mc.id=f.metric_id AND mc.metric_key='device_running'
  WHERE f.ts_bucket>=p_start AND f.ts_bucket<p_end
    AND (p_station_id IS NULL OR f.station_id=p_station_id)
    AND (p_device_id  IS NULL OR f.device_id=p_device_id)
    AND f.value=1
  ON CONFLICT DO NOTHING;
$procedure$;

COMMENT ON PROCEDURE public.sp_refresh_mv_running_presence(timestamptz, timestamptz, bigint, bigint) IS '刷新运行状态物化视图

用途：
  刷新 mv_device_running_1s 物化视图

输入参数：
  - p_start (timestamptz)：开始时间（UTC）
  - p_end (timestamptz)：结束时间（UTC）
  - p_station_id (bigint, DEFAULT NULL)：泵站ID过滤
  - p_device_id (bigint, DEFAULT NULL)：设备ID过滤

返回值：
  - void

业务逻辑：
  - 删除既有窗口数据
  - 重新计算运行状态
  - 写入物化视图

使用场景：
  - 物化视图增量刷新
  - 数据修正后重新计算

使用示例：
  -- 刷新全部数据
  CALL sp_refresh_mv_running_presence(''2025-09-01T00:00:00Z''::timestamptz, ''2025-09-02T00:00:00Z''::timestamptz, NULL, NULL);

注意事项：
  - 会删除既有窗口的数据
  - 建议在数据修正后执行
  - mv_presence_1s 表已废弃，不再刷新
';

-- 步骤3：删除 mv_presence_1s 表
DROP TABLE IF EXISTS public.mv_presence_1s;

-- 步骤4：验证删除结果
DO $$
BEGIN
    -- 验证表已删除
    IF to_regclass('public.mv_presence_1s') IS NOT NULL THEN
        RAISE EXCEPTION 'mv_presence_1s 表删除失败';
    END IF;
    
    -- 验证视图仍然存在
    IF to_regclass('public.mv_presence_1s_any') IS NULL THEN
        RAISE EXCEPTION 'mv_presence_1s_any 视图不存在';
    END IF;
    
    RAISE NOTICE '[验证] mv_presence_1s 表已成功删除';
    RAISE NOTICE '[验证] mv_presence_1s_any 视图已简化';
    RAISE NOTICE '[验证] sp_refresh_mv_running_presence 存储过程已更新';
END $$;

COMMIT;

