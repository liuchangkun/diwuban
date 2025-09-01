#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pre-commit 提醒：若本次提交修改了 docs/PLAYBOOKS 或 docs/ 下文档，但未更新 知识图谱.json，则提示运行 kg_update.py。
- 永远 exit 0（提醒不拦截）
- 通过 git diff --name-only --cached 获取暂存区文件列表
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KG = ROOT / "docs" / "PLAYBOOKS" / "知识图谱.json"


def get_staged_files() -> list[str]:
    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", "--cached"], text=True
        )
        return [
            line.strip().replace("\\", "/") for line in out.splitlines() if line.strip()
        ]
    except Exception:
        return []


def main() -> int:
    staged = get_staged_files()
    if not staged:
        return 0
    touched_docs = any(f.startswith("docs/") for f in staged)
    touched_play = any(f.startswith("docs/PLAYBOOKS/") for f in staged)
    touched_kg = any(f == "docs/PLAYBOOKS/知识图谱.json" for f in staged)

    if (touched_docs or touched_play) and not touched_kg:
        print(
            "[KG-REMINDER] 检测到文档/PLAYBOOKS 变更，建议运行: python scripts/tools/kg_update.py 并提交 docs/PLAYBOOKS/知识图谱.json"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
