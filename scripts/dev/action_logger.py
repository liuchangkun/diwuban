# -*- coding: utf-8 -*-
"""简单的对齐执行日志记录器（中文注释）
将关键动作以一行记录追加到 docs/_archive/reports/对齐执行流水.md，便于你实时查看。
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "docs" / "_archive" / "reports"
LOG_FILE = LOG_DIR / "对齐执行流水.md"


def log(message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = "# 对齐执行流水\n\n> 本文件用于展示我在仓库内执行的每一步动作，按时间倒序追加。\n\n"
    if not LOG_FILE.exists() or LOG_FILE.stat().st_size == 0:
        LOG_FILE.write_text(header, encoding="utf-8")
    with LOG_FILE.open("a", encoding="utf-8") as fw:
        fw.write(f"- [{ts}] {message}\n")


def log_with_files(message: str, files: list[str]) -> None:
    files_part = ", ".join(files) if files else "(no files)"
    log(f"{message} | files: {files_part}")


if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    if not args:
        log("(no message)")
    else:
        if "--files" in args:
            idx = args.index("--files")
            msg = " ".join(args[:idx]) if idx > 0 else "(no message)"
            files = args[idx + 1 :]
            log_with_files(msg, files)
        else:
            msg = " ".join(args)
            log(msg)
