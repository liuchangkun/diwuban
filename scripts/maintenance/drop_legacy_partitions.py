from __future__ import annotations

import json
from pathlib import Path

import sys
import psycopg

# 让脚本可直接执行到仓库根目录 app 包
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from app.core.config.loader_new import load_settings  # type: ignore
except Exception:  # pragma: no cover
    from app.core.config.loader import load_settings  # type: ignore

from app.adapters.db.gateway import make_dsn


SQL_DEPENDENTS = """
SELECT DISTINCT n.nspname AS schema, c.relname AS name, c.relkind
FROM pg_depend d
JOIN pg_class c ON c.oid=d.objid
JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE d.refobjid='public.fact_measurements_legacy'::regclass
  AND c.relkind IN ('v','m','r')
ORDER BY 1,2;
"""

SQL_CHILD_COUNT = """
SELECT count(*)
FROM pg_inherits i
WHERE i.inhparent = 'public.fact_measurements_legacy'::regclass
"""

DROP_VIEW_STMTS = [
    "DROP VIEW IF EXISTS monitoring.v_active_index_coverage",
    "DROP VIEW IF EXISTS monitoring.v_missing_indexes_last7d",
    "DROP VIEW IF EXISTS monitoring.v_active_partitions_last7d",
    "DROP VIEW IF EXISTS monitoring.v_active_partitions",
]


def main() -> None:
    settings = load_settings(Path("configs"))
    dsn = make_dsn(settings)

    result: dict = {"steps": [], "ok": True}

    with psycopg.connect(dsn) as conn:
        # Probe
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.fact_measurements_legacy')")
            legacy_oid = cur.fetchone()[0]
            result["legacy_exists"] = bool(legacy_oid)

        if not result["legacy_exists"]:
            result["steps"].append({"probe": "legacy_not_found"})
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

        with conn.cursor() as cur:
            cur.execute(SQL_CHILD_COUNT)
            child_count = int(cur.fetchone()[0])
            result["child_count"] = child_count

            cur.execute(SQL_DEPENDENTS)
            dependents = [
                {"schema": r[0], "name": r[1], "kind": r[2]} for r in cur.fetchall()
            ]
            result["dependents_before"] = dependents

        # Drop monitoring views first (idempotent)
        dropped_views: list[dict] = []
        with conn.cursor() as cur:
            for stmt in DROP_VIEW_STMTS:
                try:
                    cur.execute(stmt)
                    dropped_views.append({"stmt": stmt, "ok": True})
                except Exception as e:  # pragma: no cover
                    dropped_views.append({"stmt": stmt, "ok": False, "error": str(e)})
                    result["ok"] = False
        result["steps"].append({"drop_views": dropped_views})

        # Drop legacy parent (cascade to children)
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "DROP TABLE IF EXISTS public.fact_measurements_legacy CASCADE"
                )
                result["steps"].append({"drop_legacy": {"ok": True}})
            except Exception as e:  # pragma: no cover
                result["steps"].append({"drop_legacy": {"ok": False, "error": str(e)}})
                result["ok"] = False

        # Verify
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.fact_measurements_legacy')")
            legacy_after = cur.fetchone()[0]
            result["legacy_after"] = legacy_after

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
