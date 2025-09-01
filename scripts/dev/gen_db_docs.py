# -*- coding: utf-8 -*-
"""
自动生成数据库文档自动段：
- 更新 docs/数据库设计文档.md 与 docs/表结构与数据库.md 中“实库结构（自动生成）/视图清单/物化视图清单”自动段
- 数据来源：docs/_archive/reports/db_schema_snapshot.md
- 仅替换自动段 BEGIN:DB_AUTO/END:DB_AUTO，其他手写段不变
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAP = ROOT / "docs" / "_archive" / "reports" / "db_schema_snapshot.md"
DOC_DB = ROOT / "docs" / "数据库设计文档.md"

BEGIN = "<!-- BEGIN:DB_AUTO -->"
END = "<!-- END:DB_AUTO -->"


def extract_block_from_snapshot() -> str:
    text = SNAP.read_text(encoding="utf-8")
    # 简化：从“## 表列表”开始到文末截取，保留视图/物化视图/视图定义摘要等
    m = re.search(r"^## 表列表.*$", text, flags=re.M)
    if not m:
        # 快照异常时，直接返回提示
        return "[WARN] 快照缺少表列表段落，请检查导出脚本运行是否成功。"
    return text[m.start():]


def replace_auto_block(doc_path: Path, block: str) -> None:
    content = doc_path.read_text(encoding="utf-8")
    if BEGIN not in content or END not in content:
        raise RuntimeError(f"文档缺少自动段标记: {doc_path}")
    pre, rest = content.split(BEGIN, 1)
    _, post = rest.split(END, 1)
    new_content = pre + BEGIN + "\n\n" + block.rstrip() + "\n\n" + END + post
    if new_content != content:
        doc_path.write_text(new_content, encoding="utf-8")
        print(f"[OK] 数据库文档自动段已更新: {doc_path}")
    else:
        print(f"[OK] 数据库文档自动段无需更新: {doc_path}")


def main():
    block = extract_block_from_snapshot()
    replace_auto_block(DOC_DB, block)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("[ERR] 生成 DB 文档失败:", e)
        sys.exit(2)

