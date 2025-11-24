# -*- coding: utf-8 -*-
"""
生成 docs/配置说明.md 的 CONFIG_AUTO 自动区块（<!-- BEGIN:CONFIG_AUTO --> ... <!-- END:CONFIG_AUTO -->）。
来源：configs/*.yaml + app/core/config/loader_new.py（来源优先级/ENV 覆盖）。

用法：
  python scripts/tools/doc_gen/gen_config_md.py
"""
from __future__ import annotations

from pathlib import Path
import json
import sys
import re
from typing import Any, Dict

try:
    import yaml  # type: ignore
except Exception:
    print("[WARN] PyYAML 未安装，无法生成 CONFIG_AUTO。", file=sys.stderr)
    raise

ROOT = Path(__file__).resolve().parents[3]
DOC = ROOT / "docs/配置说明.md"
CONFIG_DIR = ROOT / "configs"
BEGIN = "<!-- BEGIN:CONFIG_AUTO -->"
END = "<!-- END:CONFIG_AUTO -->"

YAML_FILES = [
    "database.yaml",
    "logging.yaml",
    "system.yaml",
    "ingest.yaml",
    "merge.yaml",
    "error_handling.yaml",
    "device_running.yaml",
]


def _safe_load_yaml(p: Path) -> Dict[str, Any]:
    try:
        if p.exists():
            d = yaml.safe_load(p.read_text(encoding="utf-8"))
            return d or {}
    except Exception:
        pass
    return {}


def _flatten(prefix: str, obj: Any, out: Dict[str, Any]):
    if isinstance(obj, dict):
        for k, v in obj.items():
            _flatten(f"{prefix}.{k}" if prefix else str(k), v, out)
    else:
        out[prefix] = obj


def _env_overrides() -> Dict[str, str]:
    # 与 loader_new.py 对齐的 ENV 白名单
    return {
        "INGEST_WORKERS": "ingest.workers",
        "INGEST_COMMIT_INTERVAL": "ingest.commit_interval",
        "INGEST_P95_WINDOW": "ingest.p95_window",
        "INGEST_ENHANCED_SOURCE_HINT": "ingest.enhanced_source_hint",
        "INGEST_BATCH_ID_MODE": "ingest.batch_id_mode",
    }


def build_block() -> str:
    lines: list[str] = []
    lines.append(BEGIN)
    lines.append("")
    lines.append("## 自动生成：配置快照（来自 configs/*.yaml）")
    lines.append("")

    for fname in YAML_FILES:
        p = CONFIG_DIR / fname
        data = _safe_load_yaml(p)
        header = fname
        lines.append(f"- {header}")
        if not data:
            lines.append("  - <空/不存在>")
            continue
        flat: Dict[str, Any] = {}
        _flatten("", data, flat)
        # 排序：键路径字典序
        for k in sorted(flat.keys()):
            v = flat[k]
            v_json = json.dumps(v, ensure_ascii=False)
            key = k.lstrip(".")
            # 适度截断过长字符串
            if isinstance(v, str) and len(v) > 200:
                v_json = json.dumps(v[:197] + "...", ensure_ascii=False)
            lines.append(f"  - {key}: {v_json}")
        lines.append("")

    # ENV 覆盖白名单一览
    env_map = _env_overrides()
    if env_map:
        lines.append("- ENV 覆盖白名单（高优先级：ENV > YAML > 默认）")
        for env, path in env_map.items():
            lines.append(f"  - {env} -> {path}")
        lines.append("")

    # 来源优先级提示
    lines.append("- 配置来源优先级：CLI > ENV > YAML > 默认（database.yaml 仅 YAML）")
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
        print("[OK] docs/配置说明.md 已更新 CONFIG_AUTO 区块")
    else:
        print("[OK] docs/配置说明.md CONFIG_AUTO 无变化")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

