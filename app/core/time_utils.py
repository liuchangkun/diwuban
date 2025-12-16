from __future__ import annotations

"""
时间工具（app.core.time_utils）
- utc_iso_week_bounds：给定 UTC 时间，返回该 ISO 周 [周一00:00, 下周一00:00)
- windows_by_size：按天数切片窗口
- format_local_time：统一的时间格式化函数
- format_for_display：显示格式化
- format_for_log：日志格式化
- format_for_iso：ISO格式化
"""

from datetime import datetime, timedelta, timezone
from typing import Iterator, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.config.loader import Settings

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



def format_local_time(
    dt: datetime,
    settings: "Settings",
    format_type: str = "display",
    include_microseconds: bool = False
) -> str:
    """
    统一的时间格式化函数

    Args:
        dt: 要格式化的时间
        settings: 配置对象
        format_type: 格式类型 (display | iso | log)
        include_microseconds: 是否包含微秒

    Returns:
        格式化后的时间字符串

    格式说明:
        - display: YYYY-MM-DD HH:MM:SS+08
        - iso: YYYY-MM-DDTHH:MM:SS+08:00
        - log: YYYY-MM-DD HH:MM:SS.ffffff+08
    """
    try:
        # 获取时区配置
        try:
            tz_name = str(settings.system.timezone.default)
        except Exception:
            tz_name = "Asia/Shanghai"

        # 创建时区对象
        try:
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(tz_name)
        except Exception:
            # 回退到固定偏移
            tz = timezone(timedelta(hours=8))

        # 转换到本地时区
        dt_local = dt.astimezone(tz)

        # 计算时区偏移
        offset = dt_local.utcoffset() or timedelta(0)
        hours = int(offset.total_seconds() // 3600)
        minutes = int((offset.total_seconds() % 3600) // 60)
        sign = "+" if hours >= 0 else "-"

        # 根据格式类型生成字符串
        if format_type == "display":
            if include_microseconds:
                time_str = dt_local.strftime("%Y-%m-%d %H:%M:%S.%f")
            else:
                time_str = dt_local.strftime("%Y-%m-%d %H:%M:%S")
            return f"{time_str}{sign}{abs(hours):02d}"

        elif format_type == "iso":
            if include_microseconds:
                time_str = dt_local.strftime("%Y-%m-%dT%H:%M:%S.%f")
            else:
                time_str = dt_local.strftime("%Y-%m-%dT%H:%M:%S")
            return f"{time_str}{sign}{abs(hours):02d}:{abs(minutes):02d}"

        elif format_type == "log":
            time_str = dt_local.strftime("%Y-%m-%d %H:%M:%S.%f")
            return f"{time_str}{sign}{abs(hours):02d}"

        else:
            raise ValueError(f"Unknown format_type: {format_type}")

    except Exception:
        # 回退到简单格式
        return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_for_display(dt: datetime, settings: "Settings") -> str:
    """便捷函数：显示格式 YYYY-MM-DD HH:MM:SS+08"""
    return format_local_time(dt, settings, "display")


def format_for_log(dt: datetime, settings: "Settings") -> str:
    """便捷函数：日志格式 YYYY-MM-DD HH:MM:SS.ffffff+08"""
    return format_local_time(dt, settings, "log", include_microseconds=True)


def format_for_iso(dt: datetime, settings: "Settings") -> str:
    """便捷函数：ISO格式 YYYY-MM-DDTHH:MM:SS+08:00"""
    return format_local_time(dt, settings, "iso")
