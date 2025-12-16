import pathlib
import sys

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn

SQL_PATH = pathlib.Path("scripts/sql/migrations/040_create_quality_diagnosis_log_and_wrapper.sql")

def main() -> None:
    if not SQL_PATH.exists():
        print(f"migration file not found: {SQL_PATH}")
        sys.exit(1)
    sql = SQL_PATH.read_text(encoding="utf-8")
    settings = load_settings(pathlib.Path("configs"))
    with get_conn(settings) as conn:
        try:
            # 确保可执行 BEGIN/COMMIT 多语句
            try:
                conn.autocommit = True  # type: ignore[attr-defined]
            except Exception:
                pass
            with conn.cursor() as cur:
                cur.execute(sql)
        except Exception as e:
            print(f"MIGRATION_FAILED: {e}")
            sys.exit(2)
    print("MIGRATION_OK")

if __name__ == "__main__":
    main()

