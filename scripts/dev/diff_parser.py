# -*- coding: utf-8 -*-
"""
简易 diff 解析器（最小可用）：
- 读取 git diff -U0 的补丁，抽取“有意义的变更要点”，用于自动路由写入文档。
- 关心的提取：
  * Python：def/class 名称、新增路由/装饰器（@router.*、@app.*）
  * SQL：CREATE/ALTER FUNCTION/PROCEDURE/VIEW/MATERIALIZED VIEW/TABLE/INDEX 名称
  * Markdown：新增标题（#、##）与列表条目
  * YAML/JSON：新增或修改的 key 名称（粗粒度）
- 仅做启发式提取，避免复杂 AST/SQL 解析。
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]

# ---------- git helpers ----------

def run_git(args: List[str]) -> Tuple[int, str]:
    try:
        out = subprocess.check_output(["git", "-c", "core.quotepath=false", *args], cwd=str(ROOT))
        try:
            return 0, out.decode("utf-8")
        except Exception:
            import locale
            return 0, out.decode(locale.getpreferredencoding(False) or "utf-8", errors="ignore")
    except Exception as e:
        return 1, str(e)


def get_file_diff_unified0(path: str) -> str:
    # 优先最近两次提交的 diff
    rc, _ = run_git(["rev-parse", "--verify", "HEAD~1"])
    if rc == 0:
        rc2, out2 = run_git(["diff", "-U0", "HEAD~1..HEAD", "--", path])
        if rc2 == 0 and out2.strip():
            return out2
    # 回退到工作区 diff
    rc3, out3 = run_git(["diff", "-U0", "--", path])
    if rc3 == 0:
        return out3
    return ""

# ---------- extractors ----------

PY_DEF_RE = re.compile(r"^\+\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\(")
PY_CLASS_RE = re.compile(r"^\+\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\(")
PY_ROUTER_RE = re.compile(r"^\+\s*@(?:router|app)\.")

SQL_OBJ_RE = re.compile(
    r'^\+\s*(?:CREATE|ALTER)\s+(?:OR\s+REPLACE\s+)?(FUNCTION|PROCEDURE|VIEW|MATERIALIZED\s+VIEW|TABLE|INDEX)\s+([A-Za-z0-9_\."]+)',
    re.IGNORECASE,
)

MD_HEADING_RE = re.compile(r"^\+\s*(#{1,3})\s+(.+)")
MD_LISTITEM_RE = re.compile(r"^\+\s*[-*]\s+(.+)")

YAML_KEY_RE = re.compile(r"^\+\s*([A-Za-z0-9_\.\-]+)\s*:\s*(.+)?$")
JSON_KEY_RE = re.compile(r"^\+\s*\"([A-Za-z0-9_\-]+)\"\s*:\s*(.+)?$")


def parse_file_changes(path: str) -> Dict[str, Any]:
    rel = path.replace("\\", "/")
    diff = get_file_diff_unified0(rel)
    if not diff:
        return {"file": rel, "highlights": [], "type": guess_type(rel)}
    highlights: List[str] = []
    for line in diff.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        if rel.endswith(".py"):
            m1 = PY_DEF_RE.match(line)
            if m1:
                highlights.append(f"Python 函数: {m1.group(1)}()")
                continue
            m2 = PY_CLASS_RE.match(line)
            if m2:
                highlights.append(f"Python 类: {m2.group(1)}")
                continue
            if PY_ROUTER_RE.match(line):
                highlights.append("API 路由/装饰器 变更")
                continue
        elif rel.endswith(".sql"):
            m3 = SQL_OBJ_RE.match(line)
            if m3:
                kind, name = m3.group(1).upper().replace("  ", " "), m3.group(2)
                highlights.append(f"SQL {kind}: {name}")
                continue
        elif rel.endswith(".md"):
            m4 = MD_HEADING_RE.match(line)
            if m4:
                level, title = m4.group(1), m4.group(2).strip()
                highlights.append(f"文档标题新增: {level} {title}")
                continue
            m5 = MD_LISTITEM_RE.match(line)
            if m5:
                highlights.append(f"文档条目新增: {m5.group(1).strip()}")
                continue
        elif rel.endswith(('.yaml', '.yml')):
            m6 = YAML_KEY_RE.match(line)
            if m6:
                k = m6.group(1)
                highlights.append(f"配置键变更: {k}")
                continue
        elif rel.endswith('.json'):
            m7 = JSON_KEY_RE.match(line)
            if m7:
                k = m7.group(1)
                highlights.append(f"配置键变更: {k}")
                continue
    return {"file": rel, "highlights": highlights, "type": guess_type(rel)}


def guess_type(path: str) -> str:
    p = path.lower()
    if p.startswith("app/api/") or p.startswith("app/services/") or p.startswith("app/schemas/") or p.startswith("app/"):
        return "code"
    if p.endswith(".sql") or p.startswith("scripts/sql/"):
        return "db"
    if p.startswith("docs/"):
        return "docs"
    if p.startswith("configs/") or p.endswith((".yaml", ".yml", ".json")):
        return "config"
    return "other"


def collect_changes(files: List[str]) -> Dict[str, Any]:
    grouped: Dict[str, List[Dict[str, Any]]] = {"code": [], "db": [], "docs": [], "config": [], "other": []}
    for f in files:
        info = parse_file_changes(f)
        grouped.get(info["type"], grouped["other"]).append(info)
    return grouped

