from __future__ import annotations

import json
from datetime import timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn
from app.services.device_running_job import DeviceRunningJob, JobConfig


def find_last_day_window(settings):
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(ts_bucket) FROM public.fact_measurements")
            row = cur.fetchone()
            if not row or row[0] is None:
                return None
            end = row[0].replace(tzinfo=timezone.utc, microsecond=0)
            start = (end - timedelta(days=1)).replace(tzinfo=timezone.utc)
            return start, end


def summarize_mv(settings, start, end):
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM public.mv_device_running_1s
                WHERE ts_bucket >= %s AND ts_bucket < %s
                """,
                (start, end),
            )
            total_rows = int(cur.fetchone()[0])

            cur.execute(
                """
                SELECT device_id, COUNT(*) AS c
                FROM public.mv_device_running_1s
                WHERE ts_bucket >= %s AND ts_bucket < %s
                GROUP BY device_id
                ORDER BY device_id
                LIMIT 20
                """,
                (start, end),
            )
            by_device = [(int(r[0]), int(r[1])) for r in (cur.fetchall() or [])]

            cur.execute(
                """
                SELECT station_id, device_id, ts_bucket, running, phase
                FROM public.mv_device_running_1s
                WHERE ts_bucket >= %s AND ts_bucket < %s
                ORDER BY ts_bucket ASC
                LIMIT 10
                """,
                (start, end),
            )
            sample = [
                {
                    "station_id": int(r[0]),
                    "device_id": int(r[1]),
                    "ts": r[2].isoformat(),
                    "running": int(r[3]) if r[3] is not None else None,
                    "phase": int(r[4]) if r[4] is not None else None,
                }
                for r in (cur.fetchall() or [])
            ]

    return {"total_rows": total_rows, "by_device": by_device, "sample": sample}


def main() -> int:
    settings = load_settings(Path("configs"))
    win = find_last_day_window(settings)
    if not win:
        print(json.dumps({"status": "no_fact_data"}, ensure_ascii=False))
        return 0
    start, end = win

    job = DeviceRunningJob(settings, JobConfig(slice_granularity="day"))
    job.run(device_ids=None, start_ts=start, end_ts=end)

    summary = summarize_mv(settings, start, end)
    out = {"status": "ok", "start": start.isoformat(), "end": end.isoformat(), **summary}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

