from __future__ import annotations

import json
import sys
from pathlib import Path
from datetime import timedelta, datetime

# 允许脚本在仓库根目录运行时导入 app/* (scripts/dev -> scripts -> repo_root)
sys.path.insert(0, str(Path(__file__).resolve().parents[2].resolve()))

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


STATION_NAME = "二期供水泵房"


def main() -> int:
    settings = load_settings(Path("configs"))
    out: dict = {
        "station": STATION_NAME,
        "station_id": None,
        "ts_choice": None,
        "rows": [],
    }

    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # station_id
            cur.execute(
                "SELECT id FROM public.dim_stations WHERE name=%s", (STATION_NAME,)
            )
            row = cur.fetchone()
            if not row:
                print(
                    json.dumps(
                        {"error": "station_not_found", "station": STATION_NAME},
                        ensure_ascii=False,
                    )
                )
                return 2
            station_id = int(row[0])
            out["station_id"] = station_id

            # 最近秒窗口（5秒）
            cur.execute(
                """
                SELECT max(fm.ts_bucket) FROM public.fact_measurements fm
                WHERE fm.station_id=%s
                """,
                (station_id,),
            )
            max_ts = cur.fetchone()[0]
            if not max_ts:
                print(json.dumps({"error": "no_data"}, ensure_ascii=False))
                return 3

            end_ts = max_ts
            start_ts = end_ts - timedelta(seconds=5)

            # 选用窗口末秒，便于汇总
            ts_choice = end_ts
            out["ts_choice"] = ts_choice.isoformat()

            # 设备名->ID 映射（该站）
            cur.execute(
                "SELECT name, id FROM public.dim_devices WHERE station_id=%s ORDER BY id",
                (station_id,),
            )
            dev_map = {name: int(did) for name, did in cur.fetchall()}

            # presence 明细（设备×秒）：该站、该秒
            cur.execute(
                (
                    "SELECT device, ts_local, need_compute_metrics, available_metrics "
                    "FROM public.metrics_presence_per_second(%s, %s, %s, NULL) "
                    "WHERE ts_local = to_char((%s AT TIME ZONE 'Asia/Shanghai'), 'YYYY-MM-DD HH24:MI:SS') || '+08' "
                    "ORDER BY device"
                ),
                (start_ts, end_ts, STATION_NAME, ts_choice),
            )
            rows = cur.fetchall()

            # 生成“存表行”：station_id, ts_second(UTC), device_id, available_metrics[], need_compute_metrics[]
            for device_name, ts_local, need_metrics, avail_metrics in rows:
                device_id = dev_map.get(device_name)
                if device_id is None:
                    # 跳过不在该站映射内的设备
                    continue
                out["rows"].append(
                    {
                        "station_id": station_id,
                        "ts_second": ts_choice.isoformat(),  # 存 UTC 秒
                        "device_id": device_id,
                        "available_metrics": avail_metrics or [],
                        "need_compute_metrics": need_metrics or [],
                    }
                )

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
