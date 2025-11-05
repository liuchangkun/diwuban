from __future__ import annotations

import json
import sys
from pathlib import Path
from datetime import datetime

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def main(start_iso: str, end_iso: str) -> None:
    start = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    end = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))

    settings = load_settings(Path("configs"))
    out: dict[str, object] = {"window": {"start": start_iso, "end": end_iso}}

    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) FROM public.fact_measurements
                WHERE ts_bucket >= %s AND ts_bucket < %s
                """,
                (start, end),
            )
            out["rows_total"] = int(cur.fetchone()[0])

            for hour_start_iso in ("2025-02-27T18:00:00Z", "2025-02-27T19:00:00Z"):
                hs = datetime.fromisoformat(hour_start_iso.replace("Z", "+00:00"))
                he = datetime.fromisoformat(
                    ("2025-02-27T19:00:00Z" if "18:" in hour_start_iso else "2025-02-27T20:00:00Z").replace("Z", "+00:00")
                )
                label = hour_start_iso[11:13] + ":00"
                cur.execute(
                    """
                    SELECT COUNT(*) FROM public.fact_measurements
                    WHERE ts_bucket >= %s AND ts_bucket < %s
                      AND quality_status IS NOT NULL
                    """,
                    (hs, he),
                )
                out[f"marked_{label}"] = int(cur.fetchone()[0])

            cur.execute(
                "SELECT MIN(ts_bucket), MAX(ts_bucket) FROM public.fact_measurements"
            )
            mm = cur.fetchone()
            out["fact_min_ts"], out["fact_max_ts"] = (
                mm[0].isoformat() if mm[0] else None,
                mm[1].isoformat() if mm[1] else None,
            )

            # 质量规则命中摘要（基于质量画像日志）
            cur.execute(
                """
                SELECT split_part(stage, '_', 2) AS code, SUM(rows_affected)::bigint AS cnt
                FROM public.quality_profile_log
                WHERE window_start >= %s AND window_end <= %s AND stage LIKE 'update_%%'
                GROUP BY split_part(stage, '_', 2)
                ORDER BY 1
                """,
                (start, end),
            )
            out["quality_profile_summary"] = [
                {"code": int(r[0]), "count": int(r[1])} for r in (cur.fetchall() or [])
            ]

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/verify_quality_counts.py <start_iso> <end_iso>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])

