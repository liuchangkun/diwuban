BEGIN;

-- 重新定义存储过程：修正指标映射/执行顺序/排除列表/新增 702/751 等
CREATE OR REPLACE PROCEDURE public.sp_mark_quality_window(
  IN p_start timestamptz,
  IN p_end   timestamptz,
  IN p_station_id bigint DEFAULT NULL,
  IN p_device_id  bigint DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_running_id bigint;
  v_power_id   bigint;
  v_pf_id      bigint;
  v_flow_id    bigint;
  v_level_id   bigint;
  v_cur_a_id   bigint;
  v_cur_b_id   bigint;
  v_cur_c_id   bigint;
  v_volt_a_id  bigint;
  v_volt_b_id  bigint;
  v_volt_c_id  bigint;
  v_thr        numeric := 0.15; -- 三相不平衡默认阈值
  rec          record;
BEGIN
  -- 提高当前事务的超时阈值，避免窗口计算被提前取消（5分钟）
  PERFORM set_config('statement_timeout','300000', true);

  -- 仅提取目标窗口到临时表以缩小计算范围
  CREATE TEMP TABLE fwin AS
  SELECT id, station_id, device_id, metric_id, ts_bucket, value, COALESCE(quality_status,0) AS qs
  FROM public.fact_measurements
  WHERE ts_bucket>=p_start AND ts_bucket<p_end
    AND (p_station_id IS NULL OR station_id=p_station_id)
    AND (p_device_id  IS NULL OR device_id=p_device_id);

  CREATE INDEX ON fwin(station_id, device_id, ts_bucket);
  CREATE INDEX ON fwin(metric_id, ts_bucket);
  CREATE INDEX ON fwin(station_id, device_id, ts_bucket, metric_id, value);

  -- 指标ID解析（使用现有 metric_key 命名）
  SELECT id INTO v_running_id FROM public.dim_metric_config WHERE metric_key='device_running';
  SELECT id INTO v_power_id   FROM public.dim_metric_config WHERE metric_key IN ('pump_active_power','active_power','power');
  SELECT id INTO v_pf_id      FROM public.dim_metric_config WHERE metric_key IN ('pump_power_factor','power_factor');
  SELECT id INTO v_flow_id    FROM public.dim_metric_config WHERE metric_key IN ('pump_flow_rate','main_pipeline_flow_rate');
  SELECT id INTO v_level_id   FROM public.dim_metric_config WHERE metric_key IN ('pool_liquid_level');
  SELECT id INTO v_cur_a_id   FROM public.dim_metric_config WHERE metric_key='pump_current_a';
  SELECT id INTO v_cur_b_id   FROM public.dim_metric_config WHERE metric_key='pump_current_b';
  SELECT id INTO v_cur_c_id   FROM public.dim_metric_config WHERE metric_key='pump_current_c';
  SELECT id INTO v_volt_a_id  FROM public.dim_metric_config WHERE metric_key='pump_voltage_a';
  SELECT id INTO v_volt_b_id  FROM public.dim_metric_config WHERE metric_key='pump_voltage_b';
  SELECT id INTO v_volt_c_id  FROM public.dim_metric_config WHERE metric_key='pump_voltage_c';

  -- 0) 计数器单调性（751），仅累计型指标：kWh / 累计流量
  WITH base AS (
    SELECT f.id AS row_id, f.station_id, f.device_id, f.ts_bucket, f.metric_id,
           f.value, LAG(f.value) OVER (PARTITION BY f.station_id,f.device_id,f.metric_id ORDER BY f.ts_bucket) AS prev_v,
           mc.metric_key
    FROM public.fact_measurements f
    JOIN public.dim_metric_config mc ON mc.id=f.metric_id
    WHERE f.ts_bucket>=p_start AND f.ts_bucket<p_end
      AND (p_station_id IS NULL OR f.station_id=p_station_id)
      AND (p_device_id  IS NULL OR f.device_id=p_device_id)
      AND COALESCE(f.quality_status,0)=0
      AND mc.metric_key IN ('pump_kwh','pump_cumulative_flow','main_pipeline_cumulative_flow')
  )
  UPDATE public.fact_measurements u
  SET quality_status=751,
      quality_type='counter_nonmonotonic',
      quality_meta=jsonb_build_object('v',b.value,'prev',b.prev_v)
  FROM base b
  WHERE u.id=b.row_id AND b.prev_v IS NOT NULL AND b.value<b.prev_v AND COALESCE(u.quality_status,0)=0;

  -- 1) 功率因数异常（701），使用 device_running_thresholds.pf_min/max
  IF v_pf_id IS NOT NULL THEN
    WITH pf AS (
      SELECT fp.id AS row_id, fp.device_id, fp.value AS pfv, drt.pf_min, drt.pf_max
      FROM public.fact_measurements fp
      LEFT JOIN public.device_running_thresholds drt ON drt.device_id=fp.device_id
      WHERE fp.metric_id=v_pf_id AND fp.ts_bucket>=p_start AND fp.ts_bucket<p_end
        AND (p_station_id IS NULL OR fp.station_id=p_station_id)
        AND (p_device_id  IS NULL OR fp.device_id=p_device_id)
        AND COALESCE(fp.quality_status,0)=0
    )
    UPDATE public.fact_measurements u
    SET quality_status=701,
        quality_type='pf_out_of_range',
        quality_meta=jsonb_build_object('pf',pf.pfv,'pf_min',pf.pf_min,'pf_max',pf.pf_max)
    FROM pf
    WHERE u.id=pf.row_id AND pf.pf_min IS NOT NULL AND pf.pf_max IS NOT NULL
      AND (pf.pfv<pf.pf_min OR pf.pfv>pf.pf_max) AND COALESCE(u.quality_status,0)=0;
  END IF;

  -- 2) 三相不平衡（702）：电流与电压的相间不平衡
  -- 基于当前秒的 a/b/c 三相值计算 (max-min)/avg > imbalance_max_pct
  -- 从 device_running_thresholds.imbalance_max_pct 取阈值，缺省 0.15
  -- 读取阈值
  SELECT COALESCE(MAX(imbalance_max_pct), 0.15) INTO v_thr FROM public.device_running_thresholds;
  -- 电流三相
  IF v_cur_a_id IS NOT NULL AND v_cur_b_id IS NOT NULL AND v_cur_c_id IS NOT NULL THEN
    WITH cur3 AS (
      SELECT fa.station_id, fa.device_id, fa.ts_bucket,
             fa.id AS id_a, fb.id AS id_b, fc.id AS id_c,
             fa.value AS va, fb.value AS vb, fc.value AS vc
      FROM public.fact_measurements fa
      JOIN public.fact_measurements fb ON fb.station_id=fa.station_id AND fb.device_id=fa.device_id AND fb.ts_bucket=fa.ts_bucket AND fb.metric_id=v_cur_b_id
      JOIN public.fact_measurements fc ON fc.station_id=fa.station_id AND fc.device_id=fa.device_id AND fc.ts_bucket=fa.ts_bucket AND fc.metric_id=v_cur_c_id
      JOIN public.mv_device_running_1s fr ON fr.station_id=fa.station_id AND fr.device_id=fa.device_id AND fr.ts_bucket=fa.ts_bucket AND fr.running=1
      WHERE fa.metric_id=v_cur_a_id AND fa.ts_bucket>=p_start AND fa.ts_bucket<p_end
        AND (p_station_id IS NULL OR fa.station_id=p_station_id)
        AND (p_device_id  IS NULL OR fa.device_id=p_device_id)
    ), bad AS (
      SELECT *, CASE WHEN (va+vb+vc)>0 THEN (GREATEST(va,vb,vc)-LEAST(va,vb,vc))/NULLIF(((va+vb+vc)/3.0),0) ELSE NULL END AS imb
      FROM cur3
    )
    UPDATE public.fact_measurements u
    SET quality_status=702,
        quality_type='three_phase_imbalance',
        quality_meta=jsonb_build_object('imbalance',b.imb,'thr',v_thr)
    FROM bad b
    WHERE (u.id=b.id_a OR u.id=b.id_b OR u.id=b.id_c) AND b.imb IS NOT NULL AND b.imb>v_thr AND COALESCE(u.quality_status,0)=0;
  END IF;
  -- 电压三相
  IF v_volt_a_id IS NOT NULL AND v_volt_b_id IS NOT NULL AND v_volt_c_id IS NOT NULL THEN
    WITH v3 AS (
      SELECT fa.station_id, fa.device_id, fa.ts_bucket,
             fa.id AS id_a, fb.id AS id_b, fc.id AS id_c,
             fa.value AS va, fb.value AS vb, fc.value AS vc
      FROM public.fact_measurements fa
      JOIN public.fact_measurements fb ON fb.station_id=fa.station_id AND fb.device_id=fa.device_id AND fb.ts_bucket=fa.ts_bucket AND fb.metric_id=v_volt_b_id
      JOIN public.fact_measurements fc ON fc.station_id=fa.station_id AND fc.device_id=fa.device_id AND fc.ts_bucket=fa.ts_bucket AND fc.metric_id=v_volt_c_id
      JOIN public.mv_device_running_1s fr ON fr.station_id=fa.station_id AND fr.device_id=fa.device_id AND fr.ts_bucket=fa.ts_bucket AND fr.running=1
      WHERE fa.metric_id=v_volt_a_id AND fa.ts_bucket>=p_start AND fa.ts_bucket<p_end
        AND (p_station_id IS NULL OR fa.station_id=p_station_id)
        AND (p_device_id  IS NULL OR fa.device_id=p_device_id)
    ), bad AS (
      SELECT *, CASE WHEN (va+vb+vc)>0 THEN (GREATEST(va,vb,vc)-LEAST(va,vb,vc))/NULLIF(((va+vb+vc)/3.0),0) ELSE NULL END AS imb
      FROM v3
    )
    UPDATE public.fact_measurements u
    SET quality_status=702,
        quality_type='three_phase_imbalance',
        quality_meta=jsonb_build_object('imbalance',b.imb,'thr',v_thr)
    FROM bad b
    WHERE (u.id=b.id_a OR u.id=b.id_b OR u.id=b.id_c) AND b.imb IS NOT NULL AND b.imb>v_thr AND COALESCE(u.quality_status,0)=0;
  END IF;

  -- 3) 状态矛盾（401）：running=0 & power>p_on；running=1 & flow<=q_min
  IF v_running_id IS NOT NULL AND v_power_id IS NOT NULL THEN
    FOR rec IN (
      SELECT fp.id AS row_id, fp.value AS pval, COALESCE(drt.p_on, 0.0) AS p_on
      FROM fwin fp
      LEFT JOIN public.device_running_thresholds drt ON drt.device_id=fp.device_id
      WHERE fp.metric_id=v_power_id AND fp.qs=0
        AND EXISTS (
          SELECT 1 FROM fwin fr
          WHERE fr.station_id=fp.station_id AND fr.device_id=fp.device_id
            AND fr.ts_bucket=fp.ts_bucket AND fr.metric_id=v_running_id AND fr.value=0
        )
        AND COALESCE(drt.p_on,0.0) IS NOT NULL AND fp.value>COALESCE(drt.p_on,0.0)
    ) LOOP
      UPDATE public.fact_measurements u
      SET quality_status=401,
          quality_type='state_conflict_stopped_but_power_high',
          quality_meta=jsonb_build_object('p',rec.pval,'p_on',rec.p_on)
      WHERE u.id=rec.row_id AND COALESCE(u.quality_status,0)=0;
    END LOOP;
  END IF;

  IF v_running_id IS NOT NULL AND v_flow_id IS NOT NULL THEN
    FOR rec IN (
      SELECT ff.id AS row_id, ff.value AS q,
             COALESCE(o.phys_min, m.phys_min, 0.0) AS q_min
      FROM fwin ff
      LEFT JOIN LATERAL (
        SELECT dmo.phys_min
        FROM public.dim_metric_metadata_override dmo
        WHERE dmo.metric_id=ff.metric_id
          AND (dmo.device_id = ff.device_id OR dmo.device_id IS NULL)
          AND (dmo.station_id = ff.station_id OR dmo.station_id IS NULL)
        ORDER BY (dmo.device_id IS NOT NULL) DESC, (dmo.station_id IS NOT NULL) DESC
        LIMIT 1
      ) o ON TRUE
      LEFT JOIN public.dim_metric_metadata m ON m.metric_id=ff.metric_id
      WHERE ff.metric_id=v_flow_id AND ff.qs=0
        AND EXISTS (
          SELECT 1 FROM fwin fr
          WHERE fr.station_id=ff.station_id AND fr.device_id=ff.device_id
            AND fr.ts_bucket=ff.ts_bucket AND fr.metric_id=v_running_id AND fr.value=1
        )
        AND (COALESCE(o.phys_min, m.phys_min, 0.0) IS NOT NULL)
        AND ff.value <= COALESCE(o.phys_min, m.phys_min, 0.0)
    ) LOOP
      UPDATE public.fact_measurements u
      SET quality_status=401,
          quality_type='state_conflict_running_but_zero_output',
          quality_meta=jsonb_build_object('q',rec.q,'q_min',rec.q_min)
      WHERE u.id=rec.row_id AND COALESCE(u.quality_status,0)=0;
    END LOOP;
  END IF;

  -- 4) 物理越界（101）：仅物理/额定边界，排除累计量
  WITH tgt AS (
    SELECT f.id AS row_id, f.station_id, f.device_id, f.metric_id, f.ts_bucket, f.value,
           COALESCE(o.phys_min, m.phys_min) AS value_min,
           COALESCE(o.phys_max, m.phys_max) AS value_max,
           mc.metric_key
    FROM public.fact_measurements f
    JOIN public.dim_metric_config mc ON mc.id=f.metric_id
    LEFT JOIN LATERAL (
      SELECT dmo.phys_min, dmo.phys_max
      FROM public.dim_metric_metadata_override dmo
      WHERE dmo.metric_id=f.metric_id
        AND (dmo.device_id = f.device_id OR dmo.device_id IS NULL)
        AND (dmo.station_id = f.station_id OR dmo.station_id IS NULL)
      ORDER BY (dmo.device_id IS NOT NULL) DESC, (dmo.station_id IS NOT NULL) DESC
      LIMIT 1
    ) o ON TRUE
    LEFT JOIN public.dim_metric_metadata m ON m.metric_id=f.metric_id
    WHERE f.ts_bucket>=p_start AND f.ts_bucket<p_end
      AND (p_station_id IS NULL OR f.station_id=p_station_id)
      AND (p_device_id  IS NULL OR f.device_id=p_device_id)
      AND COALESCE(f.quality_status,0)=0
      AND f.value IS NOT NULL
      AND mc.metric_key NOT IN ('pump_kwh','pump_cumulative_flow','main_pipeline_cumulative_flow')
  )
  UPDATE public.fact_measurements u
  SET quality_status=101,
      quality_type='越界',
      quality_meta=jsonb_build_object('min',t.value_min,'max',t.value_max,'v',t.value,'source','phys_bounds')
  FROM tgt t
  WHERE u.id=t.row_id AND t.value IS NOT NULL AND (
        (t.value_min IS NOT NULL AND t.value<t.value_min) OR
        (t.value_max IS NOT NULL AND t.value>t.value_max)
  );

  -- 5) 异常跳变（111）：运行态限定；排除状态/累计/PF；策略 residual 或 hybrid
  --    通用增强：相对阈值(roc_ratio)、量化步进过滤(≥3×resolution)、反跳去抖（下一秒回到前值则忽略）
  WITH base AS (
    SELECT f.*
    FROM fwin f
    JOIN public.dim_metric_config mc ON mc.id=f.metric_id
    LEFT JOIN public.metric_anomaly_strategy mas ON mas.metric_id=f.metric_id AND mas.station_id=0 AND mas.device_id=0
    JOIN fwin fr ON fr.station_id=f.station_id AND fr.device_id=f.device_id AND fr.ts_bucket=f.ts_bucket AND fr.metric_id=v_running_id AND fr.value=1
    WHERE f.qs=0
      AND mc.metric_key NOT IN ('device_running','device_phase','pump_kwh','pump_cumulative_flow','main_pipeline_cumulative_flow','pump_power_factor')
      AND COALESCE(mas.strategy,'residual') IN ('residual','hybrid')
  ), dif AS (
    SELECT b.id AS row_id, b.station_id, b.device_id, b.metric_id, b.ts_bucket,
           b.value AS val,
           LAG(b.value)  OVER (PARTITION BY b.station_id,b.device_id,b.metric_id ORDER BY b.ts_bucket) AS prev_val,
           LEAD(b.value) OVER (PARTITION BY b.station_id,b.device_id,b.metric_id ORDER BY b.ts_bucket) AS next_val,
           ABS(b.value - LAG(b.value) OVER (PARTITION BY b.station_id,b.device_id,b.metric_id ORDER BY b.ts_bucket)) AS dv
    FROM base b
  ), eff AS (
    SELECT d.row_id, d.metric_id, d.dv, d.prev_val, d.next_val,
           COALESCE(r.spike_abs, 0.0) AS spike_abs,
           COALESCE(r.roc_ratio, 0.0) AS spike_rel,
           COALESCE(em.resolution, 0.0) AS resolution
    FROM dif d
    LEFT JOIN public.v_effective_metric_rules r ON r.metric_id=d.metric_id
    LEFT JOIN public.v_effective_metric_metadata em ON em.metric_id=d.metric_id
  ), thr AS (
    SELECT e.*, GREATEST(e.spike_abs,
                         e.spike_rel * GREATEST(ABS(e.prev_val), 1e-9),
                         3.0 * e.resolution) AS eff_thr,
           CASE WHEN e.next_val IS NOT NULL AND e.prev_val IS NOT NULL AND ABS(e.next_val - e.prev_val) <= e.dv * 0.25
                THEN TRUE ELSE FALSE END AS debounce
    FROM eff e
  )
  UPDATE public.fact_measurements u
  SET quality_status=111,
      quality_type='异常跳变',
      quality_meta=jsonb_build_object('dv',t.dv,'thr',t.eff_thr,'spike_abs',t.spike_abs,'spike_rel',t.spike_rel,'resolution',t.resolution)
  FROM thr t
  WHERE u.id=t.row_id AND t.dv IS NOT NULL AND t.eff_thr IS NOT NULL AND t.dv>t.eff_thr AND NOT t.debounce
    AND COALESCE(u.quality_status,0)=0;

  -- 6) 平台期（121）：运行态限定；排除状态/累计/PF；阈值来自 flatline_eps/delta
  --    通用增强：最小持续秒数(flatline_secs)、斜率约束（基于 resolution）、波动带≤MAD_k（用 auto_baseline.mad 兜底）
  WITH base2 AS (
    SELECT f.*
    FROM fwin f
    JOIN public.dim_metric_config mc ON mc.id=f.metric_id
    LEFT JOIN public.metric_anomaly_strategy mas ON mas.metric_id=f.metric_id AND mas.station_id=0 AND mas.device_id=0
    JOIN fwin fr ON fr.station_id=f.station_id AND fr.device_id=f.device_id AND fr.ts_bucket=f.ts_bucket AND fr.metric_id=v_running_id AND fr.value=1
    WHERE f.qs=0
      AND mc.metric_key NOT IN ('device_running','device_phase','pump_kwh','pump_cumulative_flow','main_pipeline_cumulative_flow','pump_power_factor')
      AND COALESCE(mas.strategy,'residual') IN ('residual','hybrid')
  ), win AS (
    SELECT b.id AS row_id, b.metric_id, b.station_id, b.device_id, b.ts_bucket,
           STDDEV_SAMP(b.value) OVER (
             PARTITION BY b.station_id,b.device_id,b.metric_id
             ORDER BY b.ts_bucket
             RANGE BETWEEN INTERVAL '60 seconds' PRECEDING AND CURRENT ROW
           ) AS sdev,
           (MAX(b.value) OVER (
             PARTITION BY b.station_id,b.device_id,b.metric_id
             ORDER BY b.ts_bucket
             RANGE BETWEEN INTERVAL '60 seconds' PRECEDING AND CURRENT ROW
           ) - MIN(b.value) OVER (
             PARTITION BY b.station_id,b.device_id,b.metric_id
             ORDER BY b.ts_bucket
             RANGE BETWEEN INTERVAL '60 seconds' PRECEDING AND CURRENT ROW
           )) AS span
    FROM base2 b
  ), eff2 AS (
    SELECT w.row_id, w.station_id, w.device_id, w.metric_id, w.sdev, w.span,
           COALESCE(r.flatline_eps, 1e-9) AS eps,
           COALESCE(r.flatline_delta, 0.0) AS delta,
           COALESCE(r.flatline_secs, 5) AS min_secs,
           COALESCE(mb.mad, 0.0) AS mad,
           COALESCE(em.resolution, 0.0) AS resolution
    FROM win w
    LEFT JOIN public.v_effective_metric_rules r ON r.metric_id=w.metric_id
    LEFT JOIN public.metric_rule_auto_baseline mb ON mb.metric_id=w.metric_id AND mb.device_id IS NULL AND mb.station_id IS NULL
    LEFT JOIN public.v_effective_metric_metadata em ON em.metric_id=w.metric_id
  ), judge AS (
    SELECT e.*,
           -- 斜率近似（span/min_secs）需小于每秒 1×resolution
           CASE WHEN e.min_secs>0 THEN e.span/GREATEST(e.min_secs,1) ELSE e.span END AS slope,
           1.0 * e.resolution AS slope_thr,
           -- 引入 mad 的兜底波动带（若配置过小，至少不小于 0.5×MAD）
           GREATEST(e.delta, e.mad*0.5) AS eff_delta
    FROM eff2 e
  )
  UPDATE public.fact_measurements u
  SET quality_status=121,
      quality_type='平台期',
      quality_meta=jsonb_build_object('stddev',j.sdev,'span',j.span,'eps',j.eps,'delta',j.delta,'min_secs',j.min_secs,'resolution',j.resolution)
  FROM judge j
  WHERE u.id=j.row_id AND j.sdev IS NOT NULL AND j.span IS NOT NULL
    AND j.sdev<=j.eps AND j.span<=j.eff_delta AND j.slope<=j.slope_thr
    AND COALESCE(u.quality_status,0)=0;
END;
$$;

COMMENT ON PROCEDURE public.sp_mark_quality_window(timestamptz, timestamptz, bigint, bigint)
IS '质量标注过程（v2）：修正指标映射、执行顺序与过滤；新增 751/702；101 仅物理边界；排除状态/累计量参与 111/121。';

COMMIT;

