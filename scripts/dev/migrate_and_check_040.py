from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn
from app.adapters.db.transaction import auto_commit


def main():
    settings = load_settings(Path('configs'))

    sql_path = Path('scripts/sql/migrations/040_create_quality_diagnosis_log_and_wrapper.sql')
    sql = sql_path.read_text(encoding='utf-8')

    print(f'[APPLY] {sql_path}')
    with get_conn(settings) as conn:
        with auto_commit(conn):
            with conn.cursor() as cur:
                cur.execute(sql)
    print('[OK] migration applied')

    # 检查过程是否存在
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT n.nspname, p.proname, pg_catalog.pg_get_function_arguments(p.oid) AS args
                FROM pg_catalog.pg_proc p
                JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
                WHERE p.prokind = 'p' AND n.nspname='public' AND p.proname='sp_mark_quality_window_vfast_diag'
                ORDER BY 1,2
                """
            )
            rows = cur.fetchall()
            print('[CHECK PROC] found:', len(rows))
            for r in rows:
                print(' -', f"{r[0]}.{r[1]}({r[2]})")

    # 进行一次烟囱调用
    run_id = 'smoke-' + uuid4().hex
    s = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    e = datetime(2025, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
    print('[SMOKE] calling wrapper with run_id=', run_id)
    with get_conn(settings) as conn:
        with auto_commit(conn):
            with conn.cursor() as cur:
                cur.execute(
                    "CALL public.sp_mark_quality_window_vfast_diag(%s::timestamptz,%s::timestamptz,%s::bigint,%s::bigint,%s::int[],%s::text,%s::text)",
                    (s, e, None, 5, None, 'brief', run_id),
                )

    # 读取质量诊断日志
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, stage, level, message
                FROM public.quality_diagnosis_log
                WHERE run_id = %s
                ORDER BY id
                """,
                (run_id,),
            )
            logs = cur.fetchall()
            print('[DB LOGS]', len(logs))
            for row in logs:
                print(' *', row)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise

