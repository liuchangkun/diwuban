from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn

TARGETS: List[Tuple[str, str]] = [
    ("public", "mv_device_running_1s"),
    ("public", "quality_diagnosis_log"),
    ("public", "mv_presence_1s"),
    ("public", "mv_metric_60s_stats"),
    ("public", "mv_presence_1s_any"),
]


def q_all(cur, sql: str, params=None):
    cur.execute(sql, params or {})
    return cur.fetchall()


def main() -> None:
    settings = load_settings(Path("configs"))
    out: Dict[str, List[Dict[str, str]]] = {}
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            for schema, name in TARGETS:
                rows = q_all(
                    cur,
                    """
                    SELECT column_name, data_type, is_nullable, collation_name
                    FROM information_schema.columns
                    WHERE table_schema=%s AND table_name=%s
                    ORDER BY ordinal_position
                    """,
                    (schema, name),
                )
                out[f"{schema}.{name}"] = [
                    {
                        "name": r[0],
                        "type": r[1],
                        "nullable": r[2],
                        "collation": r[3],
                    }
                    for r in rows
                ]
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

