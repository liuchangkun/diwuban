from pathlib import Path
from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def main():
    settings = load_settings(Path('configs'))
    lines = []
    try:
        from psycopg.rows import tuple_row
    except Exception:
        tuple_row = None
    with get_conn(settings) as conn:
        if tuple_row is not None:
            conn.row_factory = tuple_row
        with conn.cursor() as cur:
            cur.execute("select proname, prokind, pg_get_function_identity_arguments(oid) from pg_proc where proname in ('sp_mark_quality_window_vfast','sp_mark_quality_window_vfast_diag') order by 1")
            for r in cur.fetchall():
                lines.append(str(r))
    out = Path('logs/proc_sig.txt')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    main()

