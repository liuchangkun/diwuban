from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from app.adapters.db.gateway import get_conn
from app.core.config.loader import load_settings

ROOT = Path(".")
SQL_FN = ROOT / "scripts" / "sql" / "m2" / "006_fn_metrics_availability_window.sql"


def main() -> None:
    settings = load_settings(Path("configs"))
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # Ensure function exists
            sql = SQL_FN.read_text(encoding="utf-8")
            cur.execute(sql)
        conn.commit()

    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # Pick a window from data automatically
            cur.execute(
                "SELECT min(ts_bucket), max(ts_bucket) FROM public.fact_measurements"
            )
            r = cur.fetchone()
            start_ts = r[0]
            end_ts = r[1]
            print("[WINDOW]", start_ts, "→", end_ts)

            # Summary by station×device×window
            _t0 = __import__("time").perf_counter()
            cur.execute(
                """
                WITH win AS (
                  SELECT * FROM public.metrics_availability_window(%s, %s)
                ), joined AS (
                  SELECT s.name AS station, d.name AS device, w.*
                  FROM win w
                  JOIN public.dim_stations s ON s.id=w.station_id
                  JOIN public.dim_devices d ON d.id=w.device_id
                )
                SELECT station, device, min(start_ts) AS start_ts, max(end_ts) AS end_ts,
                  COUNT(*) FILTER (WHERE status='available') AS available_count,
                  COUNT(*) FILTER (WHERE method_hint='compute') AS need_compute_count,
                  array_agg(metric_key ORDER BY metric_key)
                    FILTER (WHERE status='available') AS available_metrics,
                  array_agg(metric_key ORDER BY metric_key)
                    FILTER (WHERE method_hint='compute') AS need_compute_metrics
                FROM joined
                GROUP BY station, device
                ORDER BY station, device
                """,
                (start_ts, end_ts),
            )
            summary = cur.fetchall()
            _cost_ms = int((__import__("time").perf_counter() - _t0) * 1000)
            try:
                from app.core.logging.setup import log_db_function

                log_db_function(
                    "public.metrics_availability_window",
                    args={"start_ts": str(start_ts), "end_ts": str(end_ts)},
                    duration_ms=_cost_ms,
                    rows=len(summary),
                )
            except Exception:
                pass
            print("[SUMMARY_ROWS]", len(summary))
            for row in summary[:10]:
                print("[SUMMARY]", row)

            # Detail lists
            cur.execute(
                """
                WITH win AS (
                  SELECT * FROM public.metrics_availability_window(%s, %s)
                ), joined AS (
                  SELECT s.name AS station, d.name AS device, w.*
                  FROM win w
                  JOIN public.dim_stations s ON s.id=w.station_id
                  JOIN public.dim_devices d ON d.id=w.device_id
                )
                SELECT station, device, start_ts, end_ts, metric_key, coverage_rate, status, method_hint
                FROM joined
                WHERE method_hint='compute'
                ORDER BY station, device, metric_key
                """,
                (start_ts, end_ts),
            )
            need_compute = cur.fetchall()

            cur.execute(
                """
                WITH win AS (
                  SELECT * FROM public.metrics_availability_window(%s, %s)
                ), joined AS (
                  SELECT s.name AS station, d.name AS device, w.*
                  FROM win w
                  JOIN public.dim_stations s ON s.id=w.station_id
                  JOIN public.dim_devices d ON d.id=w.device_id
                )
                SELECT station, device, start_ts, end_ts, metric_key, coverage_rate
                FROM joined
                WHERE status='available'
                ORDER BY station, device, metric_key
                """,
                (start_ts, end_ts),
            )
            available = cur.fetchall()

    out: dict[str, Any] = {
        "window": {"start": str(start_ts), "end": str(end_ts)},
        "summary_rows": len(summary),
        "need_compute_count": len(need_compute),
        "available_count": len(available),
        "summary_top5": [tuple(map(str, r)) for r in summary[:5]],
        "need_compute_top10": [tuple(map(str, r)) for r in need_compute[:10]],
        "available_top10": [tuple(map(str, r)) for r in available[:10]],
    }
    Path("logs/reports").mkdir(parents=True, exist_ok=True)
    Path("logs/reports/metrics_availability_window_report.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
