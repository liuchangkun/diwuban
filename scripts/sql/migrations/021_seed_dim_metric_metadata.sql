-- 基于 dim_metric_config 生成 dim_metric_metadata 的初始种子（仅插入缺失项）
-- 说明：
-- - 单位(unit)优先使用 dim_metric_config.unit；若为空保持 NULL
-- - 分辨率(resolution)按常见单位给出经验默认，可后续在 override/全局表里修订；其余保持 NULL
-- - 物理上下界/饱和阈值留空，后续由计算流程/人工补充
-- - 备注(remark)写入指标中文名或类别，便于审计

BEGIN;

INSERT INTO public.dim_metric_metadata(metric_id, unit, resolution, phys_min, phys_max, saturation_min, saturation_max, remark)
SELECT m.id AS metric_id,
       NULLIF(m.unit,'') AS unit,
       CASE
         WHEN lower(m.unit) IN ('v') THEN 1.0              -- 电压 1V
         WHEN lower(m.unit) IN ('a') THEN 0.1              -- 电流 0.1A
         WHEN lower(m.unit) IN ('kw') THEN 0.01            -- 有功功率 0.01kW
         WHEN lower(m.unit) IN ('kwh') THEN 1.0            -- 电能 1kWh
         WHEN lower(m.unit) IN ('hz') THEN 0.1             -- 频率 0.1Hz
         WHEN lower(m.unit) IN ('m3/h','m3/h ') THEN 0.1   -- 瞬时流量 0.1 m3/h
         WHEN lower(m.unit) IN ('m3') THEN 1.0             -- 累计流量 1 m3
         WHEN lower(m.unit) IN ('m') THEN 0.01             -- 液位/扬程 0.01 m
         WHEN lower(m.unit) IN ('mpa') THEN 0.001          -- 压力 0.001 MPa
         WHEN lower(m.unit) IN ('mm/s','mm/s ') THEN 0.01  -- 振动 0.01 mm/s
         WHEN lower(m.unit) IN ('rpm') THEN 1.0            -- 转速 1 rpm
         WHEN lower(m.unit) IN ('n.m','nm') THEN 0.1       -- 扭矩 0.1 N·m
         WHEN lower(m.unit) IN ('%','pct','percent') THEN 0.1 -- 百分比 0.1%
         WHEN lower(m.unit) IN ('c','°c','degc') THEN 0.1  -- 温度 0.1°C
         ELSE NULL
       END AS resolution,
       NULL::double precision AS phys_min,
       NULL::double precision AS phys_max,
       NULL::double precision AS saturation_min,
       NULL::double precision AS saturation_max,
       CASE
         WHEN m.metric_key ILIKE '%power_factor%' THEN '功率因数（0~1）'
         WHEN m.metric_key ILIKE '%active_power%' OR m.metric_key ILIKE '%power' THEN '有功功率'
         WHEN m.metric_key ILIKE '%current%' THEN '电流（A相/B相/C相）'
         WHEN m.metric_key ILIKE '%voltage%' THEN '电压（A相/B相/C相）'
         WHEN m.metric_key ILIKE '%frequency%' THEN '变频器频率/电网频率'
         WHEN m.metric_key ILIKE '%flow%' THEN '流量（瞬时/累计）'
         WHEN m.metric_key ILIKE '%pressure%' THEN '压力（进/出口/总管）'
         WHEN m.metric_key ILIKE '%level%' THEN '液位'
         WHEN m.metric_key ILIKE '%temperature%' THEN '温度'
         WHEN m.metric_key ILIKE '%vibration%' THEN '振动'
         WHEN m.metric_key ILIKE '%torque%' THEN '扭矩'
         WHEN m.metric_key = 'device_running' THEN '设备运行状态（0/1）'
         WHEN m.metric_key = 'device_phase' THEN '运行相位（0停止/1稳态/2启动/3停止）'
         ELSE COALESCE(NULLIF(m.unit_display,''), '通用指标')
       END AS remark
FROM public.dim_metric_config m
LEFT JOIN public.dim_metric_metadata t ON t.metric_id = m.id
WHERE t.metric_id IS NULL;

COMMIT;

