# -*- coding: utf-8 -*-
"""
导出 CLI 帮助到 UTF-8 文本（中文注释）
- 执行 `python -m app.cli.main --help` 并捕获 stdout
- 保存至 docs/_archive/reports/cli_help.txt（UTF-8 无 BOM）
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "_archive" / "reports" / "cli_help.txt"


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # 在当前 Python 进程中调用模块
    result = subprocess.run(
        [sys.executable, "-m", "app.cli.main", "--help"],
        capture_output=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr.decode(errors="ignore"))
        print("[ERR] CLI --help 失败")
        sys.exit(result.returncode)
    raw = result.stdout
    text = None
    for enc in ("utf-8", "utf-16", "gbk", "cp936", "latin1"):
        try:
            text = raw.decode(enc)
            break
        except Exception:
            continue
    if text is None:
        text = raw.decode("utf-8", errors="ignore")
    OUT.write_text(text, encoding="utf-8")
    print("[OK] CLI 帮助已导出:", OUT)


if __name__ == "__main__":
    main()
