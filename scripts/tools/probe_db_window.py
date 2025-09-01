from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from app.adapters.db.gateway import get_conn
from app.core.config.loader_new import load_settings


def main() -> None:
    settings = load_settings(Path("configs"))
    out: dict = {}
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM public.staging_raw")
            out["staging_count"] = int(cur.fetchone()[0])
        with conn.cursor() as cur:
            cur.execute("SELECT count(*), min(ts_raw), max(ts_raw) FROM public.fact_measurements")
            row = cur.fetchone()
            out["fact_count"] = int(row[0])
            out["fact_min_ts"] = row[1].isoformat() if row[1] else None
            out["fact_max_ts"] = row[2].isoformat() if row[2] else None
        with conn.cursor() as cur:
            cur.execute("SELECT id, station_id FROM public.dim_devices ORDER BY id LIMIT 1")
            r = cur.fetchone()
            out["device_id"] = int(r[0]) if r else None
            out["station_id"] = int(r[1]) if r else None
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()

