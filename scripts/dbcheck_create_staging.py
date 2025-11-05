import json
import traceback
from pathlib import Path

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings

marker_dir = Path('cli_out')
marker_dir.mkdir(parents=True, exist_ok=True)
(Path('cli_out/dbcheck_marker.txt')).write_text('start', encoding='utf-8')

try:
    settings = load_settings(Path('configs'))
    init_database(settings)
    res = {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('staging_raw','staging_rejects') ORDER BY 1")
            res['tables'] = [r[0] for r in cur.fetchall()]
            for t in ['staging_raw','staging_rejects']:
                cur.execute("SELECT count(*) FROM information_schema.columns WHERE table_schema='public' AND table_name=%s", (t,))
                res[f'{t}_cols'] = cur.fetchone()[0]
                cur.execute(f'SELECT count(*) FROM public.{t}')
                res[f'{t}_rows'] = cur.fetchone()[0]
    out_path = Path('cli_out/create_staging_dbcheck.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False)
    Path('cli_out/dbcheck_marker.txt').write_text('ok', encoding='utf-8')
except Exception:
    Path('cli_out/dbcheck_error.txt').write_text(traceback.format_exc(), encoding='utf-8')
    Path('cli_out/dbcheck_marker.txt').write_text('error', encoding='utf-8')

