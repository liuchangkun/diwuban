from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

# ensure repo root on sys.path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.adapters.db.gateway import get_conn
from app.core.config.loader_new import load_settings


def main() -> None:
    s = load_settings(Path("configs"))
    with get_conn(s) as c:
        with c.cursor() as cur:
            cur.execute(
                "SELECT MIN(ts_bucket), MAX(ts_bucket) FROM public.fact_measurements"
            )
            ws, we = cur.fetchone()
            if not ws or not we:
                print(json.dumps({"ws": None, "we": None, "device_id": None}))
                return
            start = we - dt.timedelta(minutes=5)
            end = we
            # normalize to UTC Z
            if start.tzinfo is None:
                start = start.replace(tzinfo=dt.timezone.utc)
            else:
                start = start.astimezone(dt.timezone.utc)
            if end.tzinfo is None:
                end = end.replace(tzinfo=dt.timezone.utc)
            else:
                end = end.astimezone(dt.timezone.utc)
            cur.execute(
                """
                SELECT device_id, COUNT(*) AS cnt
                FROM public.fact_measurements
                WHERE ts_bucket >= %s AND ts_bucket < %s
                GROUP BY device_id
                ORDER BY cnt DESC
                LIMIT 1
                """,
                (start, end),
            )
            r = cur.fetchone()
            device_id = int(r[0]) if r else None
            print(
                json.dumps(
                    {
                        "ws": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "we": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "device_id": device_id,
                    }
                )
            )


if __name__ == "__main__":
    main()
