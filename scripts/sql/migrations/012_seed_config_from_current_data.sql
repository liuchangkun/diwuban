-- 目的：利用数据库已有数据、函数与视图，自动填充以下表的数值：
-- device_running_thresholds（仅完善pf与相位窗口等）、metric_quality_rules（首批规则参数）、
-- metric_rule_auto_baseline（调用过程刷新）、quality_code_dict（保留，若缺则补齐）

BEGIN;

CREATE OR REPLACE PROCEDURE public.sp_seed_config_from_current_data(
  IN p_lookback_days int DEFAULT 7
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_min_ts timestamptz;
  v_max_ts timestamptz;
  v_phase_metric_id bigint;
  v_pf_metric_id bigint;
  v_power_metric_id bigint;
  v_running_metric_id bigint;
BEGIN
  -- 1) 时间窗：以当前 fact_measurements 的最小/最大时间
  SELECT MIN(ts_bucket), MAX(ts_bucket) INTO v_min_ts, v_max_ts FROM public.fact_measurements;
  IF v_min_ts IS NULL OR v_max_ts IS NULL THEN
    RAISE NOTICE 'fact_measurements 无数据，跳过';
    RETURN;
  END IF;

  -- 2) 刷新自动基线（lookback=参数）；过程内部已支持 device_phase=1 或回退到 device_running=1
  CALL public.sp_refresh_metric_rule_auto_baseline(p_lookback_days, NULL, NULL);

  -- 4) 以自动基线作为默认，补齐 metric_quality_rules（不存在则插入，存在则保留人工设置）
  INSERT INTO public.metric_quality_rules(
    station_id, device_id, metric_id,
    value_min, value_max,
    spike_abs, roc_abs, roc_ratio,
    flatline_eps, flatline_delta,
    remark
  )
  SELECT
    b.station_id, b.device_id, b.metric_id,
    b.p05, b.p95,
    b.spike_abs, b.roc_abs, b.roc_ratio,
    b.flatline_eps, b.flatline_delta,
    'seed:auto_baseline'
  FROM public.metric_rule_auto_baseline b
  LEFT JOIN public.metric_quality_rules r
    ON r.station_id IS NOT DISTINCT FROM b.station_id
   AND r.device_id  IS NOT DISTINCT FROM b.device_id
   AND r.metric_id  IS NOT DISTINCT FROM b.metric_id
  WHERE r.metric_id IS NULL;

  -- 5) 完善 device_running_thresholds：
  --    - 若缺 pf_min/pf_max，则按运行稳态段（device_phase=1）的 5%~95% 填充
  --    - 若窗口参数为空，给出保守默认
  SELECT id INTO v_phase_metric_id FROM public.dim_metric_config WHERE metric_key='device_phase';
  SELECT id INTO v_pf_metric_id    FROM public.dim_metric_config WHERE metric_key IN ('pump_power_factor','power_factor') LIMIT 1;
  SELECT id INTO v_power_metric_id FROM public.dim_metric_config WHERE metric_key IN ('pump_active_power','active_power','power') LIMIT 1;

  IF v_pf_metric_id IS NOT NULL THEN
    WITH base AS (
      SELECT f.device_id, f.value AS pf
      FROM public.fact_measurements f
      LEFT JOIN public.fact_measurements ph
        ON ph.station_id=f.station_id AND ph.device_id=f.device_id AND ph.ts_bucket=f.ts_bucket
       AND v_phase_metric_id IS NOT NULL AND ph.metric_id=v_phase_metric_id AND ph.value=1
      LEFT JOIN public.dim_metric_config mrun ON mrun.metric_key='device_running'
      LEFT JOIN public.fact_measurements frun
        ON frun.station_id=f.station_id AND frun.device_id=f.device_id AND frun.ts_bucket=f.ts_bucket
       AND mrun.id IS NOT NULL AND frun.metric_id=mrun.id AND frun.value=1
      WHERE f.metric_id=v_pf_metric_id AND f.ts_bucket>=v_min_ts AND f.ts_bucket<=v_max_ts
        AND COALESCE(f.quality_status,0)=0 AND f.value IS NOT NULL
        AND (ph.value=1 OR frun.value=1)
    ), agg AS (
      SELECT device_id,
             percentile_cont(0.05) WITHIN GROUP (ORDER BY pf)::float8 AS pf_min,
             percentile_cont(0.95) WITHIN GROUP (ORDER BY pf)::float8 AS pf_max
      FROM base GROUP BY device_id
    )
    UPDATE public.device_running_thresholds t
    SET pf_min = COALESCE(t.pf_min, a.pf_min),
        pf_max = COALESCE(t.pf_max, a.pf_max)
    FROM agg a
    WHERE a.device_id=t.device_id;
  END IF;

  -- 默认窗口与不平衡阈值（仅当为空）
  UPDATE public.device_running_thresholds t
  SET start_pre_secs  = COALESCE(start_pre_secs, 3),
      start_post_secs = COALESCE(start_post_secs, 5),
      stop_pre_secs   = COALESCE(stop_pre_secs, 3),
      stop_post_secs  = COALESCE(stop_post_secs, 3),
      imbalance_max_pct = COALESCE(imbalance_max_pct, 20.0);

  -- 6) 质量字典：若缺少必要条目则补齐（与 005 初始化保持一致）
  INSERT INTO public.quality_code_dict(code,label_zh,category,severity,description)
  VALUES
    (101,'越界','数值特性',3,'数值超出合理区间'),
    (111,'异常跳变','数值特性',3,'相邻秒差值超阈'),
    (112,'变化率异常','数值特性',3,'相对或绝对变化率超阈'),
    (121,'平台期','数值特性',2,'短窗标准差与极差均很小，可能传感器卡死'),
    (131,'上饱和','数值特性',3,'接近量程上限持续'),
    (132,'下饱和','数值特性',3,'接近量程下限持续'),
    (201,'高噪声','噪声/完整性',2,'短窗标准差异常偏高'),
    (401,'状态矛盾','跨指标/跨设备',4,'运行=0但功率/流量高或运行=1但输出近零'),
    (501,'时间漂移','时间一致性',2,'ts_raw 与 ts_bucket 偏差过大'),
    (502,'重复秒','时间一致性',2,'同秒重复/冲突'),
    (701,'功率因数异常','机理/物理',3,'功率因数超出合理范围'),
    (711,'液位流量守恒异常','机理/物理',4,'dLevel/dt 与流量不一致'),
    (721,'相似定律异常','机理/物理',3,'与变频相似定律偏差过大'),
    (731,'泵曲线偏差','机理/物理',3,'与泵特性曲线偏差过大'),
    (751,'计数器非单调','机理/物理',3,'累计量出现回退')
  ON CONFLICT (code) DO NOTHING;
END;
$$;

COMMIT;

-- 立即执行一次：
CALL public.sp_seed_config_from_current_data(7);

