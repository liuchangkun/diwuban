from __future__ import annotations

import sys

import psycopg

from app.core.config.loader import Settings


def main() -> None:
    # 严格按配置驱动：不在代码中保存任何连接信息，不拼接 DSN 字符串
    settings = Settings()
    conn = None
    try:
        if getattr(settings.db, "dsn_read", None):
            conn = psycopg.connect(settings.db.dsn_read)
        else:
            conn = psycopg.connect(
                host=settings.db.host,
                dbname=settings.db.name,
                user=settings.db.user,
            )
        with conn:
            with conn.cursor() as cur:
                cur.execute("select current_database(), current_user, current_schema()")
                db, user, schema = cur.fetchone()
                print(f"DB_OK db={db} user={user} schema={schema}")
                cur.execute(
                    """
                    select count(*) from information_schema.tables
                    where table_schema='public'
                      and table_name in ('fact_measurements','dim_devices','dim_stations','dim_metric_config')
                    """
                )
                count = cur.fetchone()[0]
                print(f"PUBLIC_CORE_TABLES_FOUND={count}")
    except Exception as e:
        raise SystemExit(f"DB_PROBE_ERROR: {e}")
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"DB_PROBE_ERROR: {e}")
        sys.exit(2)
