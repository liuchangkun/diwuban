import sys
from pathlib import Path
from datetime import timedelta

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def main():
    station_id = 1
    device_id = 5
    settings = load_settings(Path("configs"))

    # 设备时间跨度（按天跑）
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT date_trunc('day', MIN(ts_bucket)) AS d0,
                       date_trunc('day', MAX(ts_bucket)) AS d1
                FROM public.fact_measurements
                WHERE station_id=%s AND device_id=%s
                """,
                (station_id, device_id),
            )
            d0, d1 = cur.fetchone()
            if not d0 or not d1:
                print({"ok": False, "msg": "no data for device"})
                return

    # 逐日
    day = d0
    while day <= d1:
        s = day
        e = day + timedelta(days=1)
        print({"day": s.isoformat()})
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                # 刷新运行态/存在性
                cur.execute(
                    "CALL public.sp_refresh_mv_running_presence(%s,%s,%s,%s)",
                    (s, e, station_id, device_id),
                )
                conn.commit()

        # 按 10 分钟分块跑 vfast（内联执行，避免子进程导入问题）
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                t = s
                step = timedelta(minutes=10)
                while t < e:
                    s2 = t
                    e2 = min(t + step, e)
                    # 重置 + vfast 标注
                    cur.execute(
                        "CALL public.sp_reset_quality_window(%s,%s,%s,%s)",
                        (s2, e2, station_id, device_id),
                    )
                    cur.execute(
                        "CALL public.sp_mark_quality_window_vfast(%s,%s,%s,%s)",
                        (s2, e2, station_id, device_id),
                    )
                    conn.commit()
                    t = e2

        # 每天结束导出 CSV（分布+样例）
        from subprocess import run

        run(
            [
                sys.executable,
                str(ROOT / "scripts" / "dev" / "export_eval_csv.py"),
                "--station-id",
                str(station_id),
                "--device-id",
                str(device_id),
                "--start",
                s.isoformat(),
                "--end",
                e.isoformat(),
            ],
            check=True,
        )

        day = e

    print({"ok": True})


if __name__ == "__main__":
    main()
