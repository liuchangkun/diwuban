#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PLAYBOOKS 中文命名与引用检查

- 预提交（pre-commit）模式：仅提醒（exit 0）
- 严格（CI）模式：发现问题直接失败（exit 1），通过环境变量 STRICT=1 开启

检查项：
1) docs/PLAYBOOKS 下文件名不得包含英文字母 [A-Za-z] 或下划线 '_'
2) 会话快照文件命名必须为：会话快照_YYYY-MM-DD.md
3) 基础可达性：索引/使用说明存在；文档地图包含 PLAYBOOKS 入口（轻量检测）
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAY_DIR = ROOT / "docs" / "PLAYBOOKS"
DOC_MAP = ROOT / "docs" / "文档地图与导航.md"

NAME_EN_PATTERN = re.compile(r"[A-Za-z]")
SNAPSHOT_OK = re.compile(r"^会话快照_\d{4}-\d{2}-\d{2}\.md$")


def warn(msg: str) -> None:
    print(f"[PLAYBOOKS-NAMING] {msg}")


def main() -> int:
    strict = os.getenv("STRICT", "0") in {"1", "true", "TRUE"}
    problems: list[str] = []

    if not PLAY_DIR.exists():
        warn(f"未找到目录：{PLAY_DIR}")
        return 0

    # 1) 文件命名检查
    for p in sorted(PLAY_DIR.glob("*")):
        if p.is_dir():
            continue
        name = p.name
        if NAME_EN_PATTERN.search(name) or ("_" in name and not name.startswith("_")):
            problems.append(f"文件名包含英文字母或下划线：{name}（请改为中文名）")
        # 会话快照命名规范
        if ("会话快照" in name) and not SNAPSHOT_OK.match(name):
            problems.append(
                f"会话快照命名不规范：{name}（期望：会话快照_YYYY-MM-DD.md）"
            )
        if name.upper().startswith("SESSION_SNAPSHOT"):
            problems.append(
                f"发现英文命名的会话快照：{name}（请改名为 会话快照_YYYY-MM-DD.md）"
            )

    # 2) 基础可达性（轻量）
    must_exist = [PLAY_DIR / "索引.md", PLAY_DIR / "使用说明.md"]
    for m in must_exist:
        if not m.exists():
            problems.append(f"缺少基础文档：{m.relative_to(ROOT)}")

    if not DOC_MAP.exists() or "PLAYBOOKS" not in DOC_MAP.read_text(
        encoding="utf-8", errors="ignore"
    ):
        problems.append(
            "文档地图缺少 PLAYBOOKS 入口或文件不存在：docs/文档地图与导航.md"
        )

    if problems:
        for msg in problems:
            warn(msg)
        return 1 if strict else 0

    warn("检查通过：PLAYBOOKS 中文命名与可达性正常")
    return 0


if __name__ == "__main__":
    sys.exit(main())
