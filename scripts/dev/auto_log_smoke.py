from __future__ import annotations

import os
import time
from pathlib import Path

import psycopg

from app.core.logging.setup import init_logging
from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def main() -> None:
    # 开启应用侧自动日志
    os.environ["APP_DB_AUTO_LOG"] = "true"

    # 初始化日志（写入 logs/app.log）
    init_logging("configs", "Asia/Shanghai")

    settings = load_settings(Path("configs"))

    # 1) 视图：public.station_device_rated_params_view
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT station_id, station_name, device_id, device_name, pump_type
                FROM public.station_device_rated_params_view
                ORDER BY station_id, device_id
                LIMIT 3
                """
            )
            _ = cur.fetchall()

    # 2) 函数：public.metrics_availability_window（先取一个时间窗）
    start_ts = end_ts = None
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT min(ts_bucket), max(ts_bucket) FROM public.fact_measurements")
            row = cur.fetchone()
            start_ts, end_ts = row[0], row[1]

    if start_ts and end_ts:
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    WITH win AS (
                      SELECT * FROM public.metrics_availability_window(%s, %s)
                    )
                    SELECT station_id, device_id, metric_key, status
                    FROM win
                    ORDER BY station_id, device_id, metric_key
                    LIMIT 10
                    """,
                    (start_ts, end_ts),
                )
                _ = cur.fetchall()

    # 3) 触发一条 >200ms 的慢语句（用于 auto_explain 在服务器日志记录计划）
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_sleep(0.3)")
            cur.fetchone()

    print("[DONE] auto_log_smoke completed")


if __name__ == "__main__":
    main()

