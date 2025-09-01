#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CI 轻量提醒：本 PR 是否更新了 docs/PLAYBOOKS/知识图谱.json
- 若检测到 docs/ 或 docs/PLAYBOOKS 改动，但图谱未变化，则以警告输出提示（不 fail）
- 可通过 STRICT=1 设为严格模式（fail）
"""
from __future__ import annotations

# import json  # 未使用，移除以通过 ruff F401
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KG_PATH = "docs/PLAYBOOKS/知识图谱.json"


def git_diff_name_status() -> list[tuple[str, str]]:
    out = subprocess.check_output(
        ["git", "diff", "--name-status", "origin/${{ github.base_ref }}...HEAD"],
        text=True,
    )
    pairs = []
    for line in out.splitlines():
        if not line.strip():
            continue
        status, path = line.split("\t", 1)
        pairs.append((status, path))
    return pairs


def main() -> int:
    strict = os.getenv("STRICT", "0") in {"1", "true", "TRUE"}
    try:
        changes = git_diff_name_status()
    except Exception as e:
        print(f"[KG-CI] 无法获取 diff：{e}")
        return 0

    touched_docs = any(p.startswith("docs/") for _, p in changes)
    touched_play = any(p.startswith("docs/PLAYBOOKS/") for _, p in changes)
    touched_kg = any(p == KG_PATH for _, p in changes)

    if (touched_docs or touched_play) and not touched_kg:
        msg = "[KG-CI] 检测到文档/PLAYBOOKS 变更，但知识图谱未更新（建议运行 scripts/tools/kg_update.py 并提交图谱）。"
        print(msg)
        return 1 if strict else 0

    print("[KG-CI] 检查通过或无关变更。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
