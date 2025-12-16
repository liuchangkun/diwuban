from __future__ import annotations
import csv
from pathlib import Path
from typing import List

from app.adapters.db.gateway import get_conn
from app.core.config.loader import load_settings

ROOT = Path('.')
SQL_DIR = ROOT / 'scripts' / 'sql' / 'm2'
CSV_PATH = ROOT / 'docs' / 'templates' / 'metric_capability_policy_seed.csv'

SQL_FILES: List[str] = [
    '002_metric_capability_policy.sql',
    '003_metrics_availability_v_weekly.sql',
    '004_metrics_missing_v.sql',
]


def run() -> None:
    settings = load_settings(Path('configs'))
    print('[INFO] Using config dir: configs')
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # Execute SQL files (DDL + VIEW)
            for name in SQL_FILES:
                p = SQL_DIR / name
                sql = p.read_text(encoding='utf-8')
                print(f'[EXEC] {p}')
                cur.execute(sql)
            # Upsert CSV seed
            if CSV_PATH.exists():
                print(f'[SEED] Import CSV: {CSV_PATH}')
                with CSV_PATH.open('r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                for r in rows:
                    cur.execute(
                        """
                        INSERT INTO public.metric_capability_policy(metric_key, acquisition_status, compute_flag, updated_by)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (metric_key) DO UPDATE
                          SET acquisition_status = EXCLUDED.acquisition_status,
                              compute_flag       = EXCLUDED.compute_flag,
                              updated_at         = now(),
                              updated_by         = EXCLUDED.updated_by
                        """,
                        (
                            r['metric_key'], r['acquisition_status'], r['compute_flag'], r.get('updated_by') or 'sys'
                        ),
                    )
                print(f'[SEED] Upserted {len(rows)} rows into metric_capability_policy')
        conn.commit()

    # Read-only validation queries
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) FROM public.metrics_missing_v
                WHERE method_hint='compute' AND week_start >= date_trunc('week', now()) - interval '4 weeks'
                """
            )
            compute_4w = int(cur.fetchone()[0])
            cur.execute(
                """
                SELECT COUNT(*) FROM public.metrics_missing_v
                WHERE method_hint='acquire' AND week_start >= date_trunc('week', now()) - interval '8 weeks'
                """
            )
            acquire_8w = int(cur.fetchone()[0])
            cur.execute(
                """
                SELECT station_id, device_id, metric_id, metric_key, week_start, status, coverage_rate
                FROM public.metrics_missing_v
                WHERE week_start >= date_trunc('week', now()) - interval '4 weeks'
                ORDER BY week_start DESC, station_id, device_id, metric_id
                LIMIT 10
                """
            )
            samples = cur.fetchall()
            print('[RESULT] compute_required (last 4w):', compute_4w)
            print('[RESULT] missing_raw (last 8w):', acquire_8w)
            print('[SAMPLES] top 10 rows (last 4w window):')
            for row in samples:
                print(row)


if __name__ == '__main__':
    run()

