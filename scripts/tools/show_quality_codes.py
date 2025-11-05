from __future__ import annotations

from pathlib import Path
from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def main() -> None:
    settings = load_settings(Path("configs"))
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT code, label_zh, category FROM public.quality_code_dict ORDER BY code"
            )
            rows = cur.fetchall()
            print([int(r[0]) for r in rows])
            for c, l, cat in rows:
                print(f"{int(c)}\t{l}\t{cat}")


if __name__ == "__main__":
    main()

