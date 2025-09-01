from __future__ import annotations
import logging
from app.adapters.db.gateway import get_conn
from app.core.config.loader import Settings

logger = logging.getLogger(__name__)


SQL_TRUNCATE_PUBLIC = r"""
DO $$
DECLARE r RECORD;
BEGIN
  -- 逐表 TRUNCATE，包含分区表父子（CASCADE），并重置自增序列
  FOR r IN
    SELECT n.nspname AS schema_name, c.relname AS table_name
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relkind = 'r' AND n.nspname = 'public'
  LOOP
    EXECUTE format('TRUNCATE TABLE %I.%I RESTART IDENTITY CASCADE;', r.schema_name, r.table_name);
  END LOOP;
END $$;
"""


def truncate_public_schema(settings: Settings) -> None:
    """清空 public 架构下所有表数据（TRUNCATE + RESTART IDENTITY + CASCADE）。
    注意：不删除表/索引/视图/函数，不触达系统 schema。
    """
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL_TRUNCATE_PUBLIC)
        conn.commit()
    logger.warning(
        "已清空 public 架构所有表数据", extra={"event": "admin.truncate.public"}
    )
