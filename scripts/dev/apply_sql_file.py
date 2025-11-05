from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root on sys.path so we can import app.*
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config.loader import load_settings
from app.adapters.db.gateway import get_conn


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Apply a SQL file against the configured database")
    parser.add_argument("sql_file", type=str, help="Path to .sql file (relative to repo root)")
    args = parser.parse_args(argv)

    sql_path = Path(args.sql_file)
    if not sql_path.exists():
        print(f"[ERROR] SQL file not found: {sql_path}")
        return 1

    settings = load_settings(Path("configs"))
    sql_text = sql_path.read_text(encoding="utf-8")

    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(sql_text)
        conn.commit()
    print(f"[OK] Applied SQL: {sql_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

