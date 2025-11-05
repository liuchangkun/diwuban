# -*- coding: utf-8 -*-
"""
自动扫描最近一次提交变更（或工作区未提交变更），分类汇总：
- 功能/接口（app/api, app/services, app/schemas）
- 代码（app/ 其它模块）
- 数据库（scripts/sql/** 或 *.sql）
- 文档（docs/**）
并将摘要写入 docs/PLAYBOOKS/对话记忆.md（按日期合并），随后自动刷新 memory_index 与 MEMORY_AUTO 区块。

注意：
- 仅执行只读 git 命令；若无 git 或无提交历史，会回退到工作区的未提交变更（git diff --name-only）。
- 不安装新依赖。
"""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
import sys

# 动态引入解析与路由模块
sys.path.append(str((Path(__file__).resolve().parents[1] / "dev").resolve()))
from diff_parser import collect_changes  # type: ignore
from memory_router import route_and_write  # type: ignore

ROOT = Path(__file__).resolve().parents[2]
DOC_MEMO = ROOT / "docs" / "PLAYBOOKS" / "对话记忆.md"

# 允许统计的根目录（减少“其他”噪声）
ALLOWED_ROOTS = ["app/", "scripts/sql/", "docs/", "configs/"]
# 默认忽略清单（与守护进程一致）
IGNORED_DIR_NAMES = {
    ".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "node_modules", "dist", "build", "logs"
}
IGNORED_BASENAMES = {"Thumbs.db", ".DS_Store"}
IGNORED_EXTS = {".log", ".tmp", ".bak", ".swp", ".swo"}
USER_IGNORE_FILE = ROOT / "configs" / "自动记忆忽略清单.txt"
USER_IGNORES: list[str] = []
if USER_IGNORE_FILE.exists():
    try:
        USER_IGNORES = [ln.strip() for ln in USER_IGNORE_FILE.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.strip().startswith("#")]
    except Exception:
        USER_IGNORES = []

def _allowed_and_not_ignored(name: str) -> bool:
    n = name.replace("\\", "/")
    if not any(n.startswith(r) for r in ALLOWED_ROOTS):
        return False
    parts = n.split("/")
    if any(p in IGNORED_DIR_NAMES for p in parts[:-1]):
        return False
    base = parts[-1]
    if base in IGNORED_BASENAMES:
        return False
    import os as _os
    if _os.path.splitext(base)[1].lower() in IGNORED_EXTS:
        return False
    if any(tok in n for tok in USER_IGNORES):
        return False
    return True


def _run_git(args: list[str]) -> tuple[int, str]:
    """以更稳健的方式运行 git，并关闭非 ASCII 转义（core.quotepath=false）。
    在 Windows 上按系统首选编码解码，其他平台优先 UTF-8。
    """
    import locale, os
    enc = locale.getpreferredencoding(False) or "utf-8"
    try:
        out = subprocess.check_output(["git", "-c", "core.quotepath=false", *args], cwd=str(ROOT))
        try:
            return 0, out.decode("utf-8")
        except Exception:
            return 0, out.decode(enc, errors="ignore")
    except Exception as e:
        return 1, str(e)


def _get_changed_files() -> list[str]:
    names: set[str] = set()
    # 最近一次提交范围
    rc, _ = _run_git(["rev-parse", "--verify", "HEAD~1"])
    if rc == 0:
        rc2, out2 = _run_git(["diff", "--name-only", "HEAD~1..HEAD"])
        if rc2 == 0 and out2.strip():
            names.update(x.strip() for x in out2.splitlines() if x.strip())
    # 工作区未提交变更
    rc3, out3 = _run_git(["diff", "--name-only"])
    if rc3 == 0 and out3.strip():
        names.update(x.strip() for x in out3.splitlines() if x.strip())
    # 未跟踪文件（新建文件，也算变更）
    rc4, out4 = _run_git(["ls-files", "--others", "--exclude-standard"])
    if rc4 == 0 and out4.strip():
        names.update(x.strip() for x in out4.splitlines() if x.strip())
    # 
    return sorted(n for n in names if _allowed_and_not_ignored(n))


def _classify(paths: list[str]) -> dict[str, list[str]]:
    cats = {"功能/接口": [], "代码": [], "数据库": [], "文档": [], "其他": []}
    for p in paths:
        lp = p.lower()
        if lp.startswith("docs/"):
            cats["文档"].append(p)
        elif lp.endswith(".sql") or lp.startswith("scripts/sql/"):
            cats["数据库"].append(p)
        elif lp.startswith("app/api/") or lp.startswith("app/services/") or lp.startswith("app/schemas/"):
            cats["功能/接口"].append(p)
        elif lp.startswith("app/"):
            cats["代码"].append(p)
        else:
            cats["其他"].append(p)
    return cats

# --- 会话滚动摘要（AUTO 块） ---
SESSION_KEY = "SESSION"
BEGIN = f"<!-- AUTO-WIKI:BEGIN:{SESSION_KEY} -->"
END = f"<!-- AUTO-WIKI:END:{SESSION_KEY} -->"

