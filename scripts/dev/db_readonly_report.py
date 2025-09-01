from __future__ import annotations

import json
from pathlib import Path
from pathlib import Path as _P

from app.adapters.db.gateway import get_conn
from app.core.config.loader import load_settings


def main() -> None:
    settings = load_settings(_P("configs"))
    out = {
        "staging_raw": {},
        "staging_rejects": {},
        "fact_measurements": {},
        "samples": {},
    }
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM public.staging_raw")
            out["staging_raw"]["count"] = int(cur.fetchone()[0])
            cur.execute("SELECT count(*) FROM public.staging_rejects")
            out["staging_rejects"]["count"] = int(cur.fetchone()[0])
            cur.execute("SELECT count(*) FROM public.fact_measurements")
            out["fact_measurements"]["count"] = int(cur.fetchone()[0])
            # 采样事实
            cur.execute(
                "SELECT station_id, device_id, metric_id, ts_raw, ts_bucket, value, source_hint FROM public.fact_measurements ORDER BY ts_bucket DESC LIMIT 5"
            )
            rows = cur.fetchall()
            out["samples"]["fact_measurements"] = [
                {
                    "station_id": int(r[0]),
                    "device_id": int(r[1]),
                    "metric_id": int(r[2]),
                    "ts_raw": str(r[3]),
                    "ts_bucket": str(r[4]),
                    "value": float(r[5]) if r[5] is not None else None,
                    "source_hint": r[6],
                }
                for r in rows
            ]
            # 计算 staging_raw 经转换的 UTC 时间范围与最近计数
            cur.execute(
                """
                WITH parsed AS (
                  SELECT
                    (to_timestamp(rtrim(replace(split_part(sr."DataTime", '.', 1), 'T', ' '), 'Z'), 'YYYY-MM-DD HH24:MI:SS') AT TIME ZONE COALESCE(ds.extra->>'tz', 'Asia/Shanghai')) AS ts_utc
                  FROM public.staging_raw sr
                  JOIN public.dim_stations ds ON ds.name = sr.station_name
                )
                SELECT min(ts_utc), max(ts_utc), count(*) FROM parsed
                """
            )
            r = cur.fetchone()
            out["staging_raw"]["ts_utc_min"] = str(r[0]) if r and r[0] else None
            out["staging_raw"]["ts_utc_max"] = str(r[1]) if r and r[1] else None
            out["staging_raw"]["rows_parsable"] = int(r[2]) if r and r[2] else 0
            # 分区检查：列出父表与所有分区边界
            cur.execute(
                """
                SELECT
                  parent.relname AS parent,
                  child.relname AS child,
                  pg_get_expr(child.relpartbound, child.oid) AS bounds
                FROM pg_inherits
                JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
                JOIN pg_class child ON pg_inherits.inhrelid = child.oid
                WHERE parent.relname = 'fact_measurements'
                ORDER BY child.relname
                """
            )
            out["partitions"] = cur.fetchall()
            # 写入最新5条source_hint到日志文件（使用模块级 _P，避免局部覆盖导致 UnboundLocalError）
            try:
                hints = [r["source_hint"] for r in out["samples"]["fact_measurements"]]
                p = _P("logs") / "reports" / "source_hint_top5.txt"
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(
                    "\n".join(f"{i+1}. {h}" for i, h in enumerate(hints)),
                    encoding="utf-8",
                )
            except Exception:
                pass

    Path("logs/reports").mkdir(parents=True, exist_ok=True)
    Path("logs/reports/db_readonly_report.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
