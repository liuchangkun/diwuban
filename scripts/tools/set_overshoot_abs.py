from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn

METRIC_KEYS: List[str] = [
    "pump_flow_rate",
    "main_pipeline_flow_rate",
    "pump_active_power",
    "active_power",
    "power",
]

DEFAULT_OVERSHOOT_ABS = 0.5


def main() -> None:
    settings = load_settings(Path("configs"))
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, metric_key
                FROM public.dim_metric_config
                WHERE metric_key = ANY(%s)
                """,
                (METRIC_KEYS,),
            )
            rows: List[Tuple[int, str]] = [(int(r[0]), str(r[1])) for r in cur.fetchall()]

            inserted: List[str] = []
            skipped: List[str] = []

            for mid, mkey in rows:
                # 是否已存在该 metric 的规则行
                cur.execute(
                    "SELECT remark FROM public.metric_quality_rules WHERE metric_id=%s LIMIT 1",
                    (mid,),
                )
                row = cur.fetchone()
                if row is None:
                    # 插入一条带 overshoot_abs 的 remark
                    cur.execute(
                        """
                        INSERT INTO public.metric_quality_rules(metric_id, remark, updated_by)
                        VALUES (%s, %s, %s)
                        """,
                        (mid, f'{"{"}"overshoot_abs": {DEFAULT_OVERSHOOT_ABS}{"}"}', "augment"),
                    )
                    inserted.append(mkey)
                else:
                    remark = row[0] or ""
                    if "overshoot_abs" in remark:
                        skipped.append(mkey)
                    else:
                        # 保守：不覆盖已有 remark（避免丢失其他参数），仅记录跳过
                        skipped.append(mkey)
            conn.commit()
            print({
                "metrics_found": [m for _, m in rows],
                "inserted_for": inserted,
                "skipped": skipped,
                "default_overshoot_abs": DEFAULT_OVERSHOOT_ABS,
            })


if __name__ == "__main__":
    main()

