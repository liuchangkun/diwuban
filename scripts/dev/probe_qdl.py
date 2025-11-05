from pathlib import Path
import json
from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def main():
    settings = load_settings(Path('configs'))
    data = {}
    try:
        from psycopg.rows import tuple_row
    except Exception:
        tuple_row = None
    with get_conn(settings) as conn:
        if tuple_row is not None:
            conn.row_factory = tuple_row
        with conn.cursor() as cur:
            cur.execute('select current_database(), current_user')
            dbrow = cur.fetchone()
            data['db'] = tuple(dbrow) if dbrow else None
            cur.execute("select proname, prokind from pg_proc where proname='sp_mark_quality_window_vfast_diag' order by 1")
            data['proc_list'] = [tuple(r) for r in cur.fetchall()]
            cur.execute("select to_regprocedure('public.sp_mark_quality_window_vfast_diag(timestamptz,timestamptz,bigint,bigint,integer[],text,text)')")
            data['reg'] = tuple(cur.fetchone())
            try:
                cur.execute('call public.sp_mark_quality_window_vfast_diag(%s,%s,%s,%s,%s,%s,%s)', (
                    '2025-01-01T00:00:00+00:00','2025-01-01T01:00:00+00:00', None, 5, None, 'brief', 'probe_run'))
                conn.commit()
                data['call'] = 'ok'
            except Exception as e:
                data['call'] = 'error:' + str(e)
            try:
                cur.execute("select id, stage, level, message, (detail->>'result') as res from public.quality_diagnosis_log order by id desc limit 5")
                data['qdl'] = [tuple(r) for r in cur.fetchall()]
            except Exception as e:
                data['qdl_error'] = str(e)
    out = Path('logs/qdl_probe.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()

