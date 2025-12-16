from __future__ import annotations

"""
应用数据库监控配置（低开销）。
- 优先尝试 ALTER SYSTEM（需超级用户）；若权限不足，仅进行可行操作并给出提示。
- 不修改 shared_preload_libraries（需人工在 postgresql.conf 配置并重启）。
- 验证 pg_stat_statements/pg_stat_user_functions 是否可用。
"""

import sys
from pathlib import Path

import psycopg

from app.adapters.db.gateway import make_dsn
from app.core.config.loader_new import load_settings


def main() -> int:
    settings = load_settings(Path("configs"))
    dsn = make_dsn(settings)

    print("[INFO] Connecting...", dsn)
    with psycopg.connect(dsn) as conn:
        # ALTER SYSTEM 不能在事务块内执行；启用 autocommit 以避免事务阻塞
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT version(), current_user")
            version, current_user = cur.fetchone()
            print("[INFO] version:", version)
            print("[INFO] user:", current_user)

            # 是否超级用户
            cur.execute("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
            is_super = bool(cur.fetchone()[0])
            print("[INFO] superuser:", is_super)

            # 扩展
            try:
                cur.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements;")
                print("[OK] pg_stat_statements available")
            except Exception as e:
                print("[WARN] create extension failed:", e)

            # 可热加载配置（ALTER SYSTEM 需要 superuser）
            if is_super:
                # 1) 确保 shared_preload_libraries 包含 auto_explain
                try:
                    cur.execute("SHOW shared_preload_libraries")
                    current_libs = (cur.fetchone()[0] or "").strip()
                except Exception as e:
                    current_libs = ""
                    print("[WARN] SHOW shared_preload_libraries failed:", e)
                parts = [p.strip() for p in current_libs.split(",") if p.strip()]
                want = list(
                    dict.fromkeys(parts + ["pg_stat_statements", "auto_explain"])
                )
                new_val = ",".join(want) if want else "pg_stat_statements,auto_explain"
                try:
                    cur.execute(
                        f"ALTER SYSTEM SET shared_preload_libraries = '{new_val}'"
                    )
                    print("[OK] wrote shared_preload_libraries =", new_val)
                except Exception as e:
                    print("[WARN] ALTER SYSTEM shared_preload_libraries failed:", e)

                # 2) 其他参数（重启后生效或热加载）
                cmds = [
                    "ALTER SYSTEM SET track_functions = 'pl'",
                    "ALTER SYSTEM SET auto_explain.log_min_duration = '200ms'",
                    "ALTER SYSTEM SET auto_explain.log_analyze = 'on'",
                    "ALTER SYSTEM SET auto_explain.log_buffers = 'on'",
                    "ALTER SYSTEM SET auto_explain.log_format = 'text'",
                ]
                ok = 0
                for c in cmds:
                    try:
                        cur.execute(c)
                        ok += 1
                    except Exception as e:
                        print("[WARN] ALTER SYSTEM failed:", c, e)
                print(
                    f"[INFO] ALTER SYSTEM applied: {ok}/{len(cmds)} (plus shared_preload_libraries)"
                )
                print(
                    "[NOTE] auto_explain 将在数据库重启后生效；track_functions=pl 已可立即使用。"
                )
            else:
                print(
                    "[WARN] not superuser: skip ALTER SYSTEM; please modify postgresql.conf manually."
                )

        # reload（无论是否 superuser，非 superuser 也可触发）
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_reload_conf();")
                print("[OK] pg_reload_conf() called")
        except Exception as e:
            print("[WARN] reload failed:", e)

        # 显示关键项
        with conn.cursor() as cur:
            for key in [
                "shared_preload_libraries",
                "track_functions",
                "auto_explain.log_min_duration",
                "auto_explain.log_analyze",
                "auto_explain.log_buffers",
                "auto_explain.log_format",
            ]:
                try:
                    cur.execute(f"SHOW {key}")
                    val = cur.fetchone()[0]
                    print(f"[SHOW] {key} = {val}")
                except Exception as e:
                    print(f"[SHOW] {key} error: {e}")

        # 验证可用性
        with conn.cursor() as cur:
            try:
                cur.execute("SELECT * FROM pg_stat_statements LIMIT 1")
                _ = cur.fetchone()
                print("[OK] pg_stat_statements readable")
            except Exception as e:
                print("[WARN] pg_stat_statements not readable:", e)

        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT schemaname, funcname, calls, total_time FROM pg_stat_user_functions ORDER BY total_time DESC LIMIT 5"
                )
                rows = cur.fetchall()
                print("[OK] pg_stat_user_functions sample:")
                for r in rows:
                    print("   ", r)
            except Exception as e:
                print("[WARN] pg_stat_user_functions not readable:", e)

    print("[DONE] Monitoring apply/verify finished")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
