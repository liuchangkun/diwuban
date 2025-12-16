from __future__ import annotations

"""
只读数据库盘点脚本
- 加载 configs 下的 database.yaml 等配置
- 通过 app.adapters.db.gateway.get_conn 获取连接（只读查询）
- 输出与数据质量相关的对象清单与 quality_code_dict 内容

运行方式：
  python scripts/tools/db_inventory.py
输出：JSON 到 stdout
"""

import json
from pathlib import Path
from typing import Any, Dict

from app.adapters.db.gateway import get_conn
from app.core.config.loader_new import load_settings


def q_one(cur, sql: str, params: dict | None = None):
    cur.execute(sql, params or {})
    return cur.fetchone()


def q_all(cur, sql: str, params: dict | None = None):
    cur.execute(sql, params or {})
    return cur.fetchall()


def main() -> None:
    settings = load_settings(Path("configs"))

    result: Dict[str, Any] = {
        "schemas": ["public", "reporting"],
        "objects": {},
        "quality_code_dict": {},
        "presence_table_location": {},
        "functions_focus": {},
    }

    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # 基本对象清单
            tables = q_all(
                cur,
                """
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_schema IN ('public','reporting')
                ORDER BY table_schema, table_name
                """,
            )
            views = q_all(
                cur,
                """
                SELECT table_schema, table_name
                FROM information_schema.views
                WHERE table_schema IN ('public','reporting')
                ORDER BY table_schema, table_name
                """,
            )
            matviews = q_all(
                cur,
                """
                SELECT schemaname, matviewname
                FROM pg_matviews
                WHERE schemaname IN ('public','reporting')
                ORDER BY schemaname, matviewname
                """,
            )
            functions = q_all(
                cur,
                """
                SELECT n.nspname AS schema,
                       p.proname AS name,
                       pg_get_function_arguments(p.oid) AS args,
                       pg_get_function_result(p.oid) AS returns
                FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname IN ('public','reporting')
                ORDER BY n.nspname, p.proname
                """,
            )
            triggers = q_all(
                cur,
                """
                SELECT trigger_schema, event_object_table, trigger_name, action_timing,
                       string_agg(DISTINCT event_manipulation, ',') AS events
                FROM information_schema.triggers
                WHERE trigger_schema IN ('public','reporting')
                GROUP BY trigger_schema, event_object_table, trigger_name, action_timing
                ORDER BY trigger_schema, event_object_table, trigger_name
                """,
            )

            result["objects"] = {
                "tables": [[s, n] for (s, n) in tables],
                "views": [[s, n] for (s, n) in views],
                "matviews": [[s, n] for (s, n) in matviews],
                "functions": [
                    {"schema": s, "name": n, "args": a, "returns": r}
                    for (s, n, a, r) in functions
                ],
                "triggers": [
                    {
                        "schema": s,
                        "table": t,
                        "name": n,
                        "timing": tm,
                        "events": ev,
                    }
                    for (s, t, n, tm, ev) in triggers
                ],
            }

            # quality_code_dict 列与数据
            cols = q_all(
                cur,
                """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema='public' AND table_name='quality_code_dict'
                ORDER BY ordinal_position
                """,
            )
            rows = q_all(
                cur,
                """
                SELECT code, label_zh, category, severity, COALESCE(description,'')
                FROM public.quality_code_dict
                ORDER BY code
                """,
            )
            result["quality_code_dict"] = {
                "columns": [
                    {
                        "name": c,
                        "type": t,
                        "nullable": n,
                        "default": d,
                    }
                    for (c, t, n, d) in cols
                ],
                "rows": [
                    {
                        "code": int(c),
                        "label_zh": l,
                        "category": cat,
                        "severity": int(sev) if sev is not None else None,
                        "description": desc,
                    }
                    for (c, l, cat, sev, desc) in rows
                ],
            }

            # metrics_presence_per_second_device 表位置（迁移校验）
            presence_pub = q_one(
                cur, "SELECT to_regclass('public.metrics_presence_per_second_device')"
            )
            presence_rep = q_one(
                cur,
                "SELECT to_regclass('reporting.metrics_presence_per_second_device')",
            )
            result["presence_table_location"] = {
                "public": bool(presence_pub and presence_pub[0] is not None),
                "reporting": bool(presence_rep and presence_rep[0] is not None),
            }

            # 焦点函数存在性（来自文档）
            fn_names = [
                "fn_quality_stats_1d",
                "fn_running_state_1s",
                "fn_startstop_windows",
            ]
            fn_exists = {}
            for fn in fn_names:
                ok = q_one(
                    cur,
                    """
                    SELECT EXISTS (
                      SELECT 1 FROM pg_proc p
                      JOIN pg_namespace n ON n.oid = p.pronamespace
                      WHERE p.proname = %s AND n.nspname IN ('public','reporting')
                    )
                    """,
                    (fn,),
                )
                fn_exists[fn] = bool(ok and ok[0])
            result["functions_focus"] = fn_exists

    # 同时输出到控制台与文件，避免终端重定向空输出/编码问题
    try:
        out_path = Path("temp/db-objects-latest.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
