from __future__ import annotations

from pathlib import Path
from datetime import timedelta, timezone
from typing import List, Tuple, Dict
from datetime import datetime as dt

import json
from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def get_recent_window(cur) -> Tuple[dt, dt]:
    cur.execute("SELECT MAX(ts_bucket) FROM public.fact_measurements")
    row = cur.fetchone()
    if not row or not row[0]:
        raise RuntimeError("fact_measurements 无数据，无法推导测试窗口")
    end = row[0].replace(tzinfo=timezone.utc) + timedelta(seconds=1)
    start = end - timedelta(minutes=2)
    return start, end


essential_codes = [101, 102, 111, 112, 121, 131, 132]


def run_mark(cur, start: dt, end: dt, codes: List[int] | None) -> None:
    cur.execute(
        "CALL public.sp_mark_quality_window(%s,%s,%s,%s,%s)",
        (start, end, None, None, codes),
    )


def reset(cur, start: dt, end: dt) -> None:
    cur.execute(
        "CALL public.sp_reset_quality_window(%s,%s,%s,%s)", (start, end, None, None)
    )


def count_codes(cur, start: dt, end: dt) -> Dict[int, int]:
    cur.execute(
        "SELECT COALESCE(quality_status,0) AS code, COUNT(*) FROM public.fact_measurements "
        "WHERE ts_bucket>=%s AND ts_bucket<%s GROUP BY 1 ORDER BY 2 DESC",
        (start, end),
    )
    return {int(c): int(n) for c, n in cur.fetchall()}


def main() -> None:
    settings = load_settings(Path("configs"))
    # 先取窗口
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            start, end = get_recent_window(cur)

    # 1) 清窗 + 子集仅101（新会话）
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            reset(cur, start, end)
            conn.commit()
            run_mark(cur, start, end, [101])
            conn.commit()
            counts_101 = count_codes(cur, start, end)

    # 2) 清窗 + 按启用列表执行（新会话，避免 fwin 冲突）
    enabled = essential_codes
    try:
        import yaml

        merge_yml = Path("configs/merge.yaml")
        if merge_yml.exists():
            data = yaml.safe_load(merge_yml.read_text(encoding="utf-8")) or {}
            ra = (data or {}).get("run_all", {}) or {}
            codes = ra.get("quality_mark_codes_enabled")
            if isinstance(codes, list) and all(isinstance(x, int) for x in codes):
                enabled = codes
    except Exception:
        pass

    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            reset(cur, start, end)
            conn.commit()
            run_mark(cur, start, end, enabled)
            conn.commit()
            counts_enabled = count_codes(cur, start, end)

    # 输出
    print(
        json.dumps(
            {
                "window": {"start": start.isoformat(), "end": end.isoformat()},
                "only_101_counts": counts_101,
                "enabled_list": enabled,
                "enabled_counts": counts_enabled,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
