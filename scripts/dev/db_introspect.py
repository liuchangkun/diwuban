import sys
from pathlib import Path
from pprint import pprint

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def main():
    settings = load_settings(Path("configs"))
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # 是否 timescaledb hypertable
            cur.execute(
                """
                SELECT EXISTS (
                  SELECT 1 FROM information_schema.schemata WHERE schema_name='timescaledb'
                ) AS is_timescaledb
                """
            )
            is_ts = cur.fetchone()[0]

            # 尝试读取 timescaledb 信息，若失败则置空
            try:
                cur.execute(
                    """
                    SELECT json_agg(json_build_object('schema', hypertable_schema, 'name', hypertable_name))
                    FROM timescaledb_information.hypertables
                    WHERE hypertable_schema='public' AND hypertable_name='fact_measurements'
                    """
                )
                hypertables = cur.fetchone()[0]
            except Exception:
                hypertables = None

            cur.execute(
                """
                SELECT schemaname, tablename, indexname, indexdef
                FROM pg_indexes
                WHERE schemaname='public' AND tablename='fact_measurements'
                ORDER BY indexname
                """
            )
            indexes = cur.fetchall()

            cur.execute(
                """
                SELECT
                  pg_total_relation_size('public.fact_measurements') as total_bytes,
                  pg_relation_size('public.fact_measurements') as table_bytes,
                  pg_indexes_size('public.fact_measurements') as index_bytes
                """
            )
            sizes = cur.fetchone()

            cur.execute(
                """
                SELECT station_id, device_id, MIN(ts_bucket), MAX(ts_bucket), COUNT(*)
                FROM public.fact_measurements
                WHERE device_id=5
                GROUP BY station_id, device_id
                ORDER BY 1,2
                """
            )
            spans = cur.fetchall()

    print(
        {
            "is_timescaledb": is_ts,
            "hypertables": hypertables,
            "indexes": indexes[:10],  # preview
            "sizes": {
                "total_bytes": sizes[0],
                "table_bytes": sizes[1],
                "index_bytes": sizes[2],
            },
            "device5_span": spans,
        }
    )


if __name__ == "__main__":
    main()
