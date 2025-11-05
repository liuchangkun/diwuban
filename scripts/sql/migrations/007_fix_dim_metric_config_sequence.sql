-- 修复 dim_metric_config.id 序列与现有数据的偏移，避免插入时主键冲突
-- 幂等：重复执行不会报错

DO $$
DECLARE
  seq_name text;
  max_id bigint;
BEGIN
  SELECT pg_get_serial_sequence('public.dim_metric_config','id') INTO seq_name;
  IF seq_name IS NULL THEN
    RAISE NOTICE 'dim_metric_config.id 无序列（可能为 identity），跳过 setval';
    RETURN;
  END IF;
  EXECUTE 'SELECT COALESCE(MAX(id),0) FROM public.dim_metric_config' INTO max_id;
  IF max_id IS NULL THEN
    max_id := 0;
  END IF;
  -- 将 nextval 对齐到 max(id)+1
  PERFORM setval(seq_name, max_id, TRUE);
  RAISE NOTICE '对齐序列 % 至 %（next 将返回 max+1）', seq_name, max_id;
END $$;

