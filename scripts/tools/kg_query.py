#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识图谱查询（纯标准库）
用法示例：
  python scripts/tools/kg_query.py nodes type=Decision
  python scripts/tools/kg_query.py edges rel=documents
  python scripts/tools/kg_query.py neighbors id=DEC-20250819-010 hops=1
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KG = ROOT / "docs" / "PLAYBOOKS" / "知识图谱.json"


def load() -> dict:
    if not KG.exists():
        print("知识图谱不存在，请先运行 kg_update.py", file=sys.stderr)
        sys.exit(1)
    return json.loads(KG.read_text(encoding="utf-8"))


def q_nodes(kg: dict, args: dict) -> None:
    t = args.get("type")
    for n in kg.get("nodes", []):
        if t and n.get("type") != t:
            continue
        print(n)


def q_edges(kg: dict, args: dict) -> None:
    r = args.get("rel")
    for e in kg.get("edges", []):
        if r and e.get("rel") != r:
            continue
        print(e)


def neighbors(kg: dict, args: dict) -> None:
    node_id = args.get("id")
    hops = int(args.get("hops", 1))
    if not node_id:
        print("缺少 id 参数", file=sys.stderr)
        sys.exit(2)
    frontier = {node_id}
    seen = set(frontier)
    for _ in range(hops):
        nxt = set()
        for e in kg.get("edges", []):
            if e.get("src") in frontier:
                nxt.add(e.get("dst"))
            if e.get("dst") in frontier:
                nxt.add(e.get("src"))
        frontier = {x for x in nxt if x not in seen}
        seen |= frontier
    print(sorted(seen))


def parse(argv: list[str]) -> tuple[str, dict]:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(0)
    cmd = argv[1]
    kv = {}
    for a in argv[2:]:
        if "=" in a:
            k, v = a.split("=", 1)
            kv[k] = v
    return cmd, kv


def main() -> int:
    cmd, kv = parse(sys.argv)
    kg = load()
    if cmd == "nodes":
        q_nodes(kg, kv)
    elif cmd == "edges":
        q_edges(kg, kv)
    elif cmd == "neighbors":
        neighbors(kg, kv)
    else:
        print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
