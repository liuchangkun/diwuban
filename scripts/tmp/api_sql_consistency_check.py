# -*- coding: utf-8 -*-
"""
API 与 SQL 一致性对比脚本（按设备与时间窗计数对比）
- 选取 fact_measurements 中一个 device_id
- 取其时间范围中间点 ±1 小时作为窗口
- 调用 /api/v1/data/measurements
- SQL 直接计数对比
"""
from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import requests

from app.adapters.db.gateway import get_conn
from app.core.config.loader_new import load_settings

BASE = "http://127.0.0.1:8003"


def main() -> None:
    settings = load_settings(Path("configs"))
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT device_id, MIN(ts_bucket) AS mn, MAX(ts_bucket) AS mx
                FROM public.fact_measurements
                GROUP BY device_id
                ORDER BY device_id
                LIMIT 1
                """
            )
            row = cur.fetchone()
            if not row:
                print(json.dumps({"error": "no_fact_measurements"}))
                return
            device_id, mn, mx = row
            mid = mn + (mx - mn) / 2
            start = (mid - timedelta(hours=1)).isoformat()
            end = (mid + timedelta(hours=1)).isoformat()
            # 若接口支持分页（limit/offset/has_more），可在此循环拉取全量后统计；此处先保留一次 1000 条的默认采样

            # API 调用
            r = requests.get(
                f"{BASE}/api/v1/data/measurements",
                params={
                    "device_id": device_id,
                    "start_time": start,
                    "end_time": end,
                },
                timeout=30,
            )
            api_status = r.status_code
            api_count = None
            try:
                body = r.json()
                api_count = len(body.get("data", []))
            except Exception:
                body = {"parse_error": True, "text": r.text[:300]}

            # SQL 计数
            cur.execute(
                """
                SELECT COUNT(*)
                FROM public.fact_measurements
                WHERE device_id = %s AND ts_bucket >= %s AND ts_bucket <= %s
                """,
                (device_id, start, end),
            )
            (sql_count,) = cur.fetchone()

            print(
                json.dumps(
                    {
                        "device_id": device_id,
                        "window": {"start": start, "end": end},
                        "api_status": api_status,
                        "api_count": api_count,
                        "sql_count": sql_count,
                        "api_head": (
                            body.get("data", [])[:3] if isinstance(body, dict) else None
                        ),
                    },
                    ensure_ascii=False,
                )
            )


if __name__ == "__main__":
    main()
