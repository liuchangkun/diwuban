\encoding UTF8
SET client_encoding = 'UTF8';

-- 为分区与 staging 表添加注释（其余对象已注释）

-- 周分区父表注释已存在于 fact_measurements；为各周分区添加简要注释
DO $$
DECLARE r record;
BEGIN
  FOR r IN SELECT relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
           WHERE n.nspname='public' AND relkind='p' AND relname LIKE 'fact_measurements_%'
  LOOP
    EXECUTE format('COMMENT ON TABLE public.%I IS %L', r.relname, '时序事实-周分区');
  END LOOP;
END $$;

-- 叶子子分区注释
DO $$
DECLARE r record;
BEGIN
  FOR r IN SELECT relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
           WHERE n.nspname='public' AND relkind='r' AND relname LIKE 'fact_measurements_%_p%'
  LOOP
    EXECUTE format('COMMENT ON TABLE public.%I IS %L', r.relname, '时序事实-周分区-站点HASH子分区');
  END LOOP;
END $$;

-- staging 表
COMMENT ON TABLE public.staging_raw IS '导入阶段原始数据（UNLOGGED，临时用）';
COMMENT ON TABLE public.staging_rejects IS '导入阶段拒绝/错误记录（UNLOGGED，临时用）';

