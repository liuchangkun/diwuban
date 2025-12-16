from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 兼容 Python 3.8+ 的时区处理
try:
    from zoneinfo import ZoneInfo as _ZoneInfo
    ZoneInfo = _ZoneInfo  # 类型别名
    
    def create_aware_datetime(dt_naive: Any, tz: Any) -> Any:
        """zoneinfo 模式下的时区处理"""
        return dt_naive.replace(tzinfo=tz)
except ImportError:
    # Python < 3.9 或缺少 zoneinfo，使用 pytz 作为替代
    try:
        import pytz
        from typing import Any  # type: ignore
        
        class ZoneInfo:
            """pytz 兼容封装"""
            def __init__(self, tz_name: str):
                self._tz = pytz.timezone(tz_name)
                self.key = tz_name
            
            def __call__(self, dt: Any) -> Any:
                if dt.tzinfo is None:
                    return self._tz.localize(dt)
                return dt.astimezone(self._tz)
            
            @property
            def zone(self) -> str:
                return str(self._tz.zone)
                
        # 重写 datetime.replace 的用法
        def create_aware_datetime(dt_naive: Any, tz: Any) -> Any:
            if hasattr(tz, '_tz'):
                return tz._tz.localize(dt_naive)
            else:
                return dt_naive.replace(tzinfo=tz)
                
    except ImportError:
        raise ImportError(
            "Neither zoneinfo (Python 3.9+) nor pytz is available. "
            "Please install pytz: pip install pytz"
        )

import psycopg

# 将仓库根目录加入 sys.path，保证可导入 app 包
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.adapters.db.gateway import make_dsn  # noqa: E402
from app.core.config.loader import load_settings  # noqa: E402


def main() -> None:
    s = load_settings(Path("config"))
    dsn = make_dsn(s)
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT substr("DataTime",1,13) AS hour_str, COUNT(*) AS cnt '
                "FROM public.staging_raw "
                "WHERE \"DataTime\" ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2} ' "
                "GROUP BY 1 ORDER BY 2 DESC LIMIT 1"
            )
            row = cur.fetchone()
            if not row:
                print("NO_DATA")
                return
            hour_str, cnt = row
    # 将 hour_str 解释为 Asia/Shanghai 的本地整点，并转换为 UTC 窗口
    dt_naive = datetime.strptime(hour_str + ":00:00", "%Y-%m-%d %H:%M:%S")
    
    # 兼容两种时区处理方式
    try:
        # 优先尝试 zoneinfo 方式
        asia_shanghai = ZoneInfo("Asia/Shanghai")
        dt_local = dt_naive.replace(tzinfo=asia_shanghai)
    except (AttributeError, TypeError):
        # 使用 pytz 兼容封装
        asia_shanghai = ZoneInfo("Asia/Shanghai")
        dt_local = create_aware_datetime(dt_naive, asia_shanghai)
    dt_utc_start = dt_local.astimezone(timezone.utc)
    dt_utc_end = dt_utc_start + timedelta(hours=1)
    print("HOUR_LOCAL", hour_str, cnt)
    print("WINDOW_UTC_START", dt_utc_start.isoformat().replace("+00:00", "Z"))
    print("WINDOW_UTC_END", dt_utc_end.isoformat().replace("+00:00", "Z"))


if __name__ == "__main__":
    main()
