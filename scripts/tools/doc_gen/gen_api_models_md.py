# -*- coding: utf-8 -*-
"""
从 app/schemas 与 app/models 提取响应与摘要模型字段，注入 docs/应用接口说明.md 的 MODELS_AUTO 区块。
区块标记：<!-- BEGIN:MODELS_AUTO --> ... <!-- END:MODELS_AUTO -->

用法：
  python scripts/tools/doc_gen/gen_api_models_md.py
"""
from __future__ import annotations

from pathlib import Path
import sys
import inspect
import importlib
from typing import Any, List, Tuple

ROOT = Path(__file__).resolve().parents[3]
DOC = ROOT / "docs/应用接口说明.md"
BEGIN = "<!-- BEGIN:MODELS_AUTO -->"
END = "<!-- END:MODELS_AUTO -->"

# 需要提取的模块
MODULES = [
    ("app.schemas.data", ["TimeSeriesResponse"]),
    ("app.models.device", ["DeviceSummary", "DeviceResponse"]),
    ("app.models.station", ["StationSummary", "StationResponse"]),
    ("app.models.metric", ["MetricInfo"]),
]


def _iter_fields(model: Any) -> List[Tuple[str, str, str]]:
    # 尝试兼容 Pydantic v1/v2
    fields = []
    try:
        # pydantic v2
        for name, f in model.model_fields.items():  # type: ignore[attr-defined]
            typ = str(f.annotation)
            desc = (f.description or "").strip() if hasattr(f, "description") else ""
            fields.append((name, typ, desc))
        return fields
    except Exception:
        pass
    try:
        # pydantic v1
        for name, f in model.__fields__.items():  # type: ignore[attr-defined]
            typ = str(f.type_)
            desc = (getattr(f.field_info, "description", "") or "").strip()
            fields.append((name, typ, desc))
        return fields
    except Exception:
        return []


def build_block() -> str:
    lines: list[str] = []
    lines.append(BEGIN)
    lines.append("")
    lines.append("## 自动生成：主要响应/摘要模型字段一览（来源：app.schemas/app.models）")
    lines.append("")

    for mod_name, want in MODULES:
        try:
            if str(ROOT) not in sys.path:
                sys.path.insert(0, str(ROOT))
            mod = importlib.import_module(mod_name)
        except Exception as e:
            lines.append(f"- {mod_name}: <导入失败> {e}")
            lines.append("")
            continue
        exported = {k: getattr(mod, k) for k in want if hasattr(mod, k)}
        lines.append(f"- 模块：{mod_name}")
        for cls_name, cls in exported.items():
            lines.append(f"  - 模型：{cls_name}")
            flds = _iter_fields(cls)
            if not flds:
                lines.append("    - <无字段或解析失败>")
                continue
            for name, typ, desc in flds:
                lines.append(f"    - {name}: {typ} — {desc}")
        lines.append("")

    lines.append(END)
    lines.append("")
    return "\n".join(lines)


def replace_block(doc_text: str, new_block: str) -> str:
    if BEGIN in doc_text and END in doc_text:
        s = doc_text.index(BEGIN)
        e = doc_text.index(END) + len(END)
        return doc_text[:s] + new_block + doc_text[e:]
    return doc_text + "\n\n" + new_block + "\n"


def main() -> int:
    block = build_block()
    text = DOC.read_text(encoding="utf-8")
    new_text = replace_block(text, block)
    if new_text != text:
        DOC.write_text(new_text, encoding="utf-8")
        print("[OK] docs/应用接口说明.md 已更新 MODELS_AUTO 区块")
    else:
        print("[OK] docs/应用接口说明.md MODELS_AUTO 无变化")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

