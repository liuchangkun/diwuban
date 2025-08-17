-- Auto-generated from config/data_mapping.json
-- Do not edit manually. UTF-8, LF newlines.
\set ON_ERROR_STOP 1
BEGIN;
INSERT INTO public.dim_stations(name)
SELECT '二期供水泵房'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_stations WHERE name='二期供水泵房'
);
INSERT INTO public.dim_stations(name)
SELECT '二期取水泵房'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_stations WHERE name='二期取水泵房'
);
WITH s AS (
  SELECT id FROM public.dim_stations WHERE name='二期供水泵房' LIMIT 1
)
INSERT INTO public.dim_devices(station_id, name, type, pump_type)
SELECT s.id, '二期供水泵房1#泵', 'pump', 'variable_frequency'
FROM s
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_devices d WHERE d.station_id=s.id AND d.name='二期供水泵房1#泵'
);
WITH s AS (
  SELECT id FROM public.dim_stations WHERE name='二期供水泵房' LIMIT 1
)
INSERT INTO public.dim_devices(station_id, name, type, pump_type)
SELECT s.id, '二期供水泵房2#泵', 'pump', 'variable_frequency'
FROM s
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_devices d WHERE d.station_id=s.id AND d.name='二期供水泵房2#泵'
);
WITH s AS (
  SELECT id FROM public.dim_stations WHERE name='二期供水泵房' LIMIT 1
)
INSERT INTO public.dim_devices(station_id, name, type, pump_type)
SELECT s.id, '二期供水泵房3#泵', 'pump', 'variable_frequency'
FROM s
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_devices d WHERE d.station_id=s.id AND d.name='二期供水泵房3#泵'
);
WITH s AS (
  SELECT id FROM public.dim_stations WHERE name='二期供水泵房' LIMIT 1
)
INSERT INTO public.dim_devices(station_id, name, type, pump_type)
SELECT s.id, '二期供水泵房4#泵', 'pump', 'variable_frequency'
FROM s
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_devices d WHERE d.station_id=s.id AND d.name='二期供水泵房4#泵'
);
WITH s AS (
  SELECT id FROM public.dim_stations WHERE name='二期供水泵房' LIMIT 1
)
INSERT INTO public.dim_devices(station_id, name, type, pump_type)
SELECT s.id, '二期供水泵房5#泵', 'pump', 'variable_frequency'
FROM s
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_devices d WHERE d.station_id=s.id AND d.name='二期供水泵房5#泵'
);
WITH s AS (
  SELECT id FROM public.dim_stations WHERE name='二期供水泵房' LIMIT 1
)
INSERT INTO public.dim_devices(station_id, name, type, pump_type)
SELECT s.id, '二期供水泵房6#泵', 'pump', 'variable_frequency'
FROM s
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_devices d WHERE d.station_id=s.id AND d.name='二期供水泵房6#泵'
);
WITH s AS (
  SELECT id FROM public.dim_stations WHERE name='二期供水泵房' LIMIT 1
)
INSERT INTO public.dim_devices(station_id, name, type, pump_type)
SELECT s.id, '二期供水泵房总管', 'Main_pipeline', NULL
FROM s
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_devices d WHERE d.station_id=s.id AND d.name='二期供水泵房总管'
);
WITH s AS (
  SELECT id FROM public.dim_stations WHERE name='二期取水泵房' LIMIT 1
)
INSERT INTO public.dim_devices(station_id, name, type, pump_type)
SELECT s.id, '二期取水泵房1#泵', 'pump', 'soft_start'
FROM s
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_devices d WHERE d.station_id=s.id AND d.name='二期取水泵房1#泵'
);
WITH s AS (
  SELECT id FROM public.dim_stations WHERE name='二期取水泵房' LIMIT 1
)
INSERT INTO public.dim_devices(station_id, name, type, pump_type)
SELECT s.id, '二期取水泵房2#泵', 'pump', 'variable_frequency'
FROM s
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_devices d WHERE d.station_id=s.id AND d.name='二期取水泵房2#泵'
);
WITH s AS (
  SELECT id FROM public.dim_stations WHERE name='二期取水泵房' LIMIT 1
)
INSERT INTO public.dim_devices(station_id, name, type, pump_type)
SELECT s.id, '二期取水泵房3#泵', 'pump', 'soft_start'
FROM s
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_devices d WHERE d.station_id=s.id AND d.name='二期取水泵房3#泵'
);
WITH s AS (
  SELECT id FROM public.dim_stations WHERE name='二期取水泵房' LIMIT 1
)
INSERT INTO public.dim_devices(station_id, name, type, pump_type)
SELECT s.id, '二期取水泵房4#泵', 'pump', 'soft_start'
FROM s
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_devices d WHERE d.station_id=s.id AND d.name='二期取水泵房4#泵'
);
WITH s AS (
  SELECT id FROM public.dim_stations WHERE name='二期取水泵房' LIMIT 1
)
INSERT INTO public.dim_devices(station_id, name, type, pump_type)
SELECT s.id, '二期取水泵房5#泵', 'pump', 'variable_frequency'
FROM s
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_devices d WHERE d.station_id=s.id AND d.name='二期取水泵房5#泵'
);
WITH s AS (
  SELECT id FROM public.dim_stations WHERE name='二期取水泵房' LIMIT 1
)
INSERT INTO public.dim_devices(station_id, name, type, pump_type)
SELECT s.id, '总管', 'Main_pipeline', NULL
FROM s
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_devices d WHERE d.station_id=s.id AND d.name='总管'
);
-- dim_metric_config upsert
INSERT INTO public.dim_metric_config(metric_key, unit, unit_display, decimals_policy)
SELECT 'cumulative_flow', 'm3', 'm3', 'as_is'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_metric_config m WHERE m.metric_key='cumulative_flow'
);
INSERT INTO public.dim_metric_config(metric_key, unit, unit_display, decimals_policy)
SELECT 'current_a', 'A', 'A', 'as_is'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_metric_config m WHERE m.metric_key='current_a'
);
INSERT INTO public.dim_metric_config(metric_key, unit, unit_display, decimals_policy)
SELECT 'current_b', 'A', 'A', 'as_is'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_metric_config m WHERE m.metric_key='current_b'
);
INSERT INTO public.dim_metric_config(metric_key, unit, unit_display, decimals_policy)
SELECT 'current_c', 'A', 'A', 'as_is'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_metric_config m WHERE m.metric_key='current_c'
);
INSERT INTO public.dim_metric_config(metric_key, unit, unit_display, decimals_policy)
SELECT 'flow_rate', 'm3/h', 'm3/h', 'as_is'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_metric_config m WHERE m.metric_key='flow_rate'
);
INSERT INTO public.dim_metric_config(metric_key, unit, unit_display, decimals_policy)
SELECT 'frequency', 'Hz', 'Hz', 'as_is'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_metric_config m WHERE m.metric_key='frequency'
);
INSERT INTO public.dim_metric_config(metric_key, unit, unit_display, decimals_policy)
SELECT 'kwh', 'kWh', 'kWh', 'as_is'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_metric_config m WHERE m.metric_key='kwh'
);
INSERT INTO public.dim_metric_config(metric_key, unit, unit_display, decimals_policy)
SELECT 'power', 'kW', 'kW', 'as_is'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_metric_config m WHERE m.metric_key='power'
);
INSERT INTO public.dim_metric_config(metric_key, unit, unit_display, decimals_policy)
SELECT 'power_factor', '', '', 'as_is'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_metric_config m WHERE m.metric_key='power_factor'
);
INSERT INTO public.dim_metric_config(metric_key, unit, unit_display, decimals_policy)
SELECT 'pressure', 'MPa', 'MPa', 'as_is'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_metric_config m WHERE m.metric_key='pressure'
);
INSERT INTO public.dim_metric_config(metric_key, unit, unit_display, decimals_policy)
SELECT 'voltage_a', 'V', 'V', 'as_is'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_metric_config m WHERE m.metric_key='voltage_a'
);
INSERT INTO public.dim_metric_config(metric_key, unit, unit_display, decimals_policy)
SELECT 'voltage_b', 'V', 'V', 'as_is'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_metric_config m WHERE m.metric_key='voltage_b'
);
INSERT INTO public.dim_metric_config(metric_key, unit, unit_display, decimals_policy)
SELECT 'voltage_c', 'V', 'V', 'as_is'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_metric_config m WHERE m.metric_key='voltage_c'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房1#泵'||'|'||'frequency')::text, '二期供水泵房', '二期供水泵房1#泵', 'frequency', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房1#泵' AND metric_key='frequency'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房1#泵'||'|'||'voltage_a')::text, '二期供水泵房', '二期供水泵房1#泵', 'voltage_a', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房1#泵' AND metric_key='voltage_a'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房1#泵'||'|'||'current_a')::text, '二期供水泵房', '二期供水泵房1#泵', 'current_a', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房1#泵' AND metric_key='current_a'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房1#泵'||'|'||'voltage_b')::text, '二期供水泵房', '二期供水泵房1#泵', 'voltage_b', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房1#泵' AND metric_key='voltage_b'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房1#泵'||'|'||'current_b')::text, '二期供水泵房', '二期供水泵房1#泵', 'current_b', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房1#泵' AND metric_key='current_b'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房1#泵'||'|'||'voltage_c')::text, '二期供水泵房', '二期供水泵房1#泵', 'voltage_c', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房1#泵' AND metric_key='voltage_c'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房1#泵'||'|'||'current_c')::text, '二期供水泵房', '二期供水泵房1#泵', 'current_c', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房1#泵' AND metric_key='current_c'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房1#泵'||'|'||'power')::text, '二期供水泵房', '二期供水泵房1#泵', 'power', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房1#泵' AND metric_key='power'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房1#泵'||'|'||'kwh')::text, '二期供水泵房', '二期供水泵房1#泵', 'kwh', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房1#泵' AND metric_key='kwh'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房1#泵'||'|'||'power_factor')::text, '二期供水泵房', '二期供水泵房1#泵', 'power_factor', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房1#泵' AND metric_key='power_factor'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房2#泵'||'|'||'frequency')::text, '二期供水泵房', '二期供水泵房2#泵', 'frequency', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房2#泵' AND metric_key='frequency'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房2#泵'||'|'||'voltage_a')::text, '二期供水泵房', '二期供水泵房2#泵', 'voltage_a', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房2#泵' AND metric_key='voltage_a'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房2#泵'||'|'||'current_a')::text, '二期供水泵房', '二期供水泵房2#泵', 'current_a', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房2#泵' AND metric_key='current_a'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房2#泵'||'|'||'voltage_b')::text, '二期供水泵房', '二期供水泵房2#泵', 'voltage_b', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房2#泵' AND metric_key='voltage_b'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房2#泵'||'|'||'current_b')::text, '二期供水泵房', '二期供水泵房2#泵', 'current_b', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房2#泵' AND metric_key='current_b'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房2#泵'||'|'||'voltage_c')::text, '二期供水泵房', '二期供水泵房2#泵', 'voltage_c', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房2#泵' AND metric_key='voltage_c'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房2#泵'||'|'||'current_c')::text, '二期供水泵房', '二期供水泵房2#泵', 'current_c', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房2#泵' AND metric_key='current_c'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房2#泵'||'|'||'power')::text, '二期供水泵房', '二期供水泵房2#泵', 'power', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房2#泵' AND metric_key='power'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房2#泵'||'|'||'kwh')::text, '二期供水泵房', '二期供水泵房2#泵', 'kwh', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房2#泵' AND metric_key='kwh'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房2#泵'||'|'||'power_factor')::text, '二期供水泵房', '二期供水泵房2#泵', 'power_factor', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房2#泵' AND metric_key='power_factor'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房3#泵'||'|'||'frequency')::text, '二期供水泵房', '二期供水泵房3#泵', 'frequency', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房3#泵' AND metric_key='frequency'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房3#泵'||'|'||'voltage_a')::text, '二期供水泵房', '二期供水泵房3#泵', 'voltage_a', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房3#泵' AND metric_key='voltage_a'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房3#泵'||'|'||'current_a')::text, '二期供水泵房', '二期供水泵房3#泵', 'current_a', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房3#泵' AND metric_key='current_a'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房3#泵'||'|'||'voltage_b')::text, '二期供水泵房', '二期供水泵房3#泵', 'voltage_b', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房3#泵' AND metric_key='voltage_b'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房3#泵'||'|'||'current_b')::text, '二期供水泵房', '二期供水泵房3#泵', 'current_b', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房3#泵' AND metric_key='current_b'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房3#泵'||'|'||'voltage_c')::text, '二期供水泵房', '二期供水泵房3#泵', 'voltage_c', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房3#泵' AND metric_key='voltage_c'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房3#泵'||'|'||'current_c')::text, '二期供水泵房', '二期供水泵房3#泵', 'current_c', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房3#泵' AND metric_key='current_c'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房3#泵'||'|'||'power')::text, '二期供水泵房', '二期供水泵房3#泵', 'power', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房3#泵' AND metric_key='power'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房3#泵'||'|'||'kwh')::text, '二期供水泵房', '二期供水泵房3#泵', 'kwh', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房3#泵' AND metric_key='kwh'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房3#泵'||'|'||'power_factor')::text, '二期供水泵房', '二期供水泵房3#泵', 'power_factor', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房3#泵' AND metric_key='power_factor'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房4#泵'||'|'||'frequency')::text, '二期供水泵房', '二期供水泵房4#泵', 'frequency', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房4#泵' AND metric_key='frequency'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房4#泵'||'|'||'voltage_a')::text, '二期供水泵房', '二期供水泵房4#泵', 'voltage_a', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房4#泵' AND metric_key='voltage_a'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房4#泵'||'|'||'current_a')::text, '二期供水泵房', '二期供水泵房4#泵', 'current_a', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房4#泵' AND metric_key='current_a'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房4#泵'||'|'||'voltage_b')::text, '二期供水泵房', '二期供水泵房4#泵', 'voltage_b', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房4#泵' AND metric_key='voltage_b'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房4#泵'||'|'||'current_b')::text, '二期供水泵房', '二期供水泵房4#泵', 'current_b', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房4#泵' AND metric_key='current_b'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房4#泵'||'|'||'voltage_c')::text, '二期供水泵房', '二期供水泵房4#泵', 'voltage_c', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房4#泵' AND metric_key='voltage_c'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房4#泵'||'|'||'current_c')::text, '二期供水泵房', '二期供水泵房4#泵', 'current_c', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房4#泵' AND metric_key='current_c'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房4#泵'||'|'||'power')::text, '二期供水泵房', '二期供水泵房4#泵', 'power', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房4#泵' AND metric_key='power'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房4#泵'||'|'||'kwh')::text, '二期供水泵房', '二期供水泵房4#泵', 'kwh', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房4#泵' AND metric_key='kwh'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房4#泵'||'|'||'power_factor')::text, '二期供水泵房', '二期供水泵房4#泵', 'power_factor', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房4#泵' AND metric_key='power_factor'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房5#泵'||'|'||'frequency')::text, '二期供水泵房', '二期供水泵房5#泵', 'frequency', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房5#泵' AND metric_key='frequency'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房5#泵'||'|'||'voltage_a')::text, '二期供水泵房', '二期供水泵房5#泵', 'voltage_a', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房5#泵' AND metric_key='voltage_a'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房5#泵'||'|'||'current_a')::text, '二期供水泵房', '二期供水泵房5#泵', 'current_a', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房5#泵' AND metric_key='current_a'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房5#泵'||'|'||'voltage_b')::text, '二期供水泵房', '二期供水泵房5#泵', 'voltage_b', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房5#泵' AND metric_key='voltage_b'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房5#泵'||'|'||'current_b')::text, '二期供水泵房', '二期供水泵房5#泵', 'current_b', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房5#泵' AND metric_key='current_b'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房5#泵'||'|'||'voltage_c')::text, '二期供水泵房', '二期供水泵房5#泵', 'voltage_c', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房5#泵' AND metric_key='voltage_c'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房5#泵'||'|'||'current_c')::text, '二期供水泵房', '二期供水泵房5#泵', 'current_c', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房5#泵' AND metric_key='current_c'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房5#泵'||'|'||'power')::text, '二期供水泵房', '二期供水泵房5#泵', 'power', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房5#泵' AND metric_key='power'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房5#泵'||'|'||'kwh')::text, '二期供水泵房', '二期供水泵房5#泵', 'kwh', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房5#泵' AND metric_key='kwh'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房5#泵'||'|'||'power_factor')::text, '二期供水泵房', '二期供水泵房5#泵', 'power_factor', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房5#泵' AND metric_key='power_factor'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房6#泵'||'|'||'frequency')::text, '二期供水泵房', '二期供水泵房6#泵', 'frequency', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房6#泵' AND metric_key='frequency'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房6#泵'||'|'||'voltage_a')::text, '二期供水泵房', '二期供水泵房6#泵', 'voltage_a', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房6#泵' AND metric_key='voltage_a'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房6#泵'||'|'||'current_a')::text, '二期供水泵房', '二期供水泵房6#泵', 'current_a', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房6#泵' AND metric_key='current_a'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房6#泵'||'|'||'voltage_b')::text, '二期供水泵房', '二期供水泵房6#泵', 'voltage_b', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房6#泵' AND metric_key='voltage_b'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房6#泵'||'|'||'current_b')::text, '二期供水泵房', '二期供水泵房6#泵', 'current_b', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房6#泵' AND metric_key='current_b'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房6#泵'||'|'||'voltage_c')::text, '二期供水泵房', '二期供水泵房6#泵', 'voltage_c', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房6#泵' AND metric_key='voltage_c'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房6#泵'||'|'||'current_c')::text, '二期供水泵房', '二期供水泵房6#泵', 'current_c', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房6#泵' AND metric_key='current_c'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房6#泵'||'|'||'power')::text, '二期供水泵房', '二期供水泵房6#泵', 'power', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房6#泵' AND metric_key='power'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房6#泵'||'|'||'kwh')::text, '二期供水泵房', '二期供水泵房6#泵', 'kwh', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房6#泵' AND metric_key='kwh'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房6#泵'||'|'||'power_factor')::text, '二期供水泵房', '二期供水泵房6#泵', 'power_factor', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房6#泵' AND metric_key='power_factor'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房总管'||'|'||'pressure')::text, '二期供水泵房', '二期供水泵房总管', 'pressure', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房总管' AND metric_key='pressure'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房总管'||'|'||'flow_rate')::text, '二期供水泵房', '二期供水泵房总管', 'flow_rate', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房总管' AND metric_key='flow_rate'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期供水泵房'||'|'||'二期供水泵房总管'||'|'||'cumulative_flow')::text, '二期供水泵房', '二期供水泵房总管', 'cumulative_flow', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期供水泵房' AND device_name='二期供水泵房总管' AND metric_key='cumulative_flow'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房1#泵'||'|'||'voltage_a')::text, '二期取水泵房', '二期取水泵房1#泵', 'voltage_a', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房1#泵' AND metric_key='voltage_a'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房1#泵'||'|'||'current_a')::text, '二期取水泵房', '二期取水泵房1#泵', 'current_a', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房1#泵' AND metric_key='current_a'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房1#泵'||'|'||'voltage_b')::text, '二期取水泵房', '二期取水泵房1#泵', 'voltage_b', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房1#泵' AND metric_key='voltage_b'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房1#泵'||'|'||'current_b')::text, '二期取水泵房', '二期取水泵房1#泵', 'current_b', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房1#泵' AND metric_key='current_b'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房1#泵'||'|'||'voltage_c')::text, '二期取水泵房', '二期取水泵房1#泵', 'voltage_c', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房1#泵' AND metric_key='voltage_c'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房1#泵'||'|'||'current_c')::text, '二期取水泵房', '二期取水泵房1#泵', 'current_c', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房1#泵' AND metric_key='current_c'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房1#泵'||'|'||'power')::text, '二期取水泵房', '二期取水泵房1#泵', 'power', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房1#泵' AND metric_key='power'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房1#泵'||'|'||'kwh')::text, '二期取水泵房', '二期取水泵房1#泵', 'kwh', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房1#泵' AND metric_key='kwh'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房1#泵'||'|'||'power_factor')::text, '二期取水泵房', '二期取水泵房1#泵', 'power_factor', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房1#泵' AND metric_key='power_factor'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房2#泵'||'|'||'frequency')::text, '二期取水泵房', '二期取水泵房2#泵', 'frequency', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房2#泵' AND metric_key='frequency'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房2#泵'||'|'||'voltage_a')::text, '二期取水泵房', '二期取水泵房2#泵', 'voltage_a', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房2#泵' AND metric_key='voltage_a'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房2#泵'||'|'||'current_a')::text, '二期取水泵房', '二期取水泵房2#泵', 'current_a', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房2#泵' AND metric_key='current_a'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房2#泵'||'|'||'voltage_b')::text, '二期取水泵房', '二期取水泵房2#泵', 'voltage_b', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房2#泵' AND metric_key='voltage_b'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房2#泵'||'|'||'current_b')::text, '二期取水泵房', '二期取水泵房2#泵', 'current_b', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房2#泵' AND metric_key='current_b'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房2#泵'||'|'||'voltage_c')::text, '二期取水泵房', '二期取水泵房2#泵', 'voltage_c', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房2#泵' AND metric_key='voltage_c'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房2#泵'||'|'||'current_c')::text, '二期取水泵房', '二期取水泵房2#泵', 'current_c', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房2#泵' AND metric_key='current_c'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房2#泵'||'|'||'power')::text, '二期取水泵房', '二期取水泵房2#泵', 'power', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房2#泵' AND metric_key='power'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房2#泵'||'|'||'kwh')::text, '二期取水泵房', '二期取水泵房2#泵', 'kwh', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房2#泵' AND metric_key='kwh'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房2#泵'||'|'||'power_factor')::text, '二期取水泵房', '二期取水泵房2#泵', 'power_factor', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房2#泵' AND metric_key='power_factor'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房3#泵'||'|'||'voltage_a')::text, '二期取水泵房', '二期取水泵房3#泵', 'voltage_a', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房3#泵' AND metric_key='voltage_a'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房3#泵'||'|'||'current_a')::text, '二期取水泵房', '二期取水泵房3#泵', 'current_a', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房3#泵' AND metric_key='current_a'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房3#泵'||'|'||'voltage_b')::text, '二期取水泵房', '二期取水泵房3#泵', 'voltage_b', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房3#泵' AND metric_key='voltage_b'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房3#泵'||'|'||'current_b')::text, '二期取水泵房', '二期取水泵房3#泵', 'current_b', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房3#泵' AND metric_key='current_b'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房3#泵'||'|'||'voltage_c')::text, '二期取水泵房', '二期取水泵房3#泵', 'voltage_c', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房3#泵' AND metric_key='voltage_c'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房3#泵'||'|'||'current_c')::text, '二期取水泵房', '二期取水泵房3#泵', 'current_c', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房3#泵' AND metric_key='current_c'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房3#泵'||'|'||'power')::text, '二期取水泵房', '二期取水泵房3#泵', 'power', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房3#泵' AND metric_key='power'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房3#泵'||'|'||'kwh')::text, '二期取水泵房', '二期取水泵房3#泵', 'kwh', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房3#泵' AND metric_key='kwh'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房3#泵'||'|'||'power_factor')::text, '二期取水泵房', '二期取水泵房3#泵', 'power_factor', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房3#泵' AND metric_key='power_factor'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房4#泵'||'|'||'voltage_a')::text, '二期取水泵房', '二期取水泵房4#泵', 'voltage_a', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房4#泵' AND metric_key='voltage_a'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房4#泵'||'|'||'current_a')::text, '二期取水泵房', '二期取水泵房4#泵', 'current_a', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房4#泵' AND metric_key='current_a'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房4#泵'||'|'||'voltage_b')::text, '二期取水泵房', '二期取水泵房4#泵', 'voltage_b', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房4#泵' AND metric_key='voltage_b'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房4#泵'||'|'||'current_b')::text, '二期取水泵房', '二期取水泵房4#泵', 'current_b', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房4#泵' AND metric_key='current_b'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房4#泵'||'|'||'voltage_c')::text, '二期取水泵房', '二期取水泵房4#泵', 'voltage_c', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房4#泵' AND metric_key='voltage_c'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房4#泵'||'|'||'current_c')::text, '二期取水泵房', '二期取水泵房4#泵', 'current_c', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房4#泵' AND metric_key='current_c'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房4#泵'||'|'||'power')::text, '二期取水泵房', '二期取水泵房4#泵', 'power', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房4#泵' AND metric_key='power'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房4#泵'||'|'||'kwh')::text, '二期取水泵房', '二期取水泵房4#泵', 'kwh', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房4#泵' AND metric_key='kwh'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房4#泵'||'|'||'power_factor')::text, '二期取水泵房', '二期取水泵房4#泵', 'power_factor', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房4#泵' AND metric_key='power_factor'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房5#泵'||'|'||'frequency')::text, '二期取水泵房', '二期取水泵房5#泵', 'frequency', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房5#泵' AND metric_key='frequency'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房5#泵'||'|'||'voltage_a')::text, '二期取水泵房', '二期取水泵房5#泵', 'voltage_a', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房5#泵' AND metric_key='voltage_a'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房5#泵'||'|'||'current_a')::text, '二期取水泵房', '二期取水泵房5#泵', 'current_a', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房5#泵' AND metric_key='current_a'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房5#泵'||'|'||'voltage_b')::text, '二期取水泵房', '二期取水泵房5#泵', 'voltage_b', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房5#泵' AND metric_key='voltage_b'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房5#泵'||'|'||'current_b')::text, '二期取水泵房', '二期取水泵房5#泵', 'current_b', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房5#泵' AND metric_key='current_b'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房5#泵'||'|'||'voltage_c')::text, '二期取水泵房', '二期取水泵房5#泵', 'voltage_c', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房5#泵' AND metric_key='voltage_c'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房5#泵'||'|'||'current_c')::text, '二期取水泵房', '二期取水泵房5#泵', 'current_c', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房5#泵' AND metric_key='current_c'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房5#泵'||'|'||'power')::text, '二期取水泵房', '二期取水泵房5#泵', 'power', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房5#泵' AND metric_key='power'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房5#泵'||'|'||'kwh')::text, '二期取水泵房', '二期取水泵房5#泵', 'kwh', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房5#泵' AND metric_key='kwh'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'二期取水泵房5#泵'||'|'||'power_factor')::text, '二期取水泵房', '二期取水泵房5#泵', 'power_factor', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='二期取水泵房5#泵' AND metric_key='power_factor'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'总管'||'|'||'flow_rate')::text, '二期取水泵房', '总管', 'flow_rate', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='总管' AND metric_key='flow_rate'
);
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('二期取水泵房'||'|'||'总管'||'|'||'cumulative_flow')::text, '二期取水泵房', '总管', 'cumulative_flow', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='二期取水泵房' AND device_name='总管' AND metric_key='cumulative_flow'
);
COMMIT;
