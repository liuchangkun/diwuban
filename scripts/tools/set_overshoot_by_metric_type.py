from __future__ import annotations

from pathlib import Path
import json
from typing import Iterable

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn

# 定义不同 metric_key 的 overshoot_abs 阈值
FLOW_KEYS = [
    "pump_flow_rate",
    "main_pipeline_flow_rate",
]
POWER_KEYS = [
    "pump_active_power",
    "active_power",
    "power",
]
FLOW_OVERSHOOT = 0.3
POWER_OVERSHOOT = 0.5


def upsert_remark(conn, metric_keys: Iterable[str], overshoot: float) -> None:
    with conn.cursor() as cur:
        for key in metric_keys:
            cur.execute(
                "SELECT id FROM public.dim_metric_config WHERE metric_key=%s",
                (key,),
            )
            r = cur.fetchone()
            if not r:
                continue
            metric_id = int(r[0])
            # 读取现有 remark（设备、站点优先级保留），仅对最优先层级做更新
            cur.execute(
                """
                SELECT rule_id, remark
                FROM public.metric_quality_rules
                WHERE metric_id=%s
                ORDER BY (device_id IS NOT NULL) DESC, (station_id IS NOT NULL) DESC, rule_id
                LIMIT 1
                """,
                (metric_id,),
            )
            row = cur.fetchone()
            if row:
                rule_id, remark = int(row[0]), (row[1] or "")
                try:
                    obj = json.loads(remark) if remark else {}
                except Exception:
                    obj = {"_raw": remark}
                obj["overshoot_abs"] = overshoot
                new_remark = json.dumps(obj, ensure_ascii=False)
                cur.execute(
                    "UPDATE public.metric_quality_rules SET remark=%s, updated_by=%s, updated_at=now() WHERE rule_id=%s",
                    (new_remark, "augment", rule_id),
                )
            else:
                # 若无规则行则插入一条全局规则
                cur.execute(
                    "INSERT INTO public.metric_quality_rules(metric_id, remark, updated_by) VALUES (%s, %s, %s)",
                    (metric_id, json.dumps({"overshoot_abs": overshoot}, ensure_ascii=False), "augment"),
                )
    conn.commit()


def main() -> None:
    settings = load_settings(Path("configs"))
    with get_conn(settings) as conn:
        upsert_remark(conn, FLOW_KEYS, FLOW_OVERSHOOT)
        upsert_remark(conn, POWER_KEYS, POWER_OVERSHOOT)
        print({
            "flow_keys": FLOW_KEYS, "power_keys": POWER_KEYS,
            "flow_overshoot": FLOW_OVERSHOOT, "power_overshoot": POWER_OVERSHOOT
        })


if __name__ == "__main__":
    main()

