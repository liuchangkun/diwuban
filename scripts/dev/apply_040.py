from pathlib import Path
from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn
from app.adapters.db.transaction import auto_commit
from app.core.logging.setup import init_logging


def main():
    init_logging('configs')
    settings = load_settings(Path('configs'))
    sql_path = Path('scripts/sql/migrations/040_create_quality_diagnosis_log_and_wrapper.sql')
    sql = sql_path.read_text(encoding='utf-8')
    print(f'[APPLY] {sql_path}')
    with get_conn(settings) as conn:
        with auto_commit(conn):
            with conn.cursor() as cur:
                cur.execute(sql)
    print('[OK] migration applied')


if __name__ == '__main__':
    main()

