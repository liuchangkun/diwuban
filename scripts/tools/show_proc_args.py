from pathlib import Path
from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def main():
    settings = load_settings(Path("configs"))
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT p.proname, pg_catalog.pg_get_function_identity_arguments(p.oid) "
                "FROM pg_catalog.pg_proc p "
                "JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace "
                "WHERE n.nspname='public' AND p.proname IN ('sp_mark_quality_window','sp_mark_quality_window_vfast')"
            )
            for name, args in cur.fetchall():
                print(name, args)


if __name__ == "__main__":
    main()

