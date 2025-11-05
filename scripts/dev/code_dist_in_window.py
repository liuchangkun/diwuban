from __future__ import annotations

import json
import sys
from pathlib import Path

# ensure repo root
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def main() -> int:
    if len(sys.argv) < 4:
        print("usage: python scripts/dev/code_dist_in_window.py <wsZ> <weZ> <device_id>")
        return 2
    ws = sys.argv[1]
    we = sys.argv[2]
    device_id = int(sys.argv[3]) if sys.argv[3] not in ("", "None", "null") else None

    s = load_settings(Path("configs"))
    with get_conn(s) as c:
        with c.cursor() as cur:
            cur.execute(
                """
                SELECT quality_status, COUNT(*)
                FROM public.fact_measurements
                WHERE ts_bucket >= %s AND ts_bucket < %s AND device_id = %s
                  AND COALESCE(quality_status,0) > 0
                GROUP BY quality_status
                ORDER BY quality_status
                """,
                (ws, we, device_id),
            )
            rows = cur.fetchall()
    dist = {int(r[0]): int(r[1]) for r in rows}
    print(json.dumps({"window": {"start": ws, "end": we, "device_id": device_id}, "dist": dist}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

