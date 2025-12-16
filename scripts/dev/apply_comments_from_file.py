from __future__ import annotations

import json
import re
from pathlib import Path

import sys
import psycopg

# 让脚本可直接导入 app 配置
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from app.core.config.loader_new import load_settings  # type: ignore
except Exception:  # pragma: no cover
    from app.core.config.loader import load_settings  # type: ignore

from app.adapters.db.gateway import make_dsn


def split_comment_statements(sql_text: str) -> list[str]:
    """
    将由本项目生成的 comments_full.sql 拆分为独立的 COMMENT 语句。
    假设每条语句以 $DOC$; 结束（美元引号包裹，内部可含分号）。
    """
    parts = re.split(r"(\$DOC\$\s*;)", sql_text)
    stmts: list[str] = []
    for i in range(0, len(parts) - 1, 2):
        head = parts[i].strip()
        tail = parts[i + 1]  # "$DOC$;"
        if head:
            stmts.append(head + "\n" + tail)
    return stmts


def main() -> None:
    meta_sql_path = Path("generated/comments_full.sql")
    if not meta_sql_path.exists():
        raise SystemExit("generated/comments_full.sql 不存在，请先生成该文件")

    sql_text = meta_sql_path.read_text(encoding="utf-8")
    stmts = split_comment_statements(sql_text)

    settings = load_settings(Path("configs"))
    dsn = make_dsn(settings)

    applied = 0
    failures: list[dict] = []

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            for s in stmts:
                try:
                    cur.execute(s)
                    applied += 1
                except Exception as e:  # pragma: no cover
                    failures.append({"stmt": s.splitlines()[0][:200], "error": str(e)})
            # 读写事务，统一提交
        # 自动退出 with 时提交

    summary = {
        "file": str(meta_sql_path),
        "total": len(stmts),
        "applied": applied,
        "failed": len(failures),
        "failures_sample": failures[:5],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

