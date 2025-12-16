from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Any

import sys
import psycopg

# 确保可导入 app 包
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

try:
    # 优先使用新配置加载器
    from app.core.config.loader_new import load_settings  # type: ignore
except Exception:  # pragma: no cover
    # 回退旧加载器（若项目存在旧版本）
    from app.core.config.loader import load_settings  # type: ignore

from app.adapters.db.gateway import make_dsn

EXCLUDE_SCHEMAS = {
    "pg_catalog",
    "information_schema",
    "pg_toast",
    "timescaledb_internal",
    "timescaledb_information",
}


def is_user_schema(name: str) -> bool:
    if name in EXCLUDE_SCHEMAS:
        return False
    if name.startswith("pg_") or name.startswith("_timescaledb_"):
        return False
    if name.startswith("pg_toast_temp_") or name.startswith("pg_temp_"):
        return False
    return True


def scan() -> Dict[str, Any]:
    settings = load_settings(Path("configs"))
    dsn = make_dsn(settings)

    result: Dict[str, Any] = {"schemas": {}}
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT nspname FROM pg_namespace ORDER BY nspname")
            schemas = [r[0] for r in cur.fetchall() if is_user_schema(r[0])]
            for sch in schemas:
                out = result["schemas"][sch] = {
                    "tables": {},
                    "views": {},
                    "matviews": {},
                    "functions": {},
                }
                # tables
                cur.execute(
                    """
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema=%s AND table_type='BASE TABLE'
                    ORDER BY table_name
                    """,
                    (sch,),
                )
                for (tname,) in cur.fetchall():
                    out["tables"][tname] = {"columns": [], "comment": None}
                    # columns
                    cur.execute(
                        """
                        SELECT column_name, data_type, udt_name, is_nullable, collation_name
                        FROM information_schema.columns
                        WHERE table_schema=%s AND table_name=%s
                        ORDER BY ordinal_position
                        """,
                        (sch, tname),
                    )
                    cols = []
                    for cn, dt, udt, nul, coll in cur.fetchall():
                        # column comments
                        cur.execute(
                            """
                            SELECT pgd.description
                            FROM pg_catalog.pg_statio_all_tables as st
                            INNER JOIN pg_catalog.pg_description pgd ON (pgd.objoid=st.relid)
                            INNER JOIN information_schema.columns c ON (pgd.objsubid=c.ordinal_position
                              AND c.table_schema=st.schemaname AND c.table_name=st.relname)
                            WHERE c.table_schema=%s AND c.table_name=%s AND c.column_name=%s
                            """,
                            (sch, tname, cn),
                        )
                        cmt_row = cur.fetchone()
                        cmt = cmt_row[0] if cmt_row else None
                        cols.append(
                            {
                                "name": cn,
                                "data_type": dt,
                                "udt": udt,
                                "nullable": (nul == "YES"),
                                "collation": coll,
                                "comment": cmt,
                            }
                        )
                    out["tables"][tname]["columns"] = cols
                    # table comment
                    cur.execute(
                        "SELECT obj_description((quote_ident(%s)||'.'||quote_ident(%s))::regclass)",
                        (sch, tname),
                    )
                    tcm_row = cur.fetchone()
                    out["tables"][tname]["comment"] = tcm_row[0] if tcm_row else None

                # views
                cur.execute(
                    "SELECT table_name FROM information_schema.views WHERE table_schema=%s ORDER BY table_name",
                    (sch,),
                )
                for (vname,) in cur.fetchall():
                    out["views"][vname] = {"definition": None, "comment": None}
                    cur.execute(
                        "SELECT pg_get_viewdef(quote_ident(%s)||'.'||quote_ident(%s), true)",
                        (sch, vname),
                    )
                    vdef_row = cur.fetchone()
                    out["views"][vname]["definition"] = (
                        vdef_row[0] if vdef_row else None
                    )
                    cur.execute(
                        "SELECT obj_description((quote_ident(%s)||'.'||quote_ident(%s))::regclass)",
                        (sch, vname),
                    )
                    vcm_row = cur.fetchone()
                    out["views"][vname]["comment"] = vcm_row[0] if vcm_row else None

                # materialized views
                cur.execute(
                    "SELECT matviewname FROM pg_matviews WHERE schemaname=%s ORDER BY matviewname",
                    (sch,),
                )
                for (mname,) in cur.fetchall():
                    out["matviews"][mname] = {"definition": None, "comment": None}
                    cur.execute(
                        "SELECT definition FROM pg_matviews WHERE schemaname=%s AND matviewname=%s",
                        (sch, mname),
                    )
                    mdef_row = cur.fetchone()
                    out["matviews"][mname]["definition"] = (
                        mdef_row[0] if mdef_row else None
                    )
                    cur.execute(
                        "SELECT obj_description((quote_ident(%s)||'.'||quote_ident(%s))::regclass)",
                        (sch, mname),
                    )
                    mcm_row = cur.fetchone()
                    out["matviews"][mname]["comment"] = mcm_row[0] if mcm_row else None

                # functions
                cur.execute(
                    """
                    SELECT p.oid, p.proname, pg_get_function_identity_arguments(p.oid) AS args,
                           pg_get_function_result(p.oid) AS rettype,
                           d.description
                    FROM pg_proc p
                    JOIN pg_namespace n ON n.oid=p.pronamespace
                    LEFT JOIN pg_description d ON d.objoid=p.oid AND d.objsubid=0
                    WHERE n.nspname=%s AND p.prokind='f'
                    ORDER BY p.proname
                    """,
                    (sch,),
                )
                for oid, fname, fargs, fret, fdesc in cur.fetchall():
                    out["functions"][fname] = {
                        "args": fargs,
                        "return": fret,
                        "comment": fdesc,
                    }

    return result


def main() -> None:
    data = scan()
    out_dir = Path("generated")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "db_objects.json"
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(str(out_file))


if __name__ == "__main__":
    main()
