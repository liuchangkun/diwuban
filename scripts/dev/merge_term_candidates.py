# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from pathlib import Path
import difflib

ROOT = Path(__file__).resolve().parents[2]
TERMS = ROOT / "docs" / "术语词典.json"
CAND_JSON = ROOT / "docs" / "_自动" / "术语词典候选.json"
OUT_PREMERGE = ROOT / "docs" / "_自动" / "术语词典_预合并.json"
OUT_DIFF = ROOT / "docs" / "_自动" / "术语词典_预合并.diff.md"


def _load_json(p: Path):
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _rule_applies(rule: dict, target: str) -> bool:
    eq = rule.get("equals")
    if isinstance(eq, str) and eq and (eq == target):
        return True
    pre = rule.get("prefix")
    if isinstance(pre, str) and pre and target.startswith(pre):
        return True
    cont = rule.get("contains")
    if isinstance(cont, str) and cont and (cont in target):
        return True
    rx = rule.get("regex")
    if isinstance(rx, str) and rx:
        try:
            import re
            if re.search(rx, target):
                return True
        except Exception:
            pass
    return False


def main():
    terms = _load_json(TERMS) or {}
    cands = _load_json(CAND_JSON) or {}

    # Clone original as base（不改变原有结构）
    pre = json.loads(json.dumps(terms, ensure_ascii=False))

    pre["_候选合并提示"] = "候选仅供审阅；确认后再合并进 tables/apis 等正式段落。"

    # APIs candidates（使用 equals；method 可选）
    api_rules = pre.get("apis") or []
    api_exists = api_rules if isinstance(api_rules, list) else []
    api_cands = []
    for obj in cands.get("apis") or []:
        path = obj.get("key") if isinstance(obj, dict) else None
        if not isinstance(path, str) or not path:
            continue
        covered = any(_rule_applies(r, path) for r in api_exists if isinstance(r, dict))
        if not covered:
            api_cands.append({"equals": path, "summary": ""})
    if api_cands:
        pre["apis_candidates"] = api_cands

    # Tables candidates（schema.table 全名）
    tbl_rules = pre.get("tables") or []
    tbl_exists = tbl_rules if isinstance(tbl_rules, list) else []
    tbl_cands = []
    for obj in cands.get("tables") or []:
        key = obj.get("key") if isinstance(obj, dict) else None
        if not isinstance(key, str) or not key:
            continue
        covered = any(_rule_applies(r, key) for r in tbl_exists if isinstance(r, dict))
        if not covered:
            tbl_cands.append({"equals": key, "summary": ""})
    if tbl_cands:
        pre["tables_candidates"] = tbl_cands

    # Services/Models 作为候选清单输出
    svc_cands = []
    for obj in cands.get("services") or []:
        k = obj.get("key") if isinstance(obj, dict) else None
        if isinstance(k, str) and k:
            svc_cands.append({"key": k, "desc": obj.get("desc", ""), "alias": obj.get("alias", [])})
    if svc_cands:
        pre["services_candidates"] = svc_cands

    mdl_cands = []
    for obj in cands.get("models") or []:
        k = obj.get("key") if isinstance(obj, dict) else None
        if isinstance(k, str) and k:
            mdl_cands.append({"key": k, "desc": obj.get("desc", ""), "alias": obj.get("alias", [])})
    if mdl_cands:
        pre["models_candidates"] = mdl_cands

    # Write pre-merge JSON
    OUT_PREMERGE.parent.mkdir(parents=True, exist_ok=True)
    OUT_PREMERGE.write_text(json.dumps(pre, ensure_ascii=False, indent=2), encoding="utf-8")

    # Diff (unified)
    old = json.dumps(terms, ensure_ascii=False, indent=2)
    new = json.dumps(pre, ensure_ascii=False, indent=2)
    diff = "\n".join(difflib.unified_diff(old.splitlines(), new.splitlines(), fromfile="docs/术语词典.json", tofile="docs/_自动/术语词典_预合并.json", lineterm=""))
    OUT_DIFF.write_text("# 术语词典预合并 diff\n\n```diff\n" + diff + "\n```\n", encoding="utf-8")

    print("[OK] 术语词典预合并产物已生成:")
    print(" -", OUT_PREMERGE)
    print(" -", OUT_DIFF)

if __name__ == "__main__":
    main()

