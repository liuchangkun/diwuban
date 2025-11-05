import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

# ensure repo root on sys.path so 'app' package is importable when running from scripts/dev
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--station-id", type=int, required=True)
    p.add_argument("--device-id", type=int, required=True)
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    return p.parse_args()


def parse_ts(s: str) -> datetime:
    # accept ...Z by converting to +00:00
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def main():
    args = parse_args()
    station_id = args.station_id
    device_id = args.device_id
    start_dt = parse_ts(args.start)
    end_dt = parse_ts(args.end)

    settings = load_settings(Path("configs"))

    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # (re)generate the eval table rows for this window
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
        'dist_csv': str(dist_csv),
        'sample_csv': str(sample_csv),
        'dist_rows': len(dist_rows),
        'sample_rows': len(sample_rows),
    })


if __name__ == "__main__":
    main()

