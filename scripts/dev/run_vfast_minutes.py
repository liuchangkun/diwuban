import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def main():
    station_id = 1
    device_id = 5
    # 读取该设备可见时间跨度
    settings = load_settings(Path("configs"))
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT MIN(ts_bucket), MAX(ts_bucket)
                FROM public.fact_measurements
                WHERE station_id=%s AND device_id=%s
                """,
                (station_id, device_id),
            )
            r = cur.fetchone()
            if not r or not r[0] or not r[1]:
                print({"ok": False, "msg": "no data for device"})
                return
            start = r[0]
            end = r[1] + timedelta(seconds=1)  # exclusive upper bound

    # 为了演示，限制在前 120 分钟（如需全量，去掉 [:120]）
    minutes = []
    t = start.replace(second=0, microsecond=0)
    while t < end:
        minutes.append((t, t + timedelta(minutes=1)))
        t += timedelta(minutes=1)

    # 只跑前 120 分钟，避免一次执行过长
    batch = minutes[:120]
    total_started = time.time()
    stats = []

    with get_conn(settings) as conn:
        for i, (s, e) in enumerate(batch, 1):
            with conn.cursor() as cur:
                t0 = time.time()
                # 可选：刷新运行态/存在性物化
                cur.execute("CALL public.sp_refresh_mv_running_presence(%s,%s,%s,%s)", (s, e, station_id, device_id))
                conn.commit()

                # 调用 vfast 过程
                cur.execute(
                    "CALL public.sp_mark_quality_window_vfast(%s,%s,%s,%s)",
                    (s, e, station_id, device_id),
                )
                conn.commit()
                dt = time.time() - t0
                stats.append((s, dt))
                print(f"[{i}/{len(batch)}] {s.isoformat()} took {dt:.3f}s")

    total_dt = time.time() - total_started
    worst = max(stats, key=lambda x: x[1]) if stats else None
    print({
        "ok": True,
        "minutes": len(batch),
        "total_seconds": round(total_dt, 3),
        "avg_seconds": round(total_dt / len(batch), 3) if stats else None,
        "worst_minute": worst[0].isoformat() if worst else None,
        "worst_seconds": round(worst[1], 3) if worst else None,
    })


if __name__ == "__main__":
    main()

