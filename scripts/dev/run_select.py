from __future__ import annotations

import json
import sys
from pathlib import Path

# import project
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.config.loader_new import load_settings
from app.adapters.db import get_connection


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python scripts/dev/run_select.py <sql_file>")
        return 2
    sql_path = Path(sys.argv[1])
    if not sql_path.exists():
        print(f"file not found: {sql_path}")
        return 2
    sql = sql_path.read_text(encoding="utf-8")
    rows_out = []
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            try:
                rows = cur.fetchall()
            except Exception:
                rows = []
            # best-effort columns names
            try:
                cols = [d[0] for d in cur.description]
            except Exception:
                cols = []
            for r in rows:
                if cols and len(cols) == len(r):
                    rows_out.append({cols[i]: (list(r[i]) if isinstance(r[i], (list, tuple)) else r[i]) for i in range(len(cols))})
                else:
                    rows_out.append([*(r if isinstance(r, (list, tuple)) else (r,))])
    print(json.dumps(rows_out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

