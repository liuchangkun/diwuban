#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 PLAYBOOKS 与 docs 扫描生成/合并“知识图谱”JSON。
- 存储：docs/PLAYBOOKS/知识图谱.json
- 仅使用标准库，默认增量合并（保留未知节点/关系）
- 规则：
  * 节点类型：Decision/ConfigChange/Improvement/Lesson/Benchmark/Runbook/Doc/Script
  * 关系：documents/implements/depends_on/impacts/relates_to/supersedes/verifies/located_in_doc
  * 从文件名与标题推断节点；从文本中的“参见/参考/链接/脚本/文档”行推断关系（启发式）
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[2]
PLAY = ROOT / "docs" / "PLAYBOOKS"
DOCS = ROOT / "docs"
KG = PLAY / "知识图谱.json"

NODE_TYPES = {
    "决策记录.md": "Decision",
    "配置变更记录.md": "ConfigChange",
    "改进与优化记录.md": "Improvement",
    "经验教训.md": "Lesson",
    "性能基准.md": "Benchmark",
    "运行手册变更.md": "Runbook",
}

REL_HINTS = {
    "documents": ["参见", "参考", "详见", "文档", "链接"],
    "implements": ["脚本", "实现", "函数"],
    "depends_on": ["依赖", "前置", "需要"],
    "impacts": ["影响", "作用于"],
    "relates_to": ["相关", "关联"],
    "supersedes": ["替代", "废弃", "取代"],
    "verifies": ["验证", "校验"],
}

TITLE_RE = re.compile(r"^#\s*(.+)$", re.M)
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def load_kg() -> Dict[str, Any]:
    if KG.exists():
        try:
            return json.loads(KG.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"nodes": [], "edges": []}


def add_node(kg: Dict[str, Any], node_id: str, ntype: str, title: str) -> None:
    if not any(n.get("id") == node_id for n in kg["nodes"]):
        kg["nodes"].append({"id": node_id, "type": ntype, "title": title})


def add_edge(kg: Dict[str, Any], src: str, rel: str, dst: str) -> None:
    if not any(
        e
        for e in kg["edges"]
        if e.get("src") == src and e.get("rel") == rel and e.get("dst") == dst
    ):
        kg["edges"].append({"src": src, "rel": rel, "dst": dst})


def infer_nodes_and_edges() -> Dict[str, Any]:
    kg = load_kg()

    # 扫描 PLAYBOOKS 记录文件
    for fname, ntype in NODE_TYPES.items():
        f = PLAY / fname
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        # 基于行首 id: XXX 抽取记录
        for m in re.finditer(r"^##\s+id:\s*([A-Z]+-[0-9\-A-Z]+).*$", text, flags=re.M):
            rid = m.group(1).strip()
            # 在附近找标题/摘要
            title = rid
            t2 = TITLE_RE.search(text)
            if t2:
                title = f"{rid}"
            add_node(kg, rid, ntype, title)
        # 链接推断关系
        for m in LINK_RE.finditer(text):
            label, link = m.groups()
            # 只处理相对路径 docs/ 开头
            if link.startswith("docs/"):
                add_node(kg, link, "Doc", label)
                # 没有明确来源记录 id 时，用文件名聚合
                add_edge(kg, f"{fname}", "documents", link)

    # 扫描 docs/ 下的脚本/文档链接（启发式）
    for md in DOCS.glob("**/*.md"):
        if "PLAYBOOKS" in md.parts:
            continue
        text = md.read_text(encoding="utf-8", errors="ignore")
        title = TITLE_RE.search(text)
        add_node(
            kg,
            str(md.relative_to(ROOT)).replace("\\", "/"),
            "Doc",
            title.group(1) if title else md.name,
        )
        for m in LINK_RE.finditer(text):
            _, link = m.groups()
            if link.startswith("scripts/"):
                add_node(kg, link, "Script", link)
                add_edge(kg, str(md.relative_to(ROOT)).replace("\\", "/"), "uses", link)

    return kg


def main() -> int:
    kg = infer_nodes_and_edges()
    # 添加统计字段
    meta = {
        "node_count": len(kg.get("nodes", [])),
        "edge_count": len(kg.get("edges", [])),
    }
    kg["meta"] = meta
    new_text = json.dumps(kg, ensure_ascii=False, indent=2)
    old_text = KG.read_text(encoding="utf-8") if KG.exists() else ""
    if new_text != old_text:
        KG.write_text(new_text, encoding="utf-8")
        print(
            f"[KG] 已更新知识图谱：{KG} (nodes={meta['node_count']}, edges={meta['edge_count']})"
        )
    else:
        print(f"[KG] 无变化（nodes={meta['node_count']}, edges={meta['edge_count']})")

    # 同步到索引页的统计行（若存在）
    index_md = PLAY / "索引.md"
    if index_md.exists():
        lines = index_md.read_text(encoding="utf-8").splitlines()
        replaced = False
        for i, line in enumerate(lines[:10]):  # 只在前10行内查找统计行
            if line.strip().startswith("> 图谱统计："):
                lines[i] = (
                    f"> 图谱统计：nodes={meta['node_count']}, edges={meta['edge_count']}（由 kg_update.py 自动维护）"
                )
                replaced = True
                break
        if not replaced:
            lines.insert(
                2,
                f"> 图谱统计：nodes={meta['node_count']}, edges={meta['edge_count']}（由 kg_update.py 自动维护）",
            )
        index_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