def _upsert_session_block(text: str, md: str) -> str:
    if BEGIN in text and END in text and text.index(BEGIN) < text.index(END):
        prefix = text.split(BEGIN, 1)[0]
        suffix = text.split(END, 1)[1]
        return f"{prefix}{BEGIN}\n\n{md}\n{END}{suffix}"
    return text.rstrip() + f"\n\n{BEGIN}\n\n{md}\n{END}\n"



def _append_memo(cats: dict[str, list[str]], grouped: dict[str, list[dict]], written: dict[str, list[Path]], source_note: str) -> None:
    today = datetime.now(timezone.utc).astimezone().date().isoformat()
    # 1) 构建 EDE 风格的可执行摘要（简短）
    ede: list[str] = []
    ede.append(f"### 会话滚动摘要（{today}）\n")
    ede.append("- 决策：-")
    ede.append("- 约束：-")
    ede.append("- 风险：-")
    ede.append("- 命名/术语：-")
    ede.append("- 待办：-")
    ede.append("")

    # 2) 变更分类概览（每类最多 2 条示例）
    lines: list[str] = []
    hl_by_file: dict[str, list[str]] = {}
    for _, entries in grouped.items():
        for e in entries:
            f = str(e.get("file", ""))
            if f:
                hl_by_file[f] = e.get("highlights", []) or []
    mapping = {"功能/接口": ("code", "代码"), "代码": ("code", "代码"), "数据库": ("db", "数据库"), "文档": ("docs", "文档"), "其他": ("other", "其他")}
    order = ["功能/接口", "代码", "数据库", "文档", "其他"]
    for k in order:
        items = cats.get(k, [])
        if not items:
            continue
        typ = mapping[k][0]
        dsts = [p for p in written.get(typ, [])]
        dst_hint = ", ".join(str(p.relative_to(ROOT)).replace("\\", "/") for p in dsts) if dsts else "（未生成目标文档）"
        lines.append(f"- {k}（{len(items)}）→ 更新：{dst_hint}")
        for s in items[:2]:
            ex_hl = hl_by_file.get(s, [])
            if ex_hl:
                lines.append(f"  - {s}｜要点：{'; '.join(ex_hl[:2])}")
            else:
                lines.append(f"  - {s}")
        if len(items) > 2:
            lines.append(f"  - ... 等 {len(items) - 2} 项")
    if not lines:
        lines.append("- 本次未检测到变更（可能是空提交或变更被忽略）。")
    lines.append(f"- 来源：{source_note}")

    md = "\n".join(ede + ["## 本轮变更摘要", *lines, "", f"> 生成时间：{today}"]) + "\n"

    # 3) 写入/更新 AUTO 块
    if not DOC_MEMO.exists():
        DOC_MEMO.parent.mkdir(parents=True, exist_ok=True)
        DOC_MEMO.write_text("# 对话记忆（自动记录索引）\n\n", encoding="utf-8")
    text = DOC_MEMO.read_text(encoding="utf-8")
    new_text = _upsert_session_block(text, md)
    DOC_MEMO.write_text(new_text, encoding="utf-8")


def _auto_refresh_memory_index() -> None:
    # 顺序：更新索引 → 回写摘要 → 条件归档 → 同步 wiki 片段 → 生成项目总览
    subprocess.call([sys.executable, str(ROOT / "scripts" / "dev" / "update_memory_index.py")], cwd=str(ROOT))
    subprocess.call([sys.executable, str(ROOT / "scripts" / "dev" / "compose_memory_snapshot.py")], cwd=str(ROOT))
    # 执行基于标签的归档（[归档]/[过时]）
    subprocess.call([sys.executable, str(ROOT / "scripts" / "dev" / "auto_archive_playbooks.py")], cwd=str(ROOT))
    # 同步 wiki 片段（友好文案 + 注释），失败不影响主流程
    try:
        subprocess.call([sys.executable, str(ROOT / "scripts" / "dev" / "sync_wiki_from_playbooks.py")], cwd=str(ROOT))
    except Exception:
        pass
    # 生成面向人类阅读的“项目总览”（API/流程/数据库/配置）
    try:
        subprocess.call([sys.executable, str(ROOT / "scripts" / "dev" / "generate_project_wiki.py")], cwd=str(ROOT))
    except Exception:
        pass


def main() -> None:
    files = _get_changed_files()
    # 严格忽略：
    # - 系统输出（PLAYBOOKS、generated、DB 设计文档）
    # - 人工文档编辑（docs/** 全部）
    files = [
        f for f in files
        if not f.startswith("docs/")
        and not f.startswith("docs\\")
        and not f.startswith("generated/")
        and f != "docs/数据库设计文档.md"
    ]
    source_note = "git diff HEAD~1..HEAD" if files else "git diff 工作区"
    #
    grouped = collect_changes(files)
    written = route_and_write(grouped)
    #
    cats = _classify(files)
    _append_memo(cats, grouped, written, source_note)
    _auto_refresh_memory_index()
    print("[OK] 自动变更扫描与记忆更新完成。检测到变更文件数:", sum(len(v) for v in cats.values()))


if __name__ == "__main__":
    main()

