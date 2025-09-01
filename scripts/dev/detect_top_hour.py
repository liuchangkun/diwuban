from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

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
    dt_local = datetime.strptime(hour_str + ":00:00", "%Y-%m-%d %H:%M:%S").replace(
        tzinfo=ZoneInfo("Asia/Shanghai")
    )
    dt_utc_start = dt_local.astimezone(timezone.utc)
    dt_utc_end = dt_utc_start + timedelta(hours=1)
    print("HOUR_LOCAL", hour_str, cnt)
    print("WINDOW_UTC_START", dt_utc_start.isoformat().replace("+00:00", "Z"))
    print("WINDOW_UTC_END", dt_utc_end.isoformat().replace("+00:00", "Z"))


if __name__ == "__main__":
    main()
