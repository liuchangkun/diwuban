import argparse
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--station-id", type=int, required=True)
    p.add_argument("--device-id", type=int, required=True)
    p.add_argument("--start", required=True, help="ISO8601, e.g. 2025-02-27T18:00:00Z")
    p.add_argument("--end", required=True, help="ISO8601, e.g. 2025-02-27T20:00:00Z")
    p.add_argument("--step-min", type=int, default=10, help="chunk minutes for marking window")
    return p.parse_args()


def parse_ts(s: str) -> datetime:
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def main():
    args = parse_args()
    station_id = args.station_id
    device_id = args.device_id
    start_dt = parse_ts(args.start)
    end_dt = parse_ts(args.end)
    step = timedelta(minutes=args.step_min)

    settings = load_settings(Path("configs"))

    chunks = []
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            t = start_dt
            while t < end_dt:
                s = t
                e = min(t + step, end_dt)
                chunks.append((s, e))
                # reset -> mark for this chunk
                cur.execute(
                    "CALL public.sp_reset_quality_window(%s::timestamptz,%s::timestamptz,%s::bigint,%s::bigint)",
                    (s, e, station_id, device_id),
                )
                cur.execute(
                    "CALL public.sp_mark_quality_window(%s::timestamptz,%s::timestamptz,%s::bigint,%s::bigint)",
                    (s, e, station_id, device_id),
                )
                conn.commit()
                t = e

            # full-window eval after all chunks
            cur.execute(
                "CALL public.sp_generate_quality_eval_by_device_metric(%s::timestamptz,%s::timestamptz,%s::bigint,%s::bigint)",
                (start_dt, end_dt, station_id, device_id),
            )
            conn.commit()

            # fetch eval distribution
            cur.execute(
                """
                SELECT mc.metric_key, e.quality_status, e.rows_count, e.total_count, e.ratio
                FROM public.quality_eval_by_device_metric e
                JOIN public.dim_metric_config mc ON mc.id=e.metric_id
                WHERE e.window_start=%s AND e.window_end=%s AND e.station_id=%s AND e.device_id=%s
                ORDER BY mc.metric_key, e.quality_status
                """,
                (start_dt, end_dt, station_id, device_id),
            )
            dist_rows = cur.fetchall()

            # sample rows (non-zero quality) up to 10 per metric x code
            cur.execute(
                """
                WITH samp AS (
                  SELECT f.ts_bucket, f.metric_id, mc.metric_key, f.value, f.quality_status, f.quality_type, f.quality_meta,
                         ROW_NUMBER() OVER (PARTITION BY f.metric_id, f.quality_status ORDER BY f.ts_bucket) AS rn
                  FROM public.fact_measurements f
                  JOIN public.dim_metric_config mc ON mc.id=f.metric_id
                  WHERE f.station_id=%s AND f.device_id=%s
                    AND f.ts_bucket >= %s::timestamptz AND f.ts_bucket < %s::timestamptz
                    AND COALESCE(f.quality_status,0) <> 0
                )
                SELECT ts_bucket, metric_key, quality_status, quality_type, value, quality_meta
                FROM samp WHERE rn <= 10
                ORDER BY metric_key, quality_status, ts_bucket
                """,
                (station_id, device_id, start_dt, end_dt),
            )
            sample_rows = cur.fetchall()

    export_dir = Path("exports"); export_dir.mkdir(parents=True, exist_ok=True)
    dist_csv = export_dir / f"quality_eval_s{station_id}_d{device_id}_{start_dt.strftime('%Y-%m-%d_%H%M')}_{end_dt.strftime('%H%M')}.csv"
    sample_csv = export_dir / f"quality_samples_s{station_id}_d{device_id}_{start_dt.strftime('%Y-%m-%d_%H%M')}_{end_dt.strftime('%H%M')}.csv"

    with dist_csv.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['metric_key','quality_status','rows_count','total_count','ratio'])
        for r in dist_rows:
            w.writerow(r)

    with sample_csv.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['ts_bucket','metric_key','quality_status','quality_type','value','quality_meta'])
        for r in sample_rows:
            w.writerow(r)

    print({
        'ok': True,
        'chunks': len(chunks),
        'dist_csv': str(dist_csv),
        'sample_csv': str(sample_csv),
    })


if __name__ == "__main__":
    main()

