import json
from pathlib import Path
from datetime import timezone

from app.core.config.loader_new import load_settings
from app.adapters.db import init_database, get_connection
from app.adapters.db.gateway import get_staging_time_range

settings = load_settings(Path('configs'))
init_database(settings)

out = {}
with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM public.fact_measurements")
        out['fact_before'] = cur.fetchone()[0]
    s,e,cnt = get_staging_time_range(conn)
    out['staging_min_utc'] = s.isoformat() if s else None
    out['staging_max_utc'] = e.isoformat() if e else None
    out['staging_rows'] = cnt

print(json.dumps(out, ensure_ascii=False))

