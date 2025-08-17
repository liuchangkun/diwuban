-- Phase1: 调整叶子分区存储参数（fillfactor/autovacuum 等）
DO $$
DECLARE r record;
BEGIN
  FOR r IN (
    SELECT n.nspname AS schemaname, c.relname AS part_name
    FROM pg_partition_tree('public.fact_measurements') t
    JOIN pg_class c ON c.oid = t.relid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE t.isleaf
  ) LOOP
    EXECUTE format(
      'ALTER TABLE %I.%I SET (
         fillfactor=70,
         autovacuum_vacuum_scale_factor=0.05,
         autovacuum_analyze_scale_factor=0.02,
         autovacuum_vacuum_cost_delay=5,
         autovacuum_vacuum_cost_limit=2000,
         autovacuum_vacuum_threshold=1000
       )',
      r.schemaname, r.part_name
    );
  END LOOP;
END $$;
