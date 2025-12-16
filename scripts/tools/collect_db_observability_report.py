from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import psycopg

from app.adapters.db.gateway import make_dsn
from app.core.config.loader_new import load_settings


def fetch_all(cur, sql: str, params: dict | None = None) -> list[tuple]:
    cur.execute(sql, params or {})
    return cur.fetchall()


essential_views_markers = (" v_", "_view")


def main() -> int:
    settings = load_settings(Path("configs"))
    dsn = make_dsn(settings)

    out: dict[str, Any] = {"functions": [], "views": [], "raw": {}}

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            # 1) 函数/触发器画像
            try:
                fn_rows = fetch_all(
                    cur,
                    """
                    SELECT schemaname, funcname, calls, total_time, self_time
                    FROM pg_stat_user_functions
                    ORDER BY total_time DESC
                    LIMIT 50
                    """,
                )
                out["functions"] = [
                    {
                        "schema": r[0],
                        "function": r[1],
                        "calls": int(r[2]),
                        "total_time_ms": float(r[3]),
                        "self_time_ms": float(r[4]),
                    }
                    for r in fn_rows
                ]
            except Exception as e:
                out["raw"]["fn_error"] = str(e)

            # 2) 视图使用与慢点（按 total_time 取前 200，随后在应用端筛选）
            try:
                pgss_rows = fetch_all(
                    cur,
                    """
                    SELECT calls, total_time, mean_time, rows, query
                    FROM pg_stat_statements
                    ORDER BY total_time DESC
                    LIMIT 200
                    """,
                )
                view_rows: list[dict[str, Any]] = []
                for calls, total_time, mean_time, rows, query in pgss_rows:
                    ql = (query or "").lower()
                    if " from public." in ql and any(m in ql for m in essential_views_markers):
                        view_rows.append(
                            {
                                "calls": int(calls),
                                "total_time_ms": float(total_time),
                                "mean_time_ms": float(mean_time),
                                "rows": int(rows) if rows is not None else None,
                                "query": query,
                            }
                        )
                out["views"] = view_rows[:50]
            except Exception as e:
                out["raw"]["pgss_error"] = str(e)

    Path("logs/reports").mkdir(parents=True, exist_ok=True)
    p = Path("logs/reports/db_observability_report.json")
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[OK] wrote", p)
    # 同时输出简短摘要
    print("[SUMMARY] functions_top: ", len(out.get("functions", [])))
    print("[SUMMARY] views_top: ", len(out.get("views", [])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

