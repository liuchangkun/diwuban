-- 验证表结构和注释
\dt
\d+ dim_stations
\d+ dim_devices
\d+ dim_metric_config
\d+ device_rated_params
\d+ fact_measurements

-- 查看表注释
SELECT schemaname, tablename, obj_description(oid) as table_comment
FROM pg_tables pt
JOIN pg_class pc ON pc.relname = pt.tablename
WHERE schemaname = 'public'
ORDER BY tablename;

-- 查看字段注释示例（dim_devices表）
SELECT
    c.column_name,
    c.data_type,
    c.is_nullable,
    col_description('public.dim_devices'::regclass, c.ordinal_position) AS column_comment
FROM information_schema.columns c
WHERE c.table_schema='public' AND c.table_name='dim_devices'
ORDER BY c.ordinal_position;
