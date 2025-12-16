from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import sys

# 将项目根目录加入 sys.path，便于作为脚本直接运行
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def main() -> None:
    s = load_settings(Path("configs"))
    results: dict[str, object] = {}
    with get_conn(s) as conn:
        with conn.cursor() as cur:
            # 基础计数
            cur.execute("SELECT COUNT(*) FROM public.staging_raw")
            results["staging_raw_count"] = int(cur.fetchone()[0])
            cur.execute("SELECT COUNT(*) FROM public.staging_rejects")
            results["staging_rejects_count"] = int(cur.fetchone()[0])

            # 事实层全量计数与时间范围
            cur.execute(
                "SELECT COUNT(*), min(ts_bucket), max(ts_bucket) FROM public.fact_measurements"
            )
            r = cur.fetchone()
            results["fact_total"] = int(r[0]) if r and r[0] is not None else 0
            results["fact_min_ts"] = r[1].isoformat() if r and r[1] else None
            results["fact_max_ts"] = r[2].isoformat() if r and r[2] else None

            ws = datetime(2025, 2, 28, 2, 0, 0, tzinfo=timezone.utc)
            we = datetime(2025, 2, 28, 4, 0, 0, tzinfo=timezone.utc)

            cur.execute(
                "SELECT COUNT(*) FROM public.fact_measurements WHERE ts_bucket >= %s AND ts_bucket < %s",
                (ws, we),
            )
            results["fact_measurements_count_window"] = int(cur.fetchone()[0])

            # 末秒 03:59:59 是否存在、是否为 112 行
            ts_last = datetime(2025, 2, 28, 3, 59, 59, tzinfo=timezone.utc)
            cur.execute(
                "SELECT COUNT(*) FROM public.fact_measurements WHERE ts_bucket = %s",
                (ts_last,),
            )
            results["fact_measurements_count_03_59_59"] = int(cur.fetchone()[0])

            # 末秒按设备分布（Top 3 示例）
            cur.execute(
                """
                SELECT device_id, COUNT(*) AS rows
                FROM public.fact_measurements
                WHERE ts_bucket = %s
                GROUP BY device_id
                ORDER BY device_id
                LIMIT 3
                """,
                (ts_last,),
            )
            results["sample_device_rows_at_03_59_59"] = [
                {"device_id": r[0], "rows": int(r[1])} for r in cur.fetchall()
            ]

            # presence 结果表检查
            cur.execute(
                "SELECT to_regclass('public.metrics_presence_per_second_device')"
            )
            tbl = cur.fetchone()[0]
            results["presence_table_exists"] = bool(tbl)
            if tbl:
                cur.execute(
                    "SELECT COUNT(*) FROM public.metrics_presence_per_second_device WHERE ts_second >= %s AND ts_second < %s",
                    (
                        datetime(2025, 2, 28, 0, 0, 0, tzinfo=timezone.utc),
                        datetime(2025, 3, 1, 0, 0, 0, tzinfo=timezone.utc),
                    ),
                )
                results["presence_rows_window"] = int(cur.fetchone()[0])

    # 简单打印
    import json

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
