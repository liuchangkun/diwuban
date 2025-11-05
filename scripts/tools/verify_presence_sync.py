from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn
from app.services.reporting.presence_writer import upsert_window


def main() -> int:
    settings = load_settings(Path("configs"))
    # 选取一个有最近数据的设备与泵站
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.name AS station_name, d.name AS device_name, max(f.ts_bucket) AS last_ts
                FROM public.fact_measurements f
                JOIN public.dim_devices d ON d.id = f.device_id
                JOIN public.dim_stations s ON s.id = d.station_id
                GROUP BY s.name, d.name
                ORDER BY last_ts DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()
            if not row:
                print("[verify] 无 fact 数据，跳过验证")
                return 0
            station_name, device_name, last_ts = row
    # 设定一个极小窗口 [last_ts-5s, last_ts+1s)
    start = (last_ts - timedelta(seconds=5)).astimezone(timezone.utc)
    end = (last_ts + timedelta(seconds=1)).astimezone(timezone.utc)
    with get_conn(settings) as conn:
        affected = upsert_window(conn, start, end, station_name, device_name)
        print(
            f"[verify] station={station_name} device={device_name} window=[{start.isoformat()},{end.isoformat()}) affected={affected}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

