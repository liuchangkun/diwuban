# -*- coding: utf-8 -*-
"""
从 scripts/sql/*.sql 抽取结构（CREATE TABLE/INDEX/VIEW）生成 Markdown 片段（中文注释）。
用法：python scripts/dev/extract_sql_schema.py > docs/_archive/reports/sql_schema_extract.md
"""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = ROOT / "scripts" / "sql"

CREATE_PAT = re.compile(
    r"(?is)\bCREATE\s+(TABLE|MATERIALIZED\s+VIEW|VIEW|INDEX)\b[\s\S]*?;"
)
NAME_PAT = re.compile(r"\b(?:TABLE|VIEW|MATERIALIZED\s+VIEW|INDEX)\s+([\w\.\"]+)")


def main():
    print("# SQL 结构抽取（自动生成）\n")
    for p in sorted(SQL_DIR.glob("*.sql")):
        text = p.read_text(encoding="utf-8", errors="ignore")
        blocks = CREATE_PAT.findall(text)
        if not blocks:
            continue
        print(f"## {p.name}\n")
        for m in re.finditer(
            r"(?is)\bCREATE\s+(TABLE|MATERIALIZED\s+VIEW|VIEW|INDEX)\b[\s\S]*?;", text
        ):
            kind = m.group(1).upper().replace("  ", " ")
            stmt = m.group(0).strip()
            name_m = NAME_PAT.search(stmt)
            name = name_m.group(1) if name_m else "(unknown)"
            print(f"- 对象：{name} ({kind})")
            print("")
            print("```sql")
            print(stmt)
            print("```")
            print("")


if __name__ == "__main__":
    main()
