# -*- coding: utf-8 -*-
"""
将按类型归类的变更（含高亮摘要）路由写入相应 PLAYBOOKS/文档：
- code → docs/PLAYBOOKS/改进与优化记录.md（按日期分节追加条目）
- db   → docs/数据库设计文档.md 的“## 变更记录”小节 + docs/PLAYBOOKS/数据库变更记录.md（按日期分节）
- config → docs/PLAYBOOKS/配置变更记录.md（按日期分节）
- docs → docs/PLAYBOOKS/经验教训.md（按日期分节，记录新增标题/要点）
- other → docs/PLAYBOOKS/开放问题与待澄清.md（按日期分节，提示人工归档）
并基于启发式规则“同时”写入：决策记录.md、错误与修复记录.md。
返回：每个类型实际写入的文件路径列表（含 decision/fix），用于“对话记忆.md”的索引。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
PLAY = ROOT / "docs" / "PLAYBOOKS"

FILES_BY_TYPE = {
    "code": PLAY / "改进与优化记录.md",
    "config": PLAY / "配置变更记录.md",
    "docs": PLAY / "经验教训.md",
    "other": PLAY / "开放问题与待澄清.md",
}
DB_FILE = ROOT / "docs" / "数据库设计文档.md"
DB_LOG = PLAY / "数据库变更记录.md"
DECISIONS_FILE = PLAY / "决策记录.md"
FIXES_FILE = PLAY / "错误与修复记录.md"


def _ensure_today_section(path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(f"# {title}\n\n", encoding="utf-8")
    text = path.read_text(encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d")
    if f"## {today}" not in text:
        text += f"\n## {today}\n"
        path.write_text(text, encoding="utf-8")


def _append_items(path: Path, items: List[str]) -> None:
    with path.open("a", encoding="utf-8") as f:
        for it in items:
            f.write(f"- {it}\n")


def _append_under_section(path: Path, section: str, items: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(f"# {path.stem}\n\n## {section}\n", encoding="utf-8")
    text = path.read_text(encoding="utf-8")
    marker = f"## {section}"
    if marker not in text:
        text = text.rstrip() + f"\n\n{marker}\n"
    text = text.rstrip() + "\n" + "\n".join(f"- {x}" for x in items) + "\n"
    path.write_text(text, encoding="utf-8")


# Heuristics（严格版）

def is_fix(file: str, highlights: List[str]) -> bool:
    """严格：必须包含明确修复/错误类关键词才算修复。"""
    text = (file + " " + " ".join(highlights)).lower()
    en = ["fix", "bug", "hotfix", "exception", "error", "rollback", "regression"]
    zh = ["修复", "异常", "报错", "错误", "回滚", "缺陷", "回归"]
    return any(k in text for k in en) or any(k in text for k in zh)


def is_decision(file: str, highlights: List[str]) -> bool:
    """严格：满足以下任一即可：
    - 出现决策/策略/兼容性/迁移/破坏性等明确关键词（中英）
    - API 路由变更且路径位于 app/api/
    - 含 ADR/DEC 标记
    """
    text = (file + " " + " ".join(highlights)).lower()
    # 强关键词
    en = ["decision", "adr", "design decision", "policy", "strategy", "breaking change", "compat", "deprecate", "deprecation", "tradeoff", "governance"]
    zh = ["决策", "取舍", "方案", "策略", "原则", "架构", "迁移", "兼容性", "破坏性", "弃用", "约定", "规范", "标准"]
    if any(k in text for k in en) or any(k in text for k in zh):
        return True
    # API 路由严格匹配：既要有 API 路由高亮，又需位于 app/api/
    if any(h.startswith("API ") for h in highlights) and ("app/api/" in file):
        return True
    # ADR/DEC 标识（文件名或内容）
    if "adr" in text or "dec-" in text:
        return True
    return False


def route_and_write(grouped: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Path]]:
    written: Dict[str, List[Path]] = {}
    titles = {
        "code": "改进与优化记录（增量）",
        "config": "配置变更记录",
        "docs": "经验教训",
        "other": "开放问题与待澄清",
    }
    decision_lines: List[str] = []
    fix_lines: List[str] = []

    for typ, entries in grouped.items():
        if not entries:
            continue
        if typ == "db":
            # 写入数据库设计文档的“变更记录”
            today = datetime.now().strftime("%Y-%m-%d")
            lines_dbfile: List[str] = []
            lines_dblog: List[str] = []
            for e in entries:
                file = e.get("file", "")
                hs = e.get("highlights", []) or []
                line = f"{today}｜{file}"
                if hs:
                    line += "：" + "; ".join(hs)
                lines_dbfile.append(line)
                lines_dblog.append(f"{file}：" + ("; ".join(hs) if hs else "无要点"))
                if is_decision(file, hs):
                    decision_lines.append(f"{file}：" + ("; ".join(hs) if hs else ""))
                if is_fix(file, hs):
                    fix_lines.append(f"{file}：" + ("; ".join(hs) if hs else ""))
            _append_under_section(DB_FILE, "变更记录", lines_dbfile)
            _ensure_today_section(DB_LOG, "数据库变更记录")
            _append_items(DB_LOG, lines_dblog)
            written.setdefault("db", []).extend([DB_FILE, DB_LOG])
            continue

        dst = FILES_BY_TYPE.get(typ)
        if not dst:
            continue
        _ensure_today_section(dst, titles.get(typ, dst.stem))
        lines: List[str] = []
        for e in entries:
            file = e.get("file", "")
            hs = e.get("highlights", []) or []
            lines.append(f"{file}：" + ("; ".join(hs) if hs else ""))
            if is_decision(file, hs):
                decision_lines.append(f"{file}：" + ("; ".join(hs) if hs else ""))
            if is_fix(file, hs):
                fix_lines.append(f"{file}：" + ("; ".join(hs) if hs else ""))
        _append_items(dst, lines)
        written.setdefault(typ, []).append(dst)

    if decision_lines:
        _ensure_today_section(DECISIONS_FILE, "决策记录")
        _append_items(DECISIONS_FILE, decision_lines)
        written.setdefault("decision", []).append(DECISIONS_FILE)

    if fix_lines:
        _ensure_today_section(FIXES_FILE, "错误与修复记录")
        _append_items(FIXES_FILE, fix_lines)
        written.setdefault("fix", []).append(FIXES_FILE)

    return written

