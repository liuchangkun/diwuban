# -*- coding: utf-8 -*-
"""
将 generated/memory_index.json 摘要写入 docs/PLAYBOOKS/INDEX.md 的 MEMORY_AUTO 区块；
若区块不存在则附加在文末。
"""
from __future__ import annotations
import json, re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
INDEX_JSON = ROOT / "generated" / "memory_index.json"
PB_INDEX = ROOT / "docs" / "PLAYBOOKS" / "INDEX.md"
BEGIN = "<!-- MEMORY_AUTO:BEGIN"
END = "<!-- MEMORY_AUTO:END -->"


def render(md: str) -> str:
    data = json.loads(md)
    lines = [f"生成时间: {datetime.now(timezone.utc).isoformat()}", "", "| 日期 | 类型 | 标题 | 路径 |", "| --- | --- | --- | --- |"]
    for it in sorted(data.get("items", []), key=lambda x: (x.get("date_in_name") or "", x.get("title")) , reverse=True)[:20]:
        lines.append(f"| {it.get('date_in_name') or ''} | {it['type']} | {it['title']} | {it['path']} |")
    return "\n".join(lines)


def upsert_block(text: str, payload: str) -> str:
    block = f"{BEGIN} generated=scripts/dev/compose_memory_snapshot.py at={datetime.now(timezone.utc).isoformat()} -->\n{payload}\n{END}"
    if BEGIN in text and END in text:
        return re.sub(r"<!-- MEMORY_AUTO:BEGIN[\s\S]*?<!-- MEMORY_AUTO:END -->", lambda m: block, text)
    return text.rstrip() + "\n\n## 记忆自动摘要\n\n" + block + "\n"


def main() -> None:
    if not INDEX_JSON.exists():
        print("memory_index.json not found, run update_memory_index.py first")
        return
    payload = render(INDEX_JSON.read_text(encoding="utf-8"))
    old = PB_INDEX.read_text(encoding="utf-8")
    new = upsert_block(old, payload)
    PB_INDEX.write_text(new, encoding="utf-8")
    print("updated MEMORY_AUTO block in", PB_INDEX)


if __name__ == "__main__":
    main()

