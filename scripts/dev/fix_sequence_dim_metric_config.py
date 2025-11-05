from __future__ import annotations
from pathlib import Path

from app.adapters.db.gateway import get_conn
from app.core.config.loader import load_settings


def run() -> None:
    settings = load_settings(Path('configs'))
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT setval(
                  pg_get_serial_sequence('public.dim_metric_config','id'),
                  (SELECT COALESCE(MAX(id),0) FROM public.dim_metric_config),
                  true
                )
                """
            )
            print('[FIX] dim_metric_config id sequence set to max(id) with is_called=true')
        conn.commit()


if __name__ == '__main__':
    run()

