from __future__ import annotations

"""
只读校验脚本：
- 1) 时间对齐与取值范围检查（device_running）
- 2) 取最新一条 completion_runs，核对 DB 逐秒判定 vs 事实层逐秒=1 计数是否一致
输出 JSON 便于快速审阅。
"""

import json
from pathlib import Path

from app.adapters.db.gateway import get_conn
from app.core.config.loader_new import load_settings


def main() -> None:
    s = load_settings(Path("configs"))
    out: dict = {}

    with get_conn(s) as conn:
        with conn.cursor() as cur:
            # A. 时间对齐与取值范围
            cur.execute(
                """
                SELECT COUNT(*)
                FROM public.fact_measurements
                WHERE metric_id=(SELECT id FROM public.dim_metric_config WHERE metric_key='device_running')
                  AND ts_bucket <> date_trunc('second', ts_bucket)
                """
            )
            out["off_sec"] = int(cur.fetchone()[0])

            cur.execute(
                """
                SELECT MIN(value), MAX(value)
                FROM public.fact_measurements
                WHERE metric_id=(SELECT id FROM public.dim_metric_config WHERE metric_key='device_running')
                """
            )
            r = cur.fetchone()
            out["value_min"] = int(r[0]) if r and r[0] is not None else None
            out["value_max"] = int(r[1]) if r and r[1] is not None else None

            # B. 最新 run 对比（DB vs 事实层）
            cur.execute(
                """
                SELECT run_id, station_id, device_id, start_ts, end_ts
                FROM public.completion_runs
                ORDER BY run_id DESC LIMIT 1
                """
            )
            row = cur.fetchone()
            if not row:
                out["latest_run"] = None
            else:
                run_id, st_id, dev_id, st, et = (
                    int(row[0]),
                    int(row[1]),
                    int(row[2]),
                    row[3],
                    row[4],
                )
                cur.execute(
                    "SELECT COUNT(*) FROM public.fn_running_state_1s(%s,%s,%s,%s) WHERE is_running",
                    (st_id, dev_id, st, et),
                )
                db_running = int(cur.fetchone()[0])
                cur.execute(
                    """
                    SELECT COUNT(*) FROM public.fact_measurements
                    WHERE station_id=%s AND device_id=%s
                      AND metric_id=(SELECT id FROM public.dim_metric_config WHERE metric_key='device_running')
                      AND ts_bucket >= %s AND ts_bucket < %s AND value=1
                    """,
                    (st_id, dev_id, st, et),
                )
                fact_running = int(cur.fetchone()[0])
                out["latest_run"] = {
                    "run_id": run_id,
                    "station_id": st_id,
                    "device_id": dev_id,
                    "window": [st.isoformat(), et.isoformat()],
                    "db_running_secs": db_running,
                    "fact_running_secs": fact_running,
                    "match": (db_running == fact_running),
                }

    print(json.dumps(out, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
