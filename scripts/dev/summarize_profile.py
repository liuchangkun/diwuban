import sys
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def parse_ts(s: str) -> datetime:
    if s.endswith('Z'):
        s = s[:-1] + '+00:00'
    return datetime.fromisoformat(s)


def main():
    station_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    device_id  = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    day        = parse_ts(sys.argv[3]) if len(sys.argv) > 3 else None

    settings = load_settings(Path('configs'))
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            if day is None:
                cur.execute(
                    """
                    SELECT date_trunc('day', MIN(window_start)) AS d0,
                           date_trunc('day', MAX(window_end))   AS d1
                    FROM public.quality_profile_log
                    WHERE station_id=%s AND device_id=%s
                    """,
                    (station_id, device_id),
                )
                r = cur.fetchone()
                if not r or not r[0]:
                    print({"ok": False, "msg": "no profile logs"})
                    return
                d0, d1 = r
                day = d0

            s = day
            e = day + timedelta(days=1)
            cur.execute(
                """
                SELECT stage,
                       COUNT(*)    AS calls,
                       ROUND(SUM(duration_ms)::numeric,2) AS sum_ms,
                       ROUND(AVG(duration_ms)::numeric,2) AS avg_ms,
                       ROUND(MAX(duration_ms)::numeric,2) AS max_ms,
                       SUM(COALESCE(rows_affected,0))     AS rows
                FROM public.quality_profile_log
                WHERE station_id=%s AND device_id=%s
                  AND window_start>=%s AND window_end<=%s
                GROUP BY stage ORDER BY sum_ms DESC
                """,
                (station_id, device_id, s, e),
            )
            rows = cur.fetchall()
    print({"ok": True, "day": s.isoformat(), "stages": rows})


if __name__ == '__main__':
    main()

