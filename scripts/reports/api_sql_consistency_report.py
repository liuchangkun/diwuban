# -*- coding: utf-8 -*-
"""
API↔SQL 一致性测试（分页/聚合对齐版）
- 目标：对 /api/v1/data/measurements 与事实表 SQL 进行严格一致性校验
- 机制：
  1) 选择一个 device_id 与窗口（默认取事实表中间点±1小时，可入参覆盖）
  2) API 分页拉取（limit/offset），收集所有条目，统计条数
  3) SQL 端做“等价聚合”统计：
     - 若 API 返回的是按秒/分钟聚合后的每秒（或每分钟）一条，则在 SQL 中 group by 对齐
     - 若 API 直接返回打包 JSON（按时刻/设备合并），则以“时刻计数”与 SQL 端 distinct(ts_bucket) 对比
- 输出：report.json（包含 device_id、窗口、api_count、sql_count、差异率等）
"""

from __future__ import annotations

import argparse
import json
from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import requests

from app.adapters.db.gateway import get_conn
from app.core.config.loader_new import load_settings

BASE = "http://127.0.0.1:8003"


def _pick_device_and_window(settings) -> Tuple[int, str, str]:
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
                raise SystemExit("no_fact_measurements")
            device_id, mn, mx = row
            mid = mn + (mx - mn) / 2
            start = (mid - timedelta(hours=1)).isoformat()
            end = (mid + timedelta(hours=1)).isoformat()
            return int(device_id), start, end


def _api_fetch_all(
    device_id: int, start: str, end: str, page_limit: int = 1000
) -> Dict:
    items: List[Dict] = []
    offset = 0
    total = None
    while True:
        r = requests.get(
            f"{BASE}/api/v1/data/measurements",
            params={
                "device_id": device_id,
                "start_time": start,
                "end_time": end,
                "limit": page_limit,
                "offset": offset,
            },
            timeout=30,
        )
        r.raise_for_status()
        body = r.json()
        data = body.get("data", [])
        items.extend(data)
        total = body.get("total_count")
        has_more = body.get("has_more")
        if not data or not has_more:
            break
        offset += page_limit
    return {"items": items, "total": total, "pages": (offset // page_limit) + 1}


def _sql_count_distinct_ts(settings, device_id: int, start: str, end: str) -> int:
    # 以“时刻”为单位对齐：事实表中相同 device/ts_bucket 的合并视为一条
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) FROM (
                  SELECT DISTINCT ts_bucket
                  FROM public.fact_measurements
                  WHERE device_id=%s AND ts_bucket >= %s AND ts_bucket <= %s
                ) t
                """,
                (device_id, start, end),
            )
            return int(cur.fetchone()[0])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device_id", type=int, default=None)
    ap.add_argument("--start", type=str, default=None)
    ap.add_argument("--end", type=str, default=None)
    ap.add_argument("--out", type=str, default="reports/api_sql_report.json")
    args = ap.parse_args()

    settings = load_settings(Path("configs"))

    if args.device_id and args.start and args.end:
        device_id, start, end = args.device_id, args.start, args.end
    else:
        device_id, start, end = _pick_device_and_window(settings)

    # 1) API 全量
    api = _api_fetch_all(device_id, start, end, page_limit=1000)
    api_count = len(api["items"])  # 按返回行计
    # 2) SQL 等价时刻数
    sql_count = _sql_count_distinct_ts(settings, device_id, start, end)

    diff = abs(api_count - sql_count)
    ratio = (diff / max(1, sql_count)) if sql_count else 0.0

    report = {
        "device_id": device_id,
        "window": {"start": start, "end": end},
        "api_count": api_count,
        "api_total": api.get("total"),
        "sql_distinct_ts_count": sql_count,
        "diff": diff,
        "diff_ratio": round(ratio, 6),
        "pages": api.get("pages"),
        "sample_head": api["items"][:3],
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
