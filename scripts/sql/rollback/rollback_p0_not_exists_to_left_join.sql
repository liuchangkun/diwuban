-- ============================================================================
-- P0 优化回滚脚本：NOT EXISTS → LEFT JOIN
-- ============================================================================
-- 创建时间：2025-11-06
-- 用途：回滚 P0 优化（将 LEFT JOIN 改回 NOT EXISTS）
-- 使用方法：psql -U postgres -d your_database -f rollback_p0_not_exists_to_left_join.sql
-- ============================================================================

BEGIN;

-- 说明：本脚本将恢复存储过程中的 2 处修改
-- 修改1：第68行 - mv_device_running_1s 注入（LEFT JOIN → NOT EXISTS）
-- 修改2：第1099行 - 规则503 快速通道（COUNT(*) → NOT EXISTS）

CREATE OR REPLACE PROCEDURE public.sp_mark_quality_window_vfast(
  IN p_start timestamptz,
  IN p_end   timestamptz,
  IN p_station_id bigint DEFAULT NULL,
  IN p_device_id  bigint DEFAULT NULL,
  IN p_codes int[] DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_running_id bigint;
  v_pf_id      bigint;
  v_power_id   bigint;
  v_flow_id    bigint;
  v_cur_a_id   bigint;
  v_cur_b_id   bigint;
  v_cur_c_id   bigint;
  v_volt_a_id  bigint;
  v_volt_b_id  bigint;
  v_volt_c_id  bigint;
  v_thr        numeric := 0.15; -- 三相不平衡默认阈值
  v_rc         bigint := 0;     -- rows affected
  v_cnt        bigint := 0;     -- temp counter
  v_t          timestamptz;     -- stage timer
BEGIN
  -- 放宽本事务资源限制，专用于大窗口
  PERFORM set_config('statement_timeout','0', true); -- 0 = no timeout
  PERFORM set_config('work_mem','256MB', true);

  -- 窗口临时表
  v_t := clock_timestamp();
  DROP TABLE IF EXISTS fwin;
  CREATE TEMP TABLE fwin ON COMMIT DROP AS
  SELECT id, station_id, device_id, metric_id, ts_bucket, value, COALESCE(quality_status,0) AS qs
  FROM public.fact_measurements
  WHERE ts_bucket>=p_start AND ts_bucket<p_end
    AND (p_station_id IS NULL OR station_id=p_station_id)
    AND (p_device_id  IS NULL OR device_id=p_device_id);
  CREATE INDEX ON fwin(station_id, device_id, ts_bucket);
  CREATE INDEX ON fwin(metric_id, ts_bucket);
  CREATE INDEX ON fwin(station_id, device_id, ts_bucket, metric_id, value);
  INSERT INTO public.quality_profile_log(window_start, window_end, station_id, device_id, stage, duration_ms, rows_affected, details)
  VALUES (p_start, p_end, p_station_id, p_device_id, 'fwin_build', EXTRACT(MILLISECOND FROM (clock_timestamp()-v_t)), (SELECT COUNT(*) FROM fwin), NULL);

  -- 解析关键 metric_id
  SELECT id INTO v_running_id FROM public.dim_metric_config WHERE metric_key='device_running';
  SELECT id INTO v_pf_id      FROM public.dim_metric_config WHERE metric_key IN ('pump_power_factor','power_factor');
  SELECT id INTO v_power_id   FROM public.dim_metric_config WHERE metric_key IN ('pump_active_power','active_power','power');
  SELECT id INTO v_flow_id    FROM public.dim_metric_config WHERE metric_key IN ('pump_flow','flow');
  SELECT id INTO v_cur_a_id   FROM public.dim_metric_config WHERE metric_key='current_a';
  SELECT id INTO v_cur_b_id   FROM public.dim_metric_config WHERE metric_key='current_b';
  SELECT id INTO v_cur_c_id   FROM public.dim_metric_config WHERE metric_key='current_c';
  SELECT id INTO v_volt_a_id  FROM public.dim_metric_config WHERE metric_key='voltage_a';
  SELECT id INTO v_volt_b_id  FROM public.dim_metric_config WHERE metric_key='voltage_b';
  SELECT id INTO v_volt_c_id  FROM public.dim_metric_config WHERE metric_key='voltage_c';

  -- ========================================================================
  -- 回滚修改1：mv_device_running_1s 注入（LEFT JOIN → NOT EXISTS）
  -- ========================================================================
  -- 将 mv_device_running_1s 注入 fwin 以兼容历史规则对 device_running 的依赖（彻底摆脱对 fact 的依赖）
  IF v_running_id IS NOT NULL THEN
    INSERT INTO fwin(id, station_id, device_id, metric_id, ts_bucket, value, qs)
    SELECT NULL::bigint, r.station_id, r.device_id, v_running_id, r.ts_bucket, r.running::int, 0
    FROM public.mv_device_running_1s r
    WHERE r.ts_bucket>=p_start AND r.ts_bucket<p_end
      AND (p_station_id IS NULL OR r.station_id=p_station_id)
      AND (p_device_id  IS NULL OR r.device_id=p_device_id)
      AND NOT EXISTS (
        SELECT 1 FROM fwin x
        WHERE x.station_id=r.station_id AND x.device_id=r.device_id
          AND x.metric_id=v_running_id AND x.ts_bucket=r.ts_bucket
      );
  END IF;

  -- ... 省略中间代码（规则 0-8）...
  -- 注意：完整的回滚需要从备份文件恢复整个存储过程
  -- 本脚本仅展示关键修改点的回滚逻辑

  -- ========================================================================
  -- 回滚修改2：规则503 快速通道（COUNT(*) → NOT EXISTS）
  -- ========================================================================
  -- 在规则503的快速通道判断中，将 COUNT(*) 改回 NOT EXISTS
  -- 原始代码（回滚后）：
  --   IF NOT EXISTS (
  --     SELECT 1
  --     FROM t503_total_secs ts
  --     LEFT JOIN t503_pr_agg pr USING (station_id, device_id, metric_id)
  --     WHERE COALESCE(pr.present_total,0) < ts.total_secs
  --   ) THEN
  --     v_rc := 0;
  --   ...

  RAISE NOTICE '回滚脚本说明：本脚本仅展示关键修改点的回滚逻辑';
  RAISE NOTICE '完整回滚请使用备份文件：036_create_sp_mark_quality_window_vfast.sql.backup_p0_*';
  RAISE NOTICE '或使用 Git 回滚：git checkout mark_quality_window_optimization_baseline -- scripts/sql/migrations/036_create_sp_mark_quality_window_vfast.sql';

END;
$$;

COMMIT;

-- ============================================================================
-- 回滚验证
-- ============================================================================
-- 1. 查看存储过程定义
-- \df+ public.sp_mark_quality_window_vfast

-- 2. 执行存储过程测试
-- CALL public.sp_mark_quality_window_vfast(
--     '2025-11-06 14:00:00'::timestamptz,
--     '2025-11-06 16:00:00'::timestamptz,
--     NULL, NULL, NULL
-- );

-- 3. 查询性能数据
-- SELECT stage, duration_ms, rows_affected
-- FROM public.quality_profile_log
-- WHERE window_start = '2025-11-06 14:00:00'
--   AND window_end = '2025-11-06 16:00:00'
-- ORDER BY duration_ms DESC;

-- ============================================================================
-- 推荐的完整回滚方法
-- ============================================================================
-- 方法1：使用物理备份文件
-- psql -U postgres -d your_database -f scripts/sql/migrations/036_create_sp_mark_quality_window_vfast.sql.backup_p0_20251106_112647

-- 方法2：使用 Git 回滚
-- git checkout mark_quality_window_optimization_baseline -- scripts/sql/migrations/036_create_sp_mark_quality_window_vfast.sql
-- psql -U postgres -d your_database -f scripts/sql/migrations/036_create_sp_mark_quality_window_vfast.sql

-- ============================================================================

