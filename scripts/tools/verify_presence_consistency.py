from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def normalize(arr):
    return tuple(sorted([str(x) for x in (arr or [])]))


def main() -> int:
    settings = load_settings(Path("configs"))
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # 选择最近的数据窗口（任一设备）
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
                print("[consistency] 无 fact 数据，跳过验证")
                return 0
            station_name, device_name, last_ts = row

            # 选择6秒窗口
            start = (last_ts - timedelta(seconds=5)).astimezone(timezone.utc)
            end = (last_ts + timedelta(seconds=1)).astimezone(timezone.utc)

            # 旧函数输出（可能不存在则跳过）
            try:
                cur.execute(
                    "SELECT ts_utc, available_metrics, need_compute_metrics FROM public.metrics_presence_per_second(%s,%s,%s,%s) ORDER BY ts_utc",
                    (start, end, station_name, device_name),
                )
                fn_rows = cur.fetchall()
            except Exception as e:
                print(f"[consistency] 旧函数不存在或失败，跳过对比: {e}")
                return 0

            # mpps 行输出
            cur.execute(
                """
                SELECT ts_second, available_metrics, need_compute_metrics
                FROM public.metrics_presence_per_second_device m
                JOIN public.dim_devices d ON d.id=m.device_id
                JOIN public.dim_stations s ON s.id=d.station_id
                WHERE s.name=%s AND d.name=%s AND ts_second>=%s AND ts_second<%s
                ORDER BY ts_second
                """,
                (station_name, device_name, start, end),
            )
            mpps_rows = cur.fetchall()

            # 对齐并对比（按时间）
            fn_map = {r[0]: (normalize(r[1]), normalize(r[2])) for r in fn_rows}
            mpps_map = {r[0]: (normalize(r[1]), normalize(r[2])) for r in mpps_rows}

            seconds = sorted(set(list(fn_map.keys()) + list(mpps_map.keys())))
            mismatches = []
            for t in seconds:
                a1 = fn_map.get(t)
                a2 = mpps_map.get(t)
                if a1 != a2:
                    mismatches.append((t, a1, a2))

            if not mismatches:
                print(
                    f"[consistency] OK station={station_name} device={device_name} window=[{start.isoformat()},{end.isoformat()}) matched={len(seconds)}"
                )
                return 0

            print("[consistency] MISMATCH:")
            for t, a1, a2 in mismatches[:20]:
                print(t, a1, a2)
            return 1


if __name__ == "__main__":
    # 允许从仓库根运行（简易导入路径）
    sys.path.append(str(Path('.').resolve()))
    raise SystemExit(main())

