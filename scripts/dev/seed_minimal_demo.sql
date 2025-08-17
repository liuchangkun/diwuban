-- 最小化演示造数（dev）— 维表就绪 + 插入少量事实数据（对齐秒级）
-- 前提：已创建数据库与表结构；允许在 dev 环境写入少量测试数据
-- 约束：时间按泵站时区（extra->>'tz'）对齐到 UTC 秒；不使用 CSV 文件名/路径推断维度/指标
\set ON_ERROR_STOP 1

BEGIN;

-- 1) 站点（若不存在则插入）
INSERT INTO public.dim_stations(name, extra)
SELECT '二期供水泵房', '{"tz":"Asia/Shanghai"}'::jsonb
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_stations WHERE name = '二期供水泵房'
);

-- 2) 获取站点 id
WITH s AS (
  SELECT id FROM public.dim_stations WHERE name='二期供水泵房' LIMIT 1
)
-- 2.1) 设备（泵）
INSERT INTO public.dim_devices(station_id, name, type, pump_type, extra)
SELECT s.id, '二期供水泵房1#泵', 'pump', 'variable_frequency', NULL
FROM s
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_devices d WHERE d.name='二期供水泵房1#泵' AND d.station_id=s.id
);

-- 2.2) 设备（总管）
WITH s AS (
  SELECT id FROM public.dim_stations WHERE name='二期供水泵房' LIMIT 1
)
INSERT INTO public.dim_devices(station_id, name, type, pump_type, extra)
SELECT s.id, '二期供水泵房总管', 'Main_pipeline', NULL, NULL
FROM s
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_devices d WHERE d.name='二期供水泵房总管' AND d.station_id=s.id
);

-- 3) 指标配置（若不存在则插入）
-- 频电压电流功率电度功率因数 + 压力/瞬时流量/累计流量
INSERT INTO public.dim_metric_config(metric_key, unit, unit_display, decimals_policy)
SELECT v.metric_key, v.unit, v.unit_display, 'as_is'
FROM (
  VALUES
    ('frequency','Hz','Hz'),
    ('voltage_a','V','V'),('voltage_b','V','V'),('voltage_c','V','V'),
    ('current_a','A','A'),('current_b','A','A'),('current_c','A','A'),
    ('power','kW','kW'),('kwh','kWh','kWh'),('power_factor','', ''),
    ('pressure','MPa','MPa'),('flow_rate','m3/h','m3/h'),('cumulative_flow','m3','m3')
) AS v(metric_key, unit, unit_display)
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_metric_config m WHERE m.metric_key = v.metric_key
);

-- 4) 映射快照（示例：为泵与总管各生成若干 metric 映射）
WITH s AS (SELECT id, name FROM public.dim_stations WHERE name='二期供水泵房' LIMIT 1),
     pump AS (SELECT id, name FROM public.dim_devices d JOIN s ON d.station_id=s.id WHERE d.name='二期供水泵房1#泵' LIMIT 1),
     main AS (SELECT id, name FROM public.dim_devices d JOIN s ON d.station_id=s.id WHERE d.name='二期供水泵房总管' LIMIT 1)
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5(s.name||'|'||p.name||'|'||k)::text, s.name, p.name, k, 'data_mapping.json'
FROM s JOIN pump p ON TRUE, LATERAL (VALUES
  ('frequency'),('voltage_a'),('current_a'),('power'),('kwh'),('power_factor')
) AS t(k)
ON CONFLICT DO NOTHING;

WITH s AS (SELECT id, name FROM public.dim_stations WHERE name='二期供水泵房' LIMIT 1),
     main AS (SELECT id, name FROM public.dim_devices d JOIN s ON d.station_id=s.id WHERE d.name='二期供水泵房总管' LIMIT 1)
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5(s.name||'|'||m.name||'|'||k)::text, s.name, m.name, k, 'data_mapping.json'
FROM s JOIN main m ON TRUE, LATERAL (VALUES
  ('pressure'),('flow_rate'),('cumulative_flow')
) AS t(k)
ON CONFLICT DO NOTHING;

-- 5) 插入少量事实数据（按站点时区转换本地时间并对齐秒）
-- 5.1) 泵设备：frequency（两条同一秒，验证合并）
WITH s AS (SELECT id FROM public.dim_stations WHERE name='二期供水泵房' LIMIT 1),
     d AS (SELECT id FROM public.dim_devices WHERE name='二期供水泵房1#泵' LIMIT 1),
     m AS (SELECT id FROM public.dim_metric_config WHERE metric_key='frequency' LIMIT 1)
SELECT public.safe_upsert_measurement_local((SELECT id FROM s),(SELECT id FROM d),(SELECT id FROM m),'2025-08-16 10:00:00', 30.5, 'demo');
SELECT public.safe_upsert_measurement_local((SELECT id FROM s),(SELECT id FROM d),(SELECT id FROM m),'2025-08-16 10:00:00.800', 31.0, 'demo');

-- 5.2) 总管：flow_rate（两小时两条）
WITH s AS (SELECT id FROM public.dim_stations WHERE name='二期供水泵房' LIMIT 1),
     d AS (SELECT id FROM public.dim_devices WHERE name='二期供水泵房总管' LIMIT 1),
     m AS (SELECT id FROM public.dim_metric_config WHERE metric_key='flow_rate' LIMIT 1)
SELECT public.safe_upsert_measurement_local((SELECT id FROM s),(SELECT id FROM d),(SELECT id FROM m),'2025-08-16 10:15:00', 120.0, 'demo');
SELECT public.safe_upsert_measurement_local((SELECT id FROM s),(SELECT id FROM d),(SELECT id FROM m),'2025-08-16 11:45:00', 135.2, 'demo');

-- 6) 验证（返回计数与对齐检查）
\echo '--- 验证：维表示例与事实行数 ---'
SELECT 'stations' AS kind, count(*) FROM public.dim_stations WHERE name='二期供水泵房'
UNION ALL
SELECT 'pump_devices', count(*) FROM public.dim_devices d JOIN public.dim_stations s ON s.id=d.station_id WHERE s.name='二期供水泵房' AND d.name='二期供水泵房1#泵'
UNION ALL
SELECT 'main_devices', count(*) FROM public.dim_devices d JOIN public.dim_stations s ON s.id=d.station_id WHERE s.name='二期供水泵房' AND d.name='二期供水泵房总管'
UNION ALL
SELECT 'metric_config_keys', count(*) FROM public.dim_metric_config WHERE metric_key IN ('frequency','flow_rate')
UNION ALL
SELECT 'mapping_items', count(*) FROM public.dim_mapping_items WHERE station_name='二期供水泵房';

\echo '--- 验证：对齐检查（应为 0） ---'
SELECT count(*) AS not_aligned FROM public.fact_measurements WHERE date_trunc('second', ts_bucket) <> ts_bucket;

COMMIT;
