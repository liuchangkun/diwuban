from __future__ import annotations

from pathlib import Path
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def main() -> int:
    s = load_settings(Path("configs"))
    with get_conn(s) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*), min(ts_bucket), max(ts_bucket) FROM public.fact_measurements"
            )
            total, tmin, tmax = cur.fetchone()
            print("fact_measurements total,min,max:", total, tmin, tmax)
            # UTC 窗口（原日志标注的 02:00~04:00Z）
            ws = datetime(2025, 2, 28, 2, 0, 0, tzinfo=timezone.utc)
            we = datetime(2025, 2, 28, 4, 0, 0, tzinfo=timezone.utc)
            cur.execute(
                "SELECT COUNT(*) FROM public.fact_measurements WHERE ts_bucket >= %s AND ts_bucket < %s",
                (ws, we),
            )
            print("UTC window 02:00~04:00 rows:", cur.fetchone()[0])
            cur.execute(
                "SELECT COUNT(*) FROM public.fact_measurements WHERE ts_bucket=%s",
                (datetime(2025, 2, 28, 3, 59, 59, tzinfo=timezone.utc),),
            )
            print("UTC 03:59:59 rows:", cur.fetchone()[0])
            # 本地(+08)窗口：02:00~04:00+08 等价于 UTC 2025-02-27 18:00~20:00Z
            ws_utc = datetime(2025, 2, 27, 18, 0, 0, tzinfo=timezone.utc)
            we_utc = datetime(2025, 2, 27, 20, 0, 0, tzinfo=timezone.utc)
            cur.execute(
                "SELECT COUNT(*) FROM public.fact_measurements WHERE ts_bucket >= %s AND ts_bucket < %s",
                (ws_utc, we_utc),
            )
            print(
                "UTC window 2025-02-27 18:00~20:00 rows (== +08 02:00~04:00):",
                cur.fetchone()[0],
            )
            cur.execute(
                "SELECT COUNT(*) FROM public.fact_measurements WHERE ts_bucket=%s",
                (datetime(2025, 2, 27, 19, 59, 59, tzinfo=timezone.utc),),
            )
            print("UTC 2025-02-27 19:59:59 rows (== +08 03:59:59):", cur.fetchone()[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
