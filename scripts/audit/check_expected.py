from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def main() -> int:
    s = load_settings(Path('configs'))
    with get_conn(s) as conn:
        with conn.cursor() as cur:
            def one(sql: str, params: tuple = ()):
                cur.execute(sql, params)
                return cur.fetchone()[0]

            print('dim_stations.count=', one('SELECT COUNT(*) FROM public.dim_stations'))
            print('dim_devices.count=', one('SELECT COUNT(*) FROM public.dim_devices'))
            print('dim_metric_config.count=', one('SELECT COUNT(*) FROM public.dim_metric_config'))
            print('dim_mapping_items.count=', one('SELECT COUNT(*) FROM public.dim_mapping_items'))

            # 期望集合连接计数
            cur.execute(
                """
                SELECT COUNT(*)
                FROM public.dim_mapping_items mi
                JOIN public.dim_stations s ON s.name = mi.station_name
                JOIN public.dim_devices d ON d.station_id = s.id AND d.name = mi.device_name
                JOIN public.dim_metric_config mc ON mc.metric_key = mi.metric_key
                """
            )
            print('expected_join.count=', cur.fetchone()[0])

            # 抽样 5 条 expected
            cur.execute(
                """
                SELECT s.name, d.name, mi.metric_key
                FROM public.dim_mapping_items mi
                JOIN public.dim_stations s ON s.name = mi.station_name
                JOIN public.dim_devices d ON d.station_id = s.id AND d.name = mi.device_name
                JOIN public.dim_metric_config mc ON mc.metric_key = mi.metric_key
                ORDER BY s.name, d.name, mi.metric_key
                LIMIT 5
                """
            )
            print('expected_join.sample=', cur.fetchall())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

