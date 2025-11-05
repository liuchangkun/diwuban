from pathlib import Path
from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def main() -> None:
    sql_path = Path('scripts/sql/examples/remark_updates.sql')
    sql = sql_path.read_text(encoding='utf-8')
    settings = load_settings(Path('configs'))
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    print({'applied_sql': str(sql_path)})


if __name__ == '__main__':
    main()

