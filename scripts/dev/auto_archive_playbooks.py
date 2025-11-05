# -*- coding: utf-8 -*-
"""
基于 memory_index.json 的简易归档：
- 规则（最小实现）：若文档首行含有标签 [归档] 或 [过时]，则移动到 docs/_archive/PLAYBOOKS/YYYY-MM-DD/ 下。
- 未来可扩展：基于 last_updated、superseded_by、references 等策略。
"""
from __future__ import annotations
import json, shutil
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "generated" / "memory_index.json"
PB_DIR = ROOT / "docs" / "PLAYBOOKS"
ARCH = ROOT / "docs" / "_archive" / "PLAYBOOKS"


def main() -> None:
    if not INDEX.exists():
        print("memory_index.json not found, skip")
        return
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    moved = []
    for it in data.get("items", []):
        if it.get("type") != "PLAYBOOK":
            continue
        p = ROOT / it["path"]
        if not p.exists():
            continue
        first = p.read_text(encoding="utf-8").splitlines()[:1]
        if first and ("[归档]" in first[0] or "[过时]" in first[0]):
            day = (datetime.now()).strftime("%Y-%m-%d")
            dst = ARCH / day
            dst.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(dst / p.name))
            moved.append(str(p))
    if moved:
        print("archived:")
        for m in moved:
            print(" -", m)


if __name__ == "__main__":
    main()

