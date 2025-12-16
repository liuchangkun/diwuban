from __future__ import annotations

from pathlib import Path
import json
from typing import List, Tuple

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn

TARGET_KEYS = ["pump_active_power", "active_power", "power"]
OVERSHOOT_ABS = 0.5


def parse_json_loose(text: str | None) -> dict:
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        # 允许 remark 为非 JSON（如 'seed:auto_baseline'），则以键值形式保留到 other 字段
        return {"_raw": text}


def main() -> None:
    settings = load_settings(Path("configs"))
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, metric_key FROM public.dim_metric_config WHERE metric_key = ANY(%s)",
                (TARGET_KEYS,),
            )
            metrics: List[Tuple[int, str]] = [(int(r[0]), str(r[1])) for r in cur.fetchall()]

            updated: List[str] = []
            skipped: List[str] = []

            for mid, mkey in metrics:
                cur.execute(
                    "SELECT rule_id, remark FROM public.metric_quality_rules WHERE metric_id=%s ORDER BY rule_id LIMIT 1",
                    (mid,),
                )
                r = cur.fetchone()
                if not r:
                    # 无规则行时不在此脚本插入（保持与 set_overshoot_abs 的职责分离）
                    skipped.append(mkey)
                    continue
                rule_id, remark = int(r[0]), (r[1] or "")
                obj = parse_json_loose(remark)
                if "overshoot_abs" in obj:
                    skipped.append(mkey)
                    continue
                obj["overshoot_abs"] = OVERSHOOT_ABS
                new_remark = json.dumps(obj, ensure_ascii=False)
                cur.execute(
                    "UPDATE public.metric_quality_rules SET remark=%s, updated_by=%s, updated_at=now() WHERE rule_id=%s",
                    (new_remark, "augment", rule_id),
                )
                updated.append(mkey)
            conn.commit()
            print({"updated": updated, "skipped": skipped, "overshoot_abs": OVERSHOOT_ABS})


if __name__ == "__main__":
    main()

