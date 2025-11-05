# -*- coding: utf-8 -*-
"""
从 docs/ADR 与 docs/PLAYBOOKS 解析记忆索引，输出 generated/memory_index.json，
并为后续自动归档/摘要提供数据源。
"""
from __future__ import annotations
import json, re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
ADR_DIR = ROOT / "docs" / "ADR"
PB_DIR = ROOT / "docs" / "PLAYBOOKS"
OUT = ROOT / "generated" / "memory_index.json"

H1 = re.compile(r"^# +(.+)")
DATE = re.compile(r"(20\d{2}-\d{2}-\d{2})")


def _scan_dir(d: Path, typ: str) -> list[dict]:
    items = []
    for p in sorted(d.glob("**/*.md")):
        title = None
        try:
            for line in p.read_text(encoding="utf-8").splitlines():
                m = H1.match(line)
                if m:
                    title = m.group(1).strip()
                    break
        except Exception:
            title = p.stem
        dt = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat()
        date_in_name = DATE.search(p.name)
        items.append({
            "id": f"{typ}:{p.stem}", "type": typ, "title": title or p.stem,
            "path": str(p.relative_to(ROOT)), "last_updated": dt,
            "date_in_name": date_in_name.group(1) if date_in_name else None,
            "tags": [], "status": "active", "superseded_by": None, "references": 0,
        })
    return items


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    data = []
    if ADR_DIR.exists():
        data += _scan_dir(ADR_DIR, "ADR")
    if PB_DIR.exists():
        data += _scan_dir(PB_DIR, "PLAYBOOK")
    OUT.write_text(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(),
                               "items": data}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"written: {OUT}")


if __name__ == "__main__":
    main()

