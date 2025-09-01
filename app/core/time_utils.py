from __future__ import annotations

"""
时间工具（app.core.time_utils）
- utc_iso_week_bounds：给定 UTC 时间，返回该 ISO 周 [周一00:00, 下周一00:00)
- windows_by_size：按天数切片窗口
"""

from datetime import datetime, timedelta, timezone
from typing import Iterator, Tuple

UTC = timezone.utc


def utc_iso_week_bounds(dt: datetime) -> Tuple[datetime, datetime]:
    """给定 UTC 时间，返回该 ISO 周的 [周一00:00, 下周一00:00) 边界（UTC）。"""
    dt_utc = dt.astimezone(UTC)
    iso_weekday = dt_utc.isoweekday()  # 1..7
    monday = (dt_utc - timedelta(days=iso_weekday - 1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    next_monday = monday + timedelta(days=7)
    return monday, next_monday


def windows_by_size(
    start: datetime, end: datetime, size_days: int = 7
) -> Iterator[Tuple[datetime, datetime]]:
    cur = start
    delta = timedelta(days=size_days)
    while cur < end:
        nxt = min(cur + delta, end)
        yield cur, nxt
        cur = nxt
