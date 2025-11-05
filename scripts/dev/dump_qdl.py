from pathlib import Path
import json
from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn
from app.core.logging.setup import init_logging
import logging

def main():
    init_logging('configs')
    logger = logging.getLogger('anomaly')
    settings = load_settings(Path('configs'))
    try:
        from psycopg.rows import dict_row
    except Exception:
        dict_row = None
    with get_conn(settings) as conn:
        if dict_row is not None:
            conn.row_factory = dict_row
        with conn.cursor() as cur:
            cur.execute("select count(*) as c from public.quality_diagnosis_log")
            c = cur.fetchone()
            logger.info('[QDL] count', extra={'extra_data': c})
            cur.execute("select * from public.quality_diagnosis_log order by id desc limit 10")
            rows = cur.fetchall()
            for r in rows:
                logger.info('[QDL] row', extra={'extra_data': r})

if __name__ == '__main__':
    main()

