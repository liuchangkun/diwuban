import json
import sys
from pathlib import Path

# Ensure repository root is on sys.path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config.loader_new import load_settings
from app.adapters.db import init_database, get_connection

START = '2025-01-01 00:00:00+08'
END   = '2025-02-28 14:09:59+08'


def q(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        return [dict(zip(cols, r)) for r in rows]


def main():
    out = {}
    # init DB pool
    settings = load_settings(Path('configs'))
    init_database(settings)
    with get_connection() as conn:
        out['device_hours'] = q(conn, (
            """
            WITH per_hour AS (
              SELECT station_id, device_id, date_trunc('hour', ts_bucket) AS h
              FROM public.fact_measurements
              WHERE ts_bucket >= %s AND ts_bucket < %s
              GROUP BY station_id, device_id, h
            )
            SELECT station_id, device_id, COUNT(*) AS hours
            FROM per_hour
            GROUP BY station_id, device_id
            ORDER BY hours DESC
            """
        ), (START, END))

        out['quality_dist'] = q(conn, (
            """
            SELECT quality_status, COUNT(*) AS cnt
            FROM public.fact_measurements
            WHERE ts_bucket >= %s AND ts_bucket < %s
            GROUP BY quality_status
            ORDER BY cnt DESC
            """
        ), (START, END))

        out['metric_completeness'] = q(conn, (
            """
            SELECT metric_id,
                   COUNT(*) AS total,
                   SUM(CASE WHEN value IS NOT NULL THEN 1 ELSE 0 END) AS non_null,
                   SUM(CASE WHEN (value IS NOT NULL AND value > 0) THEN 1 ELSE 0 END) AS gt_zero
            FROM public.fact_measurements
            WHERE ts_bucket >= %s AND ts_bucket < %s
            GROUP BY metric_id
            ORDER BY total DESC
            """
        ), (START, END))

        out['running_coverage'] = q(conn, (
            """
            SELECT station_id, device_id,
                   SUM(CASE WHEN running=1 THEN 1 ELSE 0 END)::bigint AS run_secs,
                   COUNT(*)::bigint AS total_secs
            FROM public.mv_device_running_1s
            WHERE ts_bucket >= %s AND ts_bucket < %s
            GROUP BY station_id, device_id
            ORDER BY run_secs DESC
            """
        ), (START, END))

        out['running_phase_dist'] = q(conn, (
            """
            SELECT phase, COUNT(*) AS cnt
            FROM public.mv_device_running_1s
            WHERE ts_bucket >= %s AND ts_bucket < %s
            GROUP BY phase
            ORDER BY cnt DESC
            """
        ), (START, END))

        out['running_phase_type_dist'] = q(conn, (
            """
            SELECT phase_type, COUNT(*) AS cnt
            FROM public.mv_device_running_1s
            WHERE ts_bucket >= %s AND ts_bucket < %s
            GROUP BY phase_type
            ORDER BY cnt DESC
            """
        ), (START, END))

        out['per_hour_sec_hist'] = q(conn, (
            """
            WITH per_hour AS (
              SELECT station_id, device_id, date_trunc('hour', ts_bucket) AS h,
                     COUNT(DISTINCT ts_bucket) AS sec_count
              FROM public.fact_measurements
              WHERE ts_bucket >= %s AND ts_bucket < %s
              GROUP BY station_id, device_id, h
            )
            SELECT sec_count, COUNT(*) AS hours
            FROM per_hour
            GROUP BY sec_count
            ORDER BY sec_count
            """
        ), (START, END))

        pres_tab = q(conn, (
            """
            SELECT EXISTS (
              SELECT 1 FROM information_schema.tables
              WHERE table_schema='public' AND table_name='metrics_presence_per_second_device'
            ) AS ok
            """
        ))

        if pres_tab and pres_tab[0].get('ok'):
            out['presence_rows'] = q(conn, (
                """
                SELECT COUNT(*) AS rows
                FROM public.metrics_presence_per_second_device
                WHERE ts_second >= %s AND ts_second < %s
                """
            ), (START, END))

            out['presence_device_secs'] = q(conn, (
                """
                SELECT station_id, device_id, COUNT(*) AS secs
                FROM public.metrics_presence_per_second_device
                WHERE ts_second >= %s AND ts_second < %s
                GROUP BY station_id, device_id
                ORDER BY secs DESC
                """
            ), (START, END))

    Path('reports').mkdir(parents=True, exist_ok=True)
    Path('reports/analysis_data_layer.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print('OK analysis_data_layer.json')


if __name__ == '__main__':
    main()

