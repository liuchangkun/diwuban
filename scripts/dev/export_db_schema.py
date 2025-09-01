# -*- coding: utf-8 -*-
"""
导出数据库结构（只读，中文注释）
- 读取 configs/database.yaml
- 使用 psycopg 连接数据库（优先 dsn_read，否则 host/name/user）
- 导出表/列/索引/外键到 Markdown：docs/_archive/reports/db_schema_snapshot.md
注意：仅执行 SELECT；若连接失败则退出非零；上层脚本可回退静态解析。
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml  # type: ignore

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "_archive" / "reports" / "db_schema_snapshot.md"
CFG = ROOT / "configs" / "database.yaml"


def load_cfg():
    data = yaml.safe_load(CFG.read_text(encoding="utf-8"))
    host = data.get("host")
    name = data.get("name")
    user = data.get("user")
    dsn_read = data.get("dsn_read")
    return dsn_read, host, name, user


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    dsn_read, host, name, user = load_cfg()
    import psycopg

    if dsn_read:
        conn = psycopg.connect(dsn_read, connect_timeout=5)
    else:
        conn = psycopg.connect(host=host, dbname=name, user=user, connect_timeout=5)

    with conn:
        with conn.cursor() as cur:
            # 限制语句执行时间，避免长时间阻塞
            try:
                # 使用配置中 statement_timeout_ms，如无则放宽到 30000ms
                cur.execute("SET statement_timeout=30000")
            except Exception:
                pass
            lines = ["# 数据库结构快照\n"]
            # 表
            try:
                cur.execute(
                    """
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_type='BASE TABLE' AND table_schema NOT IN ('pg_catalog','information_schema')
                    ORDER BY table_schema, table_name
                    """
                )
                tables = cur.fetchall()
            except Exception as e:
                tables = []
                lines.append(f"[WARN] 获取表列表失败: {e}\n")
                conn.rollback()
            lines.append("## 表列表\n")
            for sch, tbl in tables:
                lines.append(f"- {sch}.{tbl}")
            lines.append("")

            # 列
            MAX_TABLES = 50
            lines.append(f"## 列明细（前 {MAX_TABLES} 张表）\n")
            for sch, tbl in tables[:MAX_TABLES]:
                try:
                    cur.execute(
                        """
                        SELECT column_name, data_type, is_nullable, column_default
                        FROM information_schema.columns
                        WHERE table_schema=%s AND table_name=%s
                        ORDER BY ordinal_position
                        """,
                        (sch, tbl),
                    )
                    cols = cur.fetchall()
                except Exception as e:
                    lines.append(f"### {sch}.{tbl}\n- [WARN] 获取列失败: {e}\n")
                    continue
                lines.append(f"### {sch}.{tbl}\n")
                for name_, typ, nullable, default in cols:
                    lines.append(
                        f"- {name_} {typ} {'NULL' if nullable=='YES' else 'NOT NULL'} default={default}"
                    )
                lines.append("")

            # 索引（简要）
            lines.append("## 索引（简要）\n")
            try:
                cur.execute(
                    """
                    SELECT schemaname, tablename, indexname, indexdef
                    FROM pg_indexes
                    WHERE schemaname NOT IN ('pg_catalog','information_schema')
                    ORDER BY schemaname, tablename, indexname
                    """
                )
                for sch, tbl, idx, idef in cur.fetchall():
                    lines.append(f"- {sch}.{tbl} :: {idx}\n```sql\n{idef}\n```\n")
            except Exception as e:
                lines.append(f"[WARN] 获取索引失败: {e}\n")
                conn.rollback()

            # 外键（简要）
            lines.append("## 外键（简要）\n")
            try:
                cur.execute(
                    """
                    SELECT tc.table_schema, tc.table_name, tc.constraint_name, kcu.column_name,
                           ccu.table_schema AS foreign_table_schema,
                           ccu.table_name AS foreign_table_name,
                           ccu.column_name AS foreign_column_name
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                      ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                      ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                    ORDER BY tc.table_schema, tc.table_name, tc.constraint_name
                    """
                )
                for sch, tbl, cons, col, f_sch, f_tbl, f_col in cur.fetchall():
                    lines.append(
                        f"- {sch}.{tbl}.{col} -> {f_sch}.{f_tbl}.{f_col} ({cons})"
                    )
            except Exception as e:
                lines.append(f"[WARN] 获取外键失败: {e}\n")
                conn.rollback()

            # 视图清单（新增）
            lines.append("## 视图列表\n")
            try:
                cur.execute(
                    """
                    SELECT table_schema, table_name
                    FROM information_schema.views
                    WHERE table_schema NOT IN ('pg_catalog','information_schema')
                    ORDER BY table_schema, table_name
                    """
                )
                for sch, v in cur.fetchall():
                    lines.append(f"- {sch}.{v}")
            except Exception as e:
                lines.append(f"[WARN] 获取视图列表失败: {e}\n")
                conn.rollback()
            lines.append("")

            # 物化视图清单（新增）
            lines.append("## 物化视图列表\n")
            try:
                cur.execute(
                    """
                    SELECT schemaname, matviewname
                    FROM pg_matviews
                    WHERE schemaname NOT IN ('pg_catalog','information_schema')
                    ORDER BY schemaname, matviewname
                    """
                )
                for sch, mv in cur.fetchall():
                    lines.append(f"- {sch}.{mv}")
            except Exception as e:
                lines.append(f"[WARN] 获取物化视图列表失败: {e}\n")
                conn.rollback()
            lines.append("")

            # 视图定义摘要（新增，前 50 个）
            lines.append("## 视图定义摘要（前 50 个）\n")
            try:
                cur.execute(
                    """
                    SELECT table_schema, table_name
                    FROM information_schema.views
                    WHERE table_schema NOT IN ('pg_catalog','information_schema')
                    ORDER BY table_schema, table_name
                    LIMIT 50
                    """
                )
                views = cur.fetchall()
                for sch, v in views:
                    try:
                        cur.execute(
                            "SELECT pg_get_viewdef(%s::regclass)", (f"{sch}.{v}",)
                        )
                        defn = cur.fetchone()[0]
                        # 截断到 1200 字符，避免报告过长
                        snippet = (
                            (defn[:1200] + "...")
                            if defn and len(defn) > 1200
                            else (defn or "")
                        )
                        lines.append(f"### {sch}.{v}\n```sql\n{snippet}\n```\n")
                    except Exception as ee:
                        lines.append(f"### {sch}.{v}\n[WARN] 获取视图定义失败: {ee}\n")
            except Exception as e:
                lines.append(f"[WARN] 视图定义摘要获取失败: {e}\n")
                conn.rollback()

            OUT.write_text("\n".join(lines), encoding="utf-8")
            print("[OK] 导出完成：", OUT)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("[ERR]", e)
        sys.exit(2)
