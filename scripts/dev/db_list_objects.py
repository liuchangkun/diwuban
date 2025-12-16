from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure repo root on sys.path so we can import app.*
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config.loader import load_settings
from app.adapters.db.gateway import get_conn


def main() -> int:
    settings = load_settings(Path("configs"))
    out: dict[str, object] = {"schemas": {}}

    q_objects = """
    SELECT n.nspname AS schema,
           c.relname AS name,
           CASE c.relkind
             WHEN 'r' THEN 'table'
             WHEN 'm' THEN 'matview'
             WHEN 'v' THEN 'view'
             WHEN 'p' THEN 'partitioned_table'
             ELSE c.relkind::text
           END AS kind
    FROM pg_class c
    JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname IN ('public','reporting','monitoring')
      AND c.relkind IN ('r','m','v','p')
    ORDER BY n.nspname, c.relkind, c.relname
    """

    q_candidates = {
        "device_running_thresholds": "SELECT to_regclass('public.device_running_thresholds') IS NOT NULL",
        "metrics_presence_per_second_device": "SELECT to_regclass('public.metrics_presence_per_second_device') IS NOT NULL",
        "quality_profile_log": "SELECT to_regclass('public.quality_profile_log') IS NOT NULL",
        "completion_runs": "SELECT to_regclass('public.completion_runs') IS NOT NULL",
        "completion_steps": "SELECT to_regclass('public.completion_steps') IS NOT NULL",
        "mv_presence_1s": "SELECT to_regclass('public.mv_presence_1s') IS NOT NULL",
        "mv_running_presence": "SELECT to_regclass('public.mv_running_presence') IS NOT NULL",
        "mv_metric_60s_stats": "SELECT to_regclass('public.mv_metric_60s_stats') IS NOT NULL",
    }

    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(q_objects)
            rows = cur.fetchall()
            for sch, name, kind in rows:
                out.setdefault("schemas", {}).setdefault(sch, []).append({"name": name, "kind": kind})

            exists: dict[str, bool] = {}
            for key, q in q_candidates.items():
                cur.execute(q)
                exists[key] = bool(cur.fetchone()[0])
            out["candidates_exists"] = exists

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

