from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn

PATTERNS = [
    "%rule%",
    "%threshold%",
    "dim_metric_config%",
    "metric%config%",
    "%quality%",
]


def main() -> None:
    settings = load_settings(Path("configs"))
    out: Dict[str, Any] = {"tables": [], "columns": {}, "views": []}
    sql_tables = f"""
    SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_schema IN ('public','reporting')
      AND ({' OR '.join(["table_name ILIKE '" + p + "'" for p in PATTERNS])})
    ORDER BY table_schema, table_name;
    """
    sql_cols = """
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_schema=%s AND table_name=%s
    ORDER BY ordinal_position;
    """
    sql_views = f"""
    SELECT table_schema, table_name
    FROM information_schema.views
    WHERE table_schema IN ('public','reporting')
      AND ({' OR '.join(["table_name ILIKE '" + p + "'" for p in PATTERNS])})
    ORDER BY table_schema, table_name;
    """

    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(sql_tables)
            tables = cur.fetchall()
            out["tables"] = [[s, t] for (s, t) in tables]
            for s, t in tables:
                cur.execute(sql_cols, (s, t))
                cols = cur.fetchall()
                out["columns"][f"{s}.{t}"] = [
                    {"name": c, "type": ty, "nullable": nul} for (c, ty, nul) in cols
                ]
            cur.execute(sql_views)
            views = cur.fetchall()
            out["views"] = [[s, t] for (s, t) in views]
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

