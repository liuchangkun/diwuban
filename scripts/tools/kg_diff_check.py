#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pre-commit：轻量提示运行 kg_update 是否会产生变化
- 原理：临时运行 kg_update 并比较生成内容与暂存区中的知识图谱是否一致
- 若将产生变化且未暂存图谱，则输出提示（不拦截）
"""
from __future__ import annotations

# import io  # 未使用，移除以通过 ruff F401
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KG = ROOT / "docs" / "PLAYBOOKS" / "知识图谱.json"


def main() -> int:
    try:
        from kg_update import infer_nodes_and_edges  # type: ignore
    except Exception:
        # 直接导入同目录脚本
        sys.path.insert(0, str((ROOT / "scripts" / "tools").resolve()))
        from kg_update import infer_nodes_and_edges  # type: ignore

    current = KG.read_text(encoding="utf-8") if KG.exists() else ""
    kg = infer_nodes_and_edges()
    kg["meta"] = {
        "node_count": len(kg.get("nodes", [])),
        "edge_count": len(kg.get("edges", [])),
    }
    generated = json.dumps(kg, ensure_ascii=False, indent=2)
    if generated != current:
        print(
            "[KG-DIFF] 运行 kg_update.py 将产生更新，建议先执行并提交 docs/PLAYBOOKS/知识图谱.json"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
