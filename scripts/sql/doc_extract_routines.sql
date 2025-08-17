\pset format unaligned
\pset tuples_only on
\o docs/_routines.tsv
SELECT n.nspname AS schema,
       p.proname AS routine,
       pg_get_function_arguments(p.oid) AS args,
       pg_catalog.format_type(p.prorettype, NULL) AS return_type,
       COALESCE(d.description, '') AS comment
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
LEFT JOIN pg_description d ON d.objoid = p.oid AND d.objsubid = 0
WHERE n.nspname IN ('public','reporting','monitoring','api')
ORDER BY 1,2;
\o
