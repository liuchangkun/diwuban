# -*- coding: utf-8 -*-
"""
将运行时快照自动注入文档（中文注释）
- API 路由快照 -> docs/应用接口说明.md 的“API 路由清单（自动生成）”分节
- CLI 帮助快照 -> docs/程序工作流程.md 的“命令帮助（自动生成）”分节
- DB 结构快照 -> docs/数据库设计文档.md 的“实库结构（自动生成）”分节

可回滚性：仅替换标记之间的内容；若无标记则在文末追加，避免覆盖人工内容。
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
SNAP_API = DOCS / "_archive" / "reports" / "api_routes_snapshot.md"
SNAP_CLI = DOCS / "_archive" / "reports" / "cli_help.txt"
SNAP_DB = DOCS / "_archive" / "reports" / "db_schema_snapshot.md"

MD_API = DOCS / "应用接口说明.md"
MD_FLOW = DOCS / "程序工作流程.md"
MD_DB = DOCS / "数据库设计文档.md"

SECTION_API = (
    "<!-- BEGIN:API_AUTO -->",
    "## API 路由清单（自动生成）",
    "<!-- END:API_AUTO -->",
)
SECTION_CLI = (
    "<!-- BEGIN:CLI_AUTO -->",
    "## 命令帮助（自动生成）",
    "<!-- END:CLI_AUTO -->",
)
SECTION_DB = (
    "<!-- BEGIN:DB_AUTO -->",
    "## 实库结构（自动生成）",
    "<!-- END:DB_AUTO -->",
)


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore") if p.exists() else ""


def replace_section(orig: str, begin: str, title: str, end: str, body: str) -> str:
    """在 begin/end 标记之间替换内容；若不存在则在文末追加"""
    pattern = re.compile(re.escape(begin) + r"[\s\S]*?" + re.escape(end), re.M)
    block = f"{begin}\n\n{title}\n\n{body}\n\n{end}"
    if pattern.search(orig):
        return pattern.sub(block, orig)
    else:
        if not orig.endswith("\n"):
            orig += "\n"
        return orig + "\n" + block + "\n"


def gen_api_body() -> str:
    snap = _read_text(SNAP_API)
    if not snap:
        return "_未找到运行时 API 路由快照_"
    lines = []
    for ln in snap.splitlines():
        if ln.strip().startswith("- "):
            lines.append(ln)
    return "\n".join(lines) if lines else "_快照中未解析到路由条目_"


def gen_cli_body() -> str:
    snap = _read_text(SNAP_CLI)
    if not snap:
        return "_未找到 CLI 帮助快照_"
    return "````text\n" + snap.strip() + "\n````"


def gen_db_body() -> str:
    snap = _read_text(SNAP_DB)
    if not snap:
        return "_未找到数据库结构快照_"
    # 仅摘录三个分节，避免过长：表列表、部分列明细、索引摘要
    parts = []
    cur_sec = None
    buf: list[str] = []
    for ln in snap.splitlines():
        if ln.startswith("## "):
            if cur_sec:
                parts.append((cur_sec, "\n".join(buf)))
            cur_sec = ln.strip("# ").strip()
            buf = []
        else:
            buf.append(ln)
    if cur_sec:
        parts.append((cur_sec, "\n".join(buf)))

    keep = {}
    for name, body in parts:
        if name.startswith("表列表"):
            keep["表列表"] = "\n".join(body.splitlines()[:300])
        if name.startswith("列明细"):
            keep["列明细"] = "\n".join(body.splitlines()[:400])
        if name.startswith("索引"):
            keep["索引"] = "\n".join(body.splitlines()[:200])
    out_lines = []
    for k in ("表列表", "列明细", "索引"):
        if k in keep:
            out_lines.append(f"### {k}")
            out_lines.append(keep[k])
            out_lines.append("")
    return "\n".join(out_lines) if out_lines else "_快照解析为空_"


def main():
    # 应用接口说明
    api_md = _read_text(MD_API)
    api_body = gen_api_body()
    api_md2 = replace_section(api_md, *SECTION_API, api_body)
    MD_API.write_text(api_md2, encoding="utf-8")
    try:
        from scripts.dev.action_logger import log_with_files

        log_with_files("已注入 API 路由快照到自动分节", ["docs/应用接口说明.md"])
    except Exception:
        pass

    # 程序工作流程（CLI 帮助）
    flow_md = _read_text(MD_FLOW)
    cli_body = gen_cli_body()
    flow_md2 = replace_section(flow_md, *SECTION_CLI, cli_body)
    MD_FLOW.write_text(flow_md2, encoding="utf-8")
    try:
        from scripts.dev.action_logger import log_with_files

        log_with_files("已注入 CLI 帮助快照到自动分节", ["docs/程序工作流程.md"])
    except Exception:
        pass

    # 数据库设计文档（实库结构）
    db_md = _read_text(MD_DB)
    db_body = gen_db_body()
    db_md2 = replace_section(db_md, *SECTION_DB, db_body)
    MD_DB.write_text(db_md2, encoding="utf-8")
    try:
        from scripts.dev.action_logger import log_with_files

        log_with_files("已注入 DB 结构快照到自动分节", ["docs/数据库设计文档.md"])
    except Exception:
        pass

    print("[OK] 文档已从快照自动注入完成")


if __name__ == "__main__":
    main()
