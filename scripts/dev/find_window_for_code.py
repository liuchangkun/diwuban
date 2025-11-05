from __future__ import annotations

import datetime as dt
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
    code = int(sys.argv[1]) if len(sys.argv) > 1 else 702

    s = load_settings(Path("configs"))
    with get_conn(s) as c:
        with c.cursor() as cur:
            # recent 2 hours window
            cur.execute("SELECT MAX(ts_bucket) FROM public.fact_measurements")
            max_ts = cur.fetchone()[0]
            if not max_ts:
                print(json.dumps({"ok": False, "error": "no data"}))
                return 0
            start = max_ts - dt.timedelta(hours=2)
            end = max_ts

            # top device in window
            cur.execute(
                """
                SELECT device_id, COUNT(*) AS cnt
                FROM public.fact_measurements
                WHERE ts_bucket >= %s AND ts_bucket < %s
                GROUP BY device_id ORDER BY cnt DESC LIMIT 1
                """,
                (start, end),
            )
            row = cur.fetchone()
            if not row:
                print(json.dumps({"ok": False, "error": "no device in window"}))
                return 0
            device_id = int(row[0])

            # any rows with target code in that window and device?
            cur.execute(
                """
                SELECT MIN(ts_bucket), MAX(ts_bucket), COUNT(*)
                FROM public.fact_measurements
                WHERE device_id=%s AND ts_bucket >= %s AND ts_bucket < %s AND quality_status=%s
                """,
                (device_id, start, end, code),
            )
            m = cur.fetchone()
            if m and m[2] and int(m[2]) > 0:
                ws = m[0]
                if ws.tzinfo is None:
                    ws = ws.replace(tzinfo=dt.timezone.utc)
                else:
                    ws = ws.astimezone(dt.timezone.utc)
                we = ws + dt.timedelta(minutes=5)
                print(
                    json.dumps(
                        {
                            "ok": True,
                            "code": code,
                            "device_id": device_id,
                            "ws": ws.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "we": we.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        }
                    )
                )
                return 0

            print(
                json.dumps(
                    {
                        "ok": False,
                        "code": code,
                        "device_id": device_id,
                        "ws": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "we": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "error": "no rows with target code in last 2h",
                    }
                )
            )
            return 0


if __name__ == "__main__":
    raise SystemExit(main())

