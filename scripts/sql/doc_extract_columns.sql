\pset format unaligned
\pset tuples_only on
\o docs/_columns.tsv
SELECT n.nspname AS schema,
       c.relname AS table,
       a.attname AS column,
       pg_catalog.format_type(a.atttypid,a.atttypmod) AS data_type,
       CASE WHEN a.attnotnull THEN 'NO' ELSE 'YES' END AS is_nullable,
       COALESCE(pg_get_expr(ad.adbin, ad.adrelid), '') AS column_default,
       COALESCE(d.description, '') AS comment
FROM pg_attribute a
JOIN pg_class c ON c.oid=a.attrelid
JOIN pg_namespace n ON n.oid=c.relnamespace
LEFT JOIN pg_attrdef ad ON ad.adrelid=a.attrelid AND ad.adnum=a.attnum
LEFT JOIN pg_description d ON d.objoid=a.attrelid AND d.objsubid=a.attnum
WHERE a.attnum>0 AND NOT a.attisdropped
  AND n.nspname IN ('public','reporting','monitoring','api')
  AND c.relkind IN ('r','m')
ORDER BY 1,2,a.attnum;
\o
