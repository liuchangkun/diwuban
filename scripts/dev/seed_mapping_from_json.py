from __future__ import annotations

import json
from hashlib import md5
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn

MAPPING_JSON = Path('configs/data_mapping.v2.json')


def run() -> int:
    settings = load_settings(Path('configs'))
    data = json.loads(MAPPING_JSON.read_text(encoding='utf-8'))
    stations = data.get('stations') or []

    rows: list[tuple[str, str, str, str]] = []  # (hash, station, device, metric_key, source)
    for s in stations:
        sname = (s or {}).get('name')
        for d in (s or {}).get('devices') or []:
            dname = (d or {}).get('name')
            for m in (d or {}).get('metrics') or []:
                key = (m or {}).get('key')
                if not (sname and dname and key):
                    continue
                h = md5(f"{sname}|{dname}|{key}".encode('utf-8')).hexdigest()
                rows.append((h, sname, dname, key, 'data_mapping.v2.json'))

    if not rows:
        print('[SEED] no rows parsed from mapping json')
        return 0

    ins_sql = (
        """
        INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
        SELECT %s, %s, %s, %s, %s
        WHERE NOT EXISTS (
          SELECT 1 FROM public.dim_mapping_items WHERE station_name=%s AND device_name=%s AND metric_key=%s
        )
        """
    )

    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            for h, sname, dname, key, src in rows:
                cur.execute(ins_sql, (h, sname, dname, key, src, sname, dname, key))
        conn.commit()

    print(f"[SEED] upserted mapping rows: parsed={len(rows)}")
    return 0


if __name__ == '__main__':
    raise SystemExit(run())

