-- 从现有 fact_measurements 的时间范围计算自动基线，并据此补齐规则/阈值/字典
BEGIN;
-- 放宽语句超时，避免大窗口计算被取消
SET LOCAL statement_timeout TO '600000ms';
DO $$
DECLARE
  v_min_ts timestamptz;
  v_max_ts timestamptz;
BEGIN
  PERFORM set_config('statement_timeout','600s', true);
  SELECT MIN(ts_bucket), MAX(ts_bucket) INTO v_min_ts, v_max_ts FROM public.fact_measurements;
  IF v_min_ts IS NULL OR v_max_ts IS NULL THEN
    RAISE NOTICE 'fact_measurements 无数据，跳过种子填充';
    RETURN;
  END IF;
  -- 1) 按边界窗口刷新自动基线（稳态=phase=1 或回退 running=1）
  CALL public.sp_refresh_metric_rule_auto_baseline_win(v_min_ts, v_max_ts + interval '1 second', NULL, NULL);
  -- 2) 运行一次基于数据的种子填充：
  --    - 若缺则补齐 quality_code_dict
  --    - 以自动基线为默认补齐 metric_quality_rules
  --    - 完善 device_running_thresholds（pf_min/pf_max 与默认相位窗口）
  CALL public.sp_seed_config_from_current_data(7);
END$$;
COMMIT;

