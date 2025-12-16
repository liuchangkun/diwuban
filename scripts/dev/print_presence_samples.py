from __future__ import annotations

import json
import sys
from datetime import timedelta
from pathlib import Path

# 允许脚本在仓库根目录运行时导入 app/* (scripts/dev -> scripts -> repo_root)
sys.path.insert(0, str(Path(__file__).resolve().parents[2].resolve()))

from app.adapters.db.gateway import get_conn
from app.core.config.loader_new import load_settings


def main() -> int:
    settings = load_settings(Path("configs"))

    out: dict = {
        "station_candidate": None,
        "window": None,
        "presence_fn_exists": False,
        "presence_fn_rows": [],
        "present_counts": [],
        "sample_metrics_at_end": [],
    }

    try:
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                # 选择一个在映射里指标最多的泵站
                cur.execute(
                    """
                    SELECT s.name, COUNT(*) AS expected_pairs
                    FROM public.dim_mapping_items mi
                    JOIN public.dim_stations s ON s.name = mi.station_name
                    GROUP BY s.name
                    ORDER BY expected_pairs DESC
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
                if not row:
                    print(
                        json.dumps(
                            {"error": "no_station_in_mapping"}, ensure_ascii=False
                        )
                    )
                    return 2

                station_name = row[0]
                out["station_candidate"] = {
                    "station_name": station_name,
                    "expected_pairs": int(row[1]),
                }

                # 该站点最近一条秒桶时间
                cur.execute(
                    """
                    SELECT max(fm.ts_bucket) FROM public.fact_measurements fm
                    JOIN public.dim_stations s ON s.id=fm.station_id
                    WHERE s.name=%s
                    """,
                    (station_name,),
                )
                max_ts = cur.fetchone()[0]
                if max_ts is None:
                    print(
                        json.dumps(
                            {"error": "no_data_for_station", "station": station_name},
                            ensure_ascii=False,
                        )
                    )
                    return 3

                # 最近 5 秒窗口（包含端点，共 6 个秒点）
                end_ts = max_ts
                start_ts = end_ts - timedelta(seconds=5)
                out["window"] = {
                    "start_ts": start_ts.isoformat(),
                    "end_ts": end_ts.isoformat(),
                }

                # 检查函数是否存在
                cur.execute(
                    """
                    SELECT 1
                    FROM pg_proc p
                    JOIN pg_namespace n ON n.oid=p.pronamespace
                    WHERE n.nspname='public' AND p.proname='metrics_presence_per_second'
                    LIMIT 1
                    """
                )
                out["presence_fn_exists"] = cur.fetchone() is not None

                # 若存在，调用函数，取部分样例
                if out["presence_fn_exists"]:
                    # 明细（设备×秒）
                    cur.execute(
                        (
                            "SELECT station, device, ts_local, need_compute_metrics, available_metrics "
                            "FROM public.metrics_presence_per_second(%s, %s, %s, NULL) "
                            "ORDER BY station, device, ts_local LIMIT 200"
                        ),
                        (start_ts, end_ts, station_name),
                    )
                    for r in cur.fetchall():
                        out["presence_fn_rows"].append(
                            {
                                "station": r[0],
                                "device": r[1],
                                "ts_local": r[2],
                                "need_compute_metrics": r[3],
                                "available_metrics": r[4],
                            }
                        )

                    # 聚合（站×秒）：真实 present_count / missing_count
                    cur.execute(
                        (
                            "SELECT ts_local, "
                            "       SUM(COALESCE(array_length(need_compute_metrics,1),0)) AS missing_count, "
                            "       SUM(COALESCE(array_length(available_metrics,1),0))    AS present_count "
                            "FROM public.metrics_presence_per_second(%s, %s, %s, NULL) "
                            "GROUP BY ts_local ORDER BY ts_local"
                        ),
                        (start_ts, end_ts, station_name),
                    )
                    out["presence_seconds_agg"] = [
                        {
                            "ts_local": r[0],
                            "missing_count": int(r[1]),
                            "present_count": int(r[2]),
                        }
                        for r in cur.fetchall()
                    ]

                # 统计该站点窗口内每秒的已有点数（真实）
                cur.execute(
                    """
                    SELECT s.name AS station, date_trunc('second', fm.ts_bucket) AS ts_utc,
                           COUNT(*) AS present_points
                    FROM public.fact_measurements fm
                    JOIN public.dim_stations s ON s.id=fm.station_id
                    WHERE s.name=%s AND fm.ts_bucket >= %s AND fm.ts_bucket < %s
                    GROUP BY s.name, date_trunc('second', fm.ts_bucket)
                    ORDER BY ts_utc
                    LIMIT 20
                    """,
                    (station_name, start_ts, end_ts),
                )
                for c in cur.fetchall():
                    out["present_counts"].append(
                        {
                            "station": c[0],
                            "ts": c[1].isoformat() if c[1] else None,
                            "present_points": int(c[2]),
                        }
                    )

                # 选窗口末秒，列出每个设备的已有码（真实）
                ts_choice = (
                    out["present_counts"][-1]["ts"] if out["present_counts"] else None
                )
                if ts_choice:
                    cur.execute(
                        """
                        SELECT d.name AS device,
                               array_agg(DISTINCT mc.metric_key ORDER BY mc.metric_key) AS metrics
                        FROM public.fact_measurements fm
                        JOIN public.dim_stations s ON s.id=fm.station_id
                        JOIN public.dim_devices d  ON d.id=fm.device_id
                        JOIN public.dim_metric_config mc ON mc.id=fm.metric_id
                        WHERE s.name=%s AND fm.ts_bucket = %s::timestamptz
                        GROUP BY d.name
                        ORDER BY d.name
                        LIMIT 10
                        """,
                        (station_name, ts_choice),
                    )
                    for dev, metrics in cur.fetchall():
                        out["sample_metrics_at_end"].append(
                            {"device": dev, "metrics": metrics}
                        )

        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
