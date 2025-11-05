from __future__ import annotations

import sys
from pathlib import Path

# 确保可导入 app/*
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python scripts/dev/apply_sql.py <sql_file>")
        return 2
    sql_path = Path(sys.argv[1])
    if not sql_path.exists():
        print(f"file not found: {sql_path}")
        return 2
    sql = sql_path.read_text(encoding="utf-8")
    settings = load_settings(Path("configs"))
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    print(f"applied: {sql_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
