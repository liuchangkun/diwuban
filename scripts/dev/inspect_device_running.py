from __future__ import annotations
"""
只读检查脚本：核对 device_running 作业运行前后关键数据点。
- 阈值设备数量（device_running_thresholds）
- 候选设备数（排除 main_pipeline 且有阈值）
- 追踪层最近 run/step/audit 抽样
- 事实层 device_running 写入抽样
"""

from pathlib import Path
from datetime import datetime, timedelta, timezone
import json

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def main() -> None:
    settings = load_settings(Path("configs"))
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=7)
    summary: dict = {}

    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # 阈值设备数量
            cur.execute("SELECT COUNT(*) FROM public.device_running_thresholds")
            summary["thresholds_count"] = int(cur.fetchone()[0])

            # 候选设备数（排除 main_pipeline）
            cur.execute(
                """
                SELECT COUNT(*)
                FROM public.dim_devices d
                JOIN public.device_running_thresholds t ON t.device_id = d.id
                WHERE COALESCE(NULLIF(d.type,''),'') <> 'main_pipeline'
                """
            )
            summary["candidate_devices"] = int(cur.fetchone()[0])

            # device_running metric_id
            cur.execute(
                "SELECT id FROM public.dim_metric_config WHERE metric_key='device_running'"
            )
            row = cur.fetchone()
            metric_id = int(row[0]) if row else None
            summary["metric_id_device_running"] = metric_id

            # 最近一条 run
            cur.execute(
                """
                SELECT run_id, device_id, start_ts, end_ts, rows_read, steps_total
                FROM public.completion_runs
                ORDER BY run_id DESC
                LIMIT 1
                """
            )
            r = cur.fetchone()
            if r:
                summary["last_run"] = {
                    "run_id": int(r[0]),
                    "device_id": int(r[1]),
                    "start_ts": r[2].isoformat() if r[2] else None,
                    "end_ts": r[3].isoformat() if r[3] else None,
                    "rows_read": int(r[4] or 0),
                    "steps_total": int(r[5] or 0),
                }

            # 最近 steps 抽样
            cur.execute(
                """
                SELECT run_id, device_id, metric_id, gap_start_ts, gap_end_ts, rows_considered
                FROM public.completion_steps
                ORDER BY id DESC
                LIMIT 5
                """
            )
            steps = []
            for s in cur.fetchall() or []:
                steps.append(
                    {
                        "run_id": int(s[0]),
                        "device_id": int(s[1]),
                        "metric_id": int(s[2]),
                        "gap_start_ts": s[3].isoformat() if s[3] else None,
                        "gap_end_ts": s[4].isoformat() if s[4] else None,
                        "rows_considered": int(s[5] or 0),
                    }
                )
            summary["last_steps"] = steps

            # 事实层抽样（近7天）
            if metric_id is not None:
                cur.execute(
                    """
                    SELECT device_id, metric_id, ts_bucket, value, source_hint
                    FROM public.fact_measurements
                    WHERE metric_id = %s AND ts_bucket >= %s
                    ORDER BY ts_bucket DESC
                    LIMIT 10
                    """,
                    (metric_id, since),
                )
                facts = []
                for f in cur.fetchall() or []:
                    facts.append(
                        {
                            "device_id": int(f[0]),
                            "metric_id": int(f[1]),
                            "ts_bucket": f[2].isoformat() if f[2] else None,
                            "value": int(f[3]) if f[3] is not None else None,
                            "source_hint": f[4],
                        }
                    )
                summary["facts_sample"] = facts

    print(json.dumps(summary, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()

