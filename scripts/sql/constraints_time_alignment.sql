-- constraints_time_alignment.sql
-- 目的：为 fact_measurements 及其所有现有分区添加“整秒对齐”检查约束
-- 说明：
-- - 约束表达式：date_trunc('second', ts_bucket) = ts_bucket
-- - 在父表与各分区上以 NOT VALID 形式添加，验证可在数据清理后单独执行 VALIDATE CONSTRAINT
-- - 对未来新建的分区，请在分区创建模板中同时添加该 CHECK 约束

BEGIN;

-- 父表添加 CHECK（若不存在）
DO $$
DECLARE
  v_exists boolean;
BEGIN
  SELECT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'ck_fact_measurements_ts_bucket_second'
  ) INTO v_exists;

  IF NOT v_exists THEN
    EXECUTE $$ALTER TABLE ONLY public.fact_measurements
             ADD CONSTRAINT ck_fact_measurements_ts_bucket_second
             CHECK (date_trunc(''second'', ts_bucket) = ts_bucket) NOT VALID$$;
  END IF;
END$$;

-- 为所有现有分区添加相同 CHECK（若不存在）
DO $$
DECLARE
  r RECORD;
  conname text;
  v_exists boolean;
BEGIN
  FOR r IN
    SELECT c.oid AS relid, c.relname, n.nspname
    FROM pg_inherits i
    JOIN pg_class   c ON c.oid = i.inhrelid
    JOIN pg_class   p ON p.oid = i.inhparent AND p.relname = 'fact_measurements'
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
  LOOP
    conname := format('ck_%s_ts_bucket_second', r.relname);
    SELECT EXISTS (
      SELECT 1
      FROM pg_constraint ct
      WHERE ct.conrelid = r.relid AND ct.conname = conname
    ) INTO v_exists;

    IF NOT v_exists THEN
      EXECUTE format(
        'ALTER TABLE %I.%I ADD CONSTRAINT %I CHECK (date_trunc(''second'', ts_bucket) = ts_bucket) NOT VALID',
        'public', r.relname, conname
      );
    END IF;
  END LOOP;
END$$;

COMMIT;

-- 验证示例（建议在数据清理和回归后执行）：
-- ALTER TABLE ONLY public.fact_measurements VALIDATE CONSTRAINT ck_fact_measurements_ts_bucket_second;
-- DO $$
-- DECLARE r RECORD; BEGIN
--   FOR r IN SELECT c.relname FROM pg_inherits i JOIN pg_class c ON c.oid=i.inhrelid WHERE i.inhparent='public.fact_measurements'::regclass LOOP
--     EXECUTE format('ALTER TABLE public.%I VALIDATE CONSTRAINT ck_%s_ts_bucket_second', r.relname, r.relname);
--   END LOOP;
-- END$$;
