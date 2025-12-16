# -*- coding: utf-8 -*-
"""
自动生成“数据库设计文档.md”的自动段与统计摘要：
- 优先从 docs/_archive/reports/db_schema_snapshot.md 读取快照，抽取自“## 表列表”起的区块
- 若快照缺失，则回退到文档现有自动段（BEGIN:DB_AUTO/END:DB_AUTO）内容
- 在自动段顶部注入“统计摘要 + 目录”（以 <!-- BEGIN:DB_SUMMARY --> 包裹，便于幂等更新）
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
SUM_BEGIN = "<!-- BEGIN:DB_SUMMARY -->"
SUM_END = "<!-- END:DB_SUMMARY -->"


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def extract_block_from_snapshot() -> str | None:
    if not SNAP.exists():
        return None
    text = _read_text(SNAP)
    m = re.search(r"^## 表列表.*$", text, flags=re.M)
    if not m:
        return None
    return text[m.start() :]


def extract_current_auto_block(doc_path: Path) -> str | None:
    content = _read_text(doc_path)
    if BEGIN not in content or END not in content:
        return None
    pre, rest = content.split(BEGIN, 1)
    auto, _post = rest.split(END, 1)
    return auto.strip()


def build_summary(block: str) -> str:
    # 统计表数量（按行前缀 - schema.table 简单匹配）
    table_lines = re.findall(
        r"^\-\s+[A-Za-z0-9_]+\.[A-Za-z0-9_]+\s*$", block, flags=re.M
    )
    n_tables = len(table_lines)
    summary = (
        f"### 数据库对象统计（自动）\n\n"
        f"- 表总数：{n_tables}\n"
        f"- 注：此统计来自自动段的对象清单（仅供参考）\n\n"
        f"### 目录\n\n"
        f"- [表列表](#表列表)\n"
        f"- [列明细（前 50 张表）](#列明细前-50-张表)\n"
    )
    return f"{SUM_BEGIN}\n{summary}{SUM_END}"


def compose_auto_block(raw_block: str) -> str:
    # 去掉旧的 SUMMARY 段，避免重复
    cleaned = raw_block
    if SUM_BEGIN in cleaned and SUM_END in cleaned:
        pre, rest = cleaned.split(SUM_BEGIN, 1)
        _old, post = rest.split(SUM_END, 1)
        cleaned = (pre + post).strip()
    summary = build_summary(cleaned)
    return summary + "\n\n" + cleaned.strip() + "\n"


def replace_auto_block(doc_path: Path, block: str) -> None:
    content = _read_text(doc_path)
    if BEGIN not in content or END not in content:
        raise RuntimeError(f"文档缺少自动段标记: {doc_path}")
    pre, rest = content.split(BEGIN, 1)
    _auto_old, post = rest.split(END, 1)
    new_auto = compose_auto_block(block)
    new_content = pre + BEGIN + "\n\n" + new_auto + "\n\n" + END + post
    if new_content != content:
        doc_path.write_text(new_content, encoding="utf-8")
        print(f"[OK] 数据库文档自动段已更新: {doc_path}")
    else:
        print(f"[OK] 数据库文档自动段无需更新: {doc_path}")


def main() -> None:
    block = extract_block_from_snapshot()
    if block is None:
        # 回退到现有自动段
        cur = extract_current_auto_block(DOC_DB)
        if cur is None:
            raise RuntimeError("无法获取自动段：快照缺失且文档无自动段标记")
        block = cur
    replace_auto_block(DOC_DB, block)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("[ERR] 生成 DB 文档失败:", e)
        sys.exit(2)
