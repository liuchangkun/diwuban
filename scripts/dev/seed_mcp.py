from __future__ import annotations

import csv
from pathlib import Path
import sys

# 确保可导入 app 包
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn

CSV_PATH = Path("docs/templates/metric_capability_policy_seed.csv")
DDL_PATH = Path("scripts/sql/m2/002_metric_capability_policy.sql")


def main() -> int:
    settings = load_settings(Path("configs"))
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # 确保表存在
            ddl = DDL_PATH.read_text(encoding="utf-8")
            cur.execute(ddl)
            # 读取 CSV 并 UPSERT
            rows: list[dict[str, str]] = []
            with CSV_PATH.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    rows.append(r)
            for r in rows:
                cur.execute(
                    (
                        """
                        INSERT INTO public.metric_capability_policy(metric_key, acquisition_status, compute_flag, updated_by)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (metric_key) DO UPDATE
                          SET acquisition_status = EXCLUDED.acquisition_status,
                              compute_flag       = EXCLUDED.compute_flag,
                              updated_at         = now(),
                              updated_by         = EXCLUDED.updated_by
                        """
                    ),
                    (
                        r.get("metric_key"),
                        r.get("acquisition_status"),
                        r.get("compute_flag"),
                        r.get("updated_by") or "sys",
                    ),
                )
            # 提交事务，确保 UPSERT 生效
            conn.commit()
    print(f"[SEED] Upserted {len(rows)} rows into metric_capability_policy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
