from __future__ import annotations

import json
from datetime import timedelta, timezone
from pathlib import Path
import sys

# Ensure repo root on sys.path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config.loader import load_settings
from app.adapters.db.gateway import get_conn
from app.services.device_running_job import DeviceRunningJob, JobConfig


def pick_device_and_window(settings):
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH cand AS (
                  SELECT d.device_id
                  FROM public.device_running_thresholds d
                )
                SELECT f.device_id,
                       MIN(f.ts_bucket) AS mn,
                       MAX(f.ts_bucket) AS mx
                FROM public.fact_measurements f
                JOIN cand ON cand.device_id=f.device_id
                GROUP BY f.device_id
                HAVING COUNT(*)>0
                ORDER BY MAX(f.ts_bucket) DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()
            if not row:
                return None
            did, mn, mx = int(row[0]), row[1], row[2]
            # choose 1-day window ending at mx (UTC, second aligned)
            end = mx.replace(tzinfo=timezone.utc, microsecond=0)
            start = (end - timedelta(days=1)).replace(tzinfo=timezone.utc)
            if start < mn:
                start = mn.replace(tzinfo=timezone.utc, microsecond=0)
            return did, start, end


def main() -> int:
    settings = load_settings(Path("configs"))
    picked = pick_device_and_window(settings)
    if not picked:
        print(json.dumps({"status": "no_device_with_data"}, ensure_ascii=False))
        return 0
    device_id, start, end = picked

    # Run job for this device and window
    job = DeviceRunningJob(settings, JobConfig(slice_granularity="day"))
    job.run(device_ids=[device_id], start_ts=start, end_ts=end)

    # Verify rows in mv_device_running_1s
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) FROM public.mv_device_running_1s
                WHERE device_id=%s AND ts_bucket>=%s AND ts_bucket<%s
                """,
                (device_id, start, end),
            )
            cnt = int(cur.fetchone()[0])
            cur.execute(
                """
                SELECT station_id, device_id, ts_bucket, running, phase
                FROM public.mv_device_running_1s
                WHERE device_id=%s AND ts_bucket>=%s AND ts_bucket<%s
                ORDER BY ts_bucket ASC
                LIMIT 5
                """,
                (device_id, start, end),
            )
            sample = cur.fetchall() or []
    out = {
        "status": "ok",
        "device_id": device_id,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "rows": cnt,
        "sample": [
            {
                "station_id": r[0],
                "device_id": r[1],
                "ts": r[2].isoformat() if r[2] else None,
                "running": int(r[3]) if r[3] is not None else None,
                "phase": int(r[4]) if r[4] is not None else None,
            }
            for r in sample
        ],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

