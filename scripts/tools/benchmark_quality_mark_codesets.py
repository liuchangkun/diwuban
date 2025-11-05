from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime, timedelta, timezone
import time
import json

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def pick_device_and_window(cur) -> Tuple[int, datetime, datetime]:
    # 选取最近1小时内数据最多的设备与窗口（10分钟）
    cur.execute(
        """
        WITH recent AS (
          SELECT device_id, MAX(ts_bucket) AS max_ts
          FROM public.fact_measurements
          GROUP BY device_id
        )
        SELECT r.device_id, r.max_ts
        FROM recent r
        ORDER BY r.max_ts DESC NULLS LAST
        LIMIT 1
        """
    )
    row = cur.fetchone()
    if not row or not row[0] or not row[1]:
        raise RuntimeError("无法选取设备与窗口（fact_measurements 为空）")
    device_id = int(row[0])
    end = row[1].replace(tzinfo=timezone.utc) + timedelta(seconds=1)
    start = end - timedelta(minutes=10)
    return device_id, start, end


def reset(cur, start: datetime, end: datetime, device_id: int) -> None:
    cur.execute(
        "CALL public.sp_reset_quality_window(%s,%s,%s,%s)", (start, end, None, device_id)
    )


def run_mark(cur, start: datetime, end: datetime, device_id: int, codes: List[int] | None) -> float:
    t0 = time.perf_counter()
    cur.execute(
        "CALL public.sp_mark_quality_window(%s,%s,%s,%s,%s)",
        (start, end, None, device_id, codes),
    )
    return (time.perf_counter() - t0) * 1000.0


def count_codes(cur, start: datetime, end: datetime, device_id: int) -> Dict[int, int]:
    cur.execute(
        """
        SELECT COALESCE(quality_status,0) AS code, COUNT(*)
        FROM public.fact_measurements
        WHERE ts_bucket>=%s AND ts_bucket<%s AND device_id=%s
        GROUP BY 1 ORDER BY 2 DESC
        """,
        (start, end, device_id),
    )
    return {int(c): int(n) for c, n in cur.fetchall()}


def main() -> None:
    settings = load_settings(Path("configs"))
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            device_id, start, end = pick_device_and_window(cur)

    scenarios: Dict[str, List[int] | None] = {
        "only_101": [101],
        "only_111_112": [111, 112],
        "all_enabled": None,  # None 表示全部执行（p_codes=NULL）
    }

    results = {
        "device_id": None,
        "window": None,
        "scenarios": {},
    }

    results["device_id"] = device_id
    results["window"] = {"start": start.isoformat(), "end": end.isoformat()}

    for name, codes in scenarios.items():
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                reset(cur, start, end, device_id)
                conn.commit()
                elapsed_ms = run_mark(cur, start, end, device_id, codes)
                conn.commit()
                counts = count_codes(cur, start, end, device_id)
                results["scenarios"][name] = {
                    "codes": codes,
                    "elapsed_ms": round(elapsed_ms, 2),
                    "counts": counts,
                }

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

