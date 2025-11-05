-- 目的：按时间窗批量执行“首批质量标注规则”，将异常写回 fact_measurements 的质量字段
-- 规则覆盖：越界(101)、异常跳变(111)、平台期(121，固定60s窗口)、状态矛盾(401)、功率因数异常(701)、液位流量守恒异常(711, 简化)
-- 说明：仅在 quality_status=0 时标注，避免覆盖已有标注；可按站/设备过滤

BEGIN;

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
BEGIN
  -- 解析常用指标ID（存在则执行相关规则，不存在则跳过）
  SELECT id INTO v_running_id FROM public.dim_metric_config WHERE metric_key='device_running';
  SELECT id INTO v_power_id   FROM public.dim_metric_config WHERE metric_key IN ('pump_active_power','active_power','power');
  SELECT id INTO v_pf_id      FROM public.dim_metric_config WHERE metric_key IN ('pump_power_factor','power_factor');
  SELECT id INTO v_flow_id    FROM public.dim_metric_config WHERE metric_key IN ('pump_flow_rate','main_pipeline_flow_rate');
  SELECT id INTO v_level_id   FROM public.dim_metric_config WHERE metric_key IN ('pool_liquid_level');

  -- 1) 越界（仅按物理/额定衍生边界，避免窄带统计当作硬越界；排除累计量等非越界型指标）
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

  -- 2) 异常跳变（相邻秒绝对差 > spike_abs）
  WITH base AS (
    SELECT f.*
    FROM public.fact_measurements f
    WHERE f.ts_bucket>=p_start AND f.ts_bucket<p_end
      AND (p_station_id IS NULL OR f.station_id=p_station_id)
      AND (p_device_id  IS NULL OR f.device_id=p_device_id)
      AND COALESCE(f.quality_status,0)=0
  ), dif AS (
    SELECT b.id AS row_id, b.station_id, b.device_id, b.metric_id, b.ts_bucket,
           ABS(b.value - LAG(b.value) OVER (PARTITION BY b.station_id,b.device_id,b.metric_id ORDER BY b.ts_bucket)) AS dv
    FROM base b
  ), eff AS (
    SELECT d.*, r.spike_abs
    FROM dif d
    LEFT JOIN public.v_effective_metric_rules r ON r.metric_id=d.metric_id
  )
  UPDATE public.fact_measurements u
  SET quality_status=111,
      quality_type='异常跳变',
      quality_meta=jsonb_build_object('dv',e.dv,'thr',e.spike_abs)
  FROM eff e
  WHERE u.id=e.row_id AND e.dv IS NOT NULL AND e.spike_abs IS NOT NULL AND e.dv>e.spike_abs
    AND COALESCE(u.quality_status,0)=0;

  -- 3) 平台期（固定 60s 窗口的 stddev/span 判定；阈值来自 v_effective_metric_rules.flatline_eps/delta）
  WITH base2 AS (
    SELECT f.*
    FROM public.fact_measurements f
    WHERE f.ts_bucket>=p_start AND f.ts_bucket<p_end
      AND (p_station_id IS NULL OR f.station_id=p_station_id)
      AND (p_device_id  IS NULL OR f.device_id=p_device_id)
      AND COALESCE(f.quality_status,0)=0
  ), win AS (
    SELECT b.id AS row_id, b.metric_id,
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
    SELECT w.row_id, COALESCE(r.flatline_eps, 1e-9) AS eps, COALESCE(r.flatline_delta, 0.0) AS delta, w.sdev, w.span
    FROM win w
    LEFT JOIN public.v_effective_metric_rules r ON r.metric_id=w.metric_id
  )
  UPDATE public.fact_measurements u
  SET quality_status=121,
      quality_type='平台期',
      quality_meta=jsonb_build_object('stddev',e.sdev,'span',e.span,'eps',e.eps,'delta',e.delta)
  FROM eff2 e
  WHERE u.id=e.row_id AND e.sdev IS NOT NULL AND e.span IS NOT NULL
    AND e.sdev<=e.eps AND e.span<=e.delta
    AND COALESCE(u.quality_status,0)=0;

  -- 4) 状态矛盾（简化两类）：running=0 但功率高；running=1 但总管流量≈0
  IF v_running_id IS NOT NULL AND v_power_id IS NOT NULL THEN
    -- running=0 & power>p_on（阈值来自 device_running_thresholds.p_on）
    WITH p AS (
      SELECT fp.id AS row_id, fp.station_id, fp.device_id, fp.ts_bucket, fp.value AS pval,
             drt.p_on
      FROM public.fact_measurements fp
      JOIN public.mv_device_running_1s fr ON fr.station_id=fp.station_id AND fr.device_id=fp.device_id
        AND fr.ts_bucket=fp.ts_bucket AND fr.running=0
      LEFT JOIN public.device_running_thresholds drt ON drt.device_id=fp.device_id
      WHERE fp.metric_id=v_power_id AND fp.ts_bucket>=p_start AND fp.ts_bucket<p_end
        AND (p_station_id IS NULL OR fp.station_id=p_station_id)
        AND (p_device_id  IS NULL OR fp.device_id=p_device_id)
        AND COALESCE(fp.quality_status,0)=0
    )
    UPDATE public.fact_measurements u
    SET quality_status=401,
        quality_type='状态矛盾',
        quality_meta=jsonb_build_object('case','stopped_but_power_high','p',p.pval,'p_on',p.p_on)
    FROM p
    WHERE u.id=p.row_id AND p.p_on IS NOT NULL AND p.pval>p.p_on AND COALESCE(u.quality_status,0)=0;
  END IF;

  IF v_running_id IS NOT NULL AND v_flow_id IS NOT NULL THEN
    -- running=1 & flow<=min（阈值来自 v_effective_metric_rules.value_min）
    WITH f AS (
      SELECT ff.id AS row_id, ff.station_id, ff.device_id, ff.ts_bucket, ff.value AS q,
             vr.value_min
      FROM public.fact_measurements ff
      JOIN public.mv_device_running_1s fr ON fr.station_id=ff.station_id AND fr.device_id=ff.device_id
        AND fr.ts_bucket=ff.ts_bucket AND fr.running=1
      LEFT JOIN public.v_effective_metric_rules vr ON vr.metric_id=ff.metric_id
      WHERE ff.metric_id=v_flow_id AND ff.ts_bucket>=p_start AND ff.ts_bucket<p_end
        AND (p_station_id IS NULL OR ff.station_id=p_station_id)
        AND (p_device_id  IS NULL OR ff.device_id=p_device_id)
        AND COALESCE(ff.quality_status,0)=0
    )
    UPDATE public.fact_measurements u
    SET quality_status=401,
        quality_type='状态矛盾',
        quality_meta=jsonb_build_object('case','running_but_zero_output','q',f.q,'q_min',f.value_min)
    FROM f
    WHERE u.id=f.row_id AND f.value_min IS NOT NULL AND f.q<=f.value_min AND COALESCE(u.quality_status,0)=0;
  END IF;

  -- 5) 功率因数异常（pf 不在阈值范围）
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
        quality_type='功率因数异常',
        quality_meta=jsonb_build_object('pf',pf.pfv,'pf_min',pf.pf_min,'pf_max',pf.pf_max)
    FROM pf
    WHERE u.id=pf.row_id AND pf.pf_min IS NOT NULL AND pf.pf_max IS NOT NULL
      AND (pf.pfv<pf.pf_min OR pf.pfv>pf.pf_max) AND COALESCE(u.quality_status,0)=0;
  END IF;

  -- 6) 液位流量守恒异常（简化版：当总出流量明显>0而液位仍上升，或入流占位未知时作为提示）
  IF v_flow_id IS NOT NULL AND v_level_id IS NOT NULL THEN
    WITH lv AS (
      SELECT l.id AS row_id, l.station_id, l.device_id, l.ts_bucket, l.value AS level,
             LAG(l.value) OVER (PARTITION BY l.station_id,l.device_id ORDER BY l.ts_bucket) AS prev_level
      FROM public.fact_measurements l
      WHERE l.metric_id=v_level_id AND l.ts_bucket>=p_start AND l.ts_bucket<p_end
        AND (p_station_id IS NULL OR l.station_id=p_station_id)
        AND (p_device_id  IS NULL OR l.device_id=p_device_id)
        AND COALESCE(l.quality_status,0)=0
    ), q AS (
      SELECT f.station_id, f.device_id, f.ts_bucket, f.value AS q_out,
             vr.value_min
      FROM public.fact_measurements f
      LEFT JOIN public.v_effective_metric_rules vr ON vr.metric_id=f.metric_id
      WHERE f.metric_id=v_flow_id AND f.ts_bucket>=p_start AND f.ts_bucket<p_end
    )
    UPDATE public.fact_measurements u
    SET quality_status=711,
        quality_type='液位流量守恒异常',
        quality_meta=jsonb_build_object('case','q_out>0_but_level_rising','q_out',q.q_out,'q_min',q.value_min)
    FROM lv JOIN q ON q.station_id=lv.station_id AND q.device_id=lv.device_id AND q.ts_bucket=lv.ts_bucket
    WHERE u.id=lv.row_id AND lv.prev_level IS NOT NULL AND q.value_min IS NOT NULL
      AND q.q_out>q.value_min AND lv.level>lv.prev_level AND COALESCE(u.quality_status,0)=0;
  END IF;
END;
$$;

COMMENT ON PROCEDURE public.sp_mark_quality_window(timestamptz, timestamptz, bigint, bigint)
IS '质量标注过程：对给定时间窗执行首批规则（越界/跳变/平台期/状态矛盾/功率因数/液位守恒），仅在 quality_status=0 时标注。';

COMMIT;

