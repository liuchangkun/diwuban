from __future__ import annotations
from pathlib import Path

from app.adapters.db.gateway import get_conn
from app.core.config.loader import load_settings

ROOT = Path('.')
SQL_DIR = ROOT / 'scripts' / 'sql' / 'm2'

SQL_FILES = [
    '006_fn_metrics_availability_window.sql',
    '007_fn_metrics_presence_per_second.sql',
]


def run() -> None:
    settings = load_settings(Path('configs'))
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            for name in SQL_FILES:
                p = SQL_DIR / name
                sql = p.read_text(encoding='utf-8')
                print(f'[EXEC] {p}')
                cur.execute(sql)
        conn.commit()


if __name__ == '__main__':
    run()

