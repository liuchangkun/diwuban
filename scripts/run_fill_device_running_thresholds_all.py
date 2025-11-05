from __future__ import annotations

from pathlib import Path
import json

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def main():
    s = load_settings(Path("configs"))
    summary: dict = {"ok": False}
    with get_conn(s) as conn:
        with conn.cursor() as cur:
            # 窗口：使用 fact_measurements 的最小/最大时间（半开区间 [start, end)）
            cur.execute("SELECT MIN(ts_bucket), MAX(ts_bucket) FROM public.fact_measurements")
            row = cur.fetchone() or (None, None)
            start, end = row[0], row[1]
            if not start or not end:
                print(json.dumps({"ok": False, "error": "fact_measurements 无数据"}, ensure_ascii=False))
                return
            # ensure rows
            cur.execute(
                """
                INSERT INTO public.device_running_thresholds(device_id)
                SELECT DISTINCT fm.device_id
                FROM public.fact_measurements fm
                ON CONFLICT (device_id) DO NOTHING
                """
            )
            # PF: pf_min/pf_max（5%/95%），质量=0，稳态：phase=1 或（该秒没有phase数据时 running=1）
            cur.execute(
                """
                WITH ids AS (
                  SELECT
                    (SELECT id FROM public.dim_metric_config WHERE metric_key='device_phase') AS phase_id,
                    (SELECT id FROM public.dim_metric_config WHERE metric_key='device_running') AS run_id,
                    (SELECT id FROM public.dim_metric_config WHERE metric_key IN ('pump_power_factor','power_factor') LIMIT 1) AS pf_id
                ), base AS (
                  SELECT f.device_id, f.value::float8 AS pf
                  FROM public.fact_measurements f
                  JOIN ids ON TRUE
                  WHERE f.metric_id = ids.pf_id
                    AND f.ts_bucket >= %s AND f.ts_bucket < (%s + interval '1 second')
                    AND COALESCE(f.quality_status,0)=0 AND f.value IS NOT NULL
                    AND (
                      EXISTS (
                        SELECT 1 FROM public.fact_measurements ph
                        WHERE ph.station_id=f.station_id AND ph.device_id=f.device_id AND ph.ts_bucket=f.ts_bucket
                          AND ph.metric_id = (SELECT phase_id FROM ids) AND ph.value=1
                      )
                      OR (
                        NOT EXISTS (
                          SELECT 1 FROM public.fact_measurements ph2
                          WHERE ph2.station_id=f.station_id AND ph2.device_id=f.device_id AND ph2.ts_bucket=f.ts_bucket
                            AND ph2.metric_id = (SELECT phase_id FROM ids)
                        )
                        AND EXISTS (
                          SELECT 1 FROM public.fact_measurements fr
                          WHERE fr.station_id=f.station_id AND fr.device_id=f.device_id AND fr.ts_bucket=f.ts_bucket
                            AND fr.metric_id = (SELECT run_id FROM ids) AND fr.value=1
                        )
                      )
                    )
                ), agg AS (
                  SELECT device_id,
                         percentile_cont(0.05) WITHIN GROUP (ORDER BY pf) AS pf_min,
                         percentile_cont(0.95) WITHIN GROUP (ORDER BY pf) AS pf_max
                  FROM base GROUP BY device_id
                )
                UPDATE public.device_running_thresholds t
                SET pf_min = COALESCE(t.pf_min, a.pf_min),
                    pf_max = COALESCE(t.pf_max, a.pf_max)
                FROM agg a
                WHERE a.device_id = t.device_id;
                """,
                (start, end),
            )
            # Power: p_on/p_off（20%/80%，确保 on>=off）
            cur.execute(
                """
                WITH ids AS (
                  SELECT (SELECT id FROM public.dim_metric_config WHERE metric_key IN ('pump_active_power','active_power','power') LIMIT 1) AS p_id
                ), base AS (
                  SELECT f.device_id, f.value::float8 AS v
                  FROM public.fact_measurements f
                  JOIN ids ON TRUE
                  WHERE ids.p_id IS NOT NULL AND f.metric_id = ids.p_id
                    AND f.ts_bucket >= %s AND f.ts_bucket < (%s + interval '1 second')
                    AND COALESCE(f.quality_status,0)=0 AND f.value IS NOT NULL
                ), agg AS (
                  SELECT device_id,
                         percentile_cont(0.20) WITHIN GROUP (ORDER BY v) AS v20,
                         percentile_cont(0.80) WITHIN GROUP (ORDER BY v) AS v80
                  FROM base GROUP BY device_id
                )
                UPDATE public.device_running_thresholds t
                SET p_off = COALESCE(t.p_off, a.v20),
                    p_on  = COALESCE(t.p_on,  GREATEST(a.v80, COALESCE(t.p_off, a.v20)))
                FROM agg a
                WHERE a.device_id = t.device_id;
                """,
                (start, end),
            )
            # Frequency: f_on/f_off（20%/80%）
            cur.execute(
                """
                WITH ids AS (
                  SELECT (SELECT id FROM public.dim_metric_config WHERE metric_key IN ('pump_frequency','frequency') LIMIT 1) AS f_id
                ), base AS (
                  SELECT f.device_id, f.value::float8 AS v
                  FROM public.fact_measurements f
                  JOIN ids ON TRUE
                  WHERE ids.f_id IS NOT NULL AND f.metric_id = ids.f_id
                    AND f.ts_bucket >= %s AND f.ts_bucket < (%s + interval '1 second')
                    AND COALESCE(f.quality_status,0)=0 AND f.value IS NOT NULL
                ), agg AS (
                  SELECT device_id,
                         percentile_cont(0.20) WITHIN GROUP (ORDER BY v) AS v20,
                         percentile_cont(0.80) WITHIN GROUP (ORDER BY v) AS v80
                  FROM base GROUP BY device_id
                )
                UPDATE public.device_running_thresholds t
                SET f_off = COALESCE(t.f_off, a.v20),
                    f_on  = COALESCE(t.f_on,  GREATEST(a.v80, COALESCE(t.f_off, a.v20)))
                FROM agg a
                WHERE a.device_id = t.device_id;
                """,
                (start, end),
            )
            # Current: i_on/i_off（三相最大：20%/80%）。若无三相电流则跳过。
            cur.execute(
                """
                WITH ids AS (
                  SELECT
                    (SELECT id FROM public.dim_metric_config WHERE metric_key IN ('current_a','ia','i_a') LIMIT 1) AS ia,
                    (SELECT id FROM public.dim_metric_config WHERE metric_key IN ('current_b','ib','i_b') LIMIT 1) AS ib,
                    (SELECT id FROM public.dim_metric_config WHERE metric_key IN ('current_c','ic','i_c') LIMIT 1) AS ic
                ), base AS (
                  SELECT f.device_id, f.ts_bucket AS ts,
                         MAX(CASE WHEN f.metric_id=(SELECT ia FROM ids) THEN f.value::float8 END) AS ia,
                         MAX(CASE WHEN f.metric_id=(SELECT ib FROM ids) THEN f.value::float8 END) AS ib,
                         MAX(CASE WHEN f.metric_id=(SELECT ic FROM ids) THEN f.value::float8 END) AS ic
                  FROM public.fact_measurements f
                  JOIN ids ON TRUE
                  WHERE ((SELECT ia FROM ids) IS NOT NULL OR (SELECT ib FROM ids) IS NOT NULL OR (SELECT ic FROM ids) IS NOT NULL)
                    AND f.metric_id IN ((SELECT ia FROM ids), (SELECT ib FROM ids), (SELECT ic FROM ids))
                    AND f.ts_bucket >= %s AND f.ts_bucket < (%s + interval '1 second')
                    AND COALESCE(f.quality_status,0)=0
                  GROUP BY f.device_id, f.ts_bucket
                ), imax AS (
                  SELECT device_id,
                         GREATEST(COALESCE(ia, -1e12), COALESCE(ib, -1e12), COALESCE(ic, -1e12)) AS i
                  FROM base
                ), agg AS (
                  SELECT device_id,
                         percentile_cont(0.20) WITHIN GROUP (ORDER BY i) AS v20,
                         percentile_cont(0.80) WITHIN GROUP (ORDER BY i) AS v80
                  FROM imax GROUP BY device_id
                )
                UPDATE public.device_running_thresholds t
                SET i_off = COALESCE(t.i_off, a.v20),
                    i_on  = COALESCE(t.i_on,  GREATEST(a.v80, COALESCE(t.i_off, a.v20)))
                FROM agg a
                WHERE a.device_id = t.device_id;
                """,
                (start, end),
            )
            # 默认窗口/不平衡阈值（仅当为空）
            cur.execute(
                """
                UPDATE public.device_running_thresholds t
                SET start_pre_secs  = COALESCE(start_pre_secs, 3),
                    start_post_secs = COALESCE(start_post_secs, 5),
                    stop_pre_secs   = COALESCE(stop_pre_secs, 3),
                    stop_post_secs  = COALESCE(stop_post_secs, 3),
                    imbalance_max_pct = COALESCE(imbalance_max_pct, 20.0)
                """
            )
            conn.commit()
        # 汇总
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM public.device_running_thresholds")
            total = int(cur.fetchone()[0])
            cur.execute(
                "SELECT COUNT(*) FROM public.device_running_thresholds WHERE pf_min IS NOT NULL OR pf_max IS NOT NULL"
            )
            pf_filled = int(cur.fetchone()[0])
            cur.execute(
                """
                SELECT COUNT(*) FROM public.device_running_thresholds
                WHERE (i_on IS NOT NULL AND i_off IS NOT NULL)
                   OR (p_on IS NOT NULL AND p_off IS NOT NULL)
                   OR (f_on IS NOT NULL AND f_off IS NOT NULL)
                """
            )
            io_filled = int(cur.fetchone()[0])
            cur.execute(
                "SELECT device_id, pf_min, pf_max, i_on, i_off, p_on, p_off, f_on, f_off FROM public.device_running_thresholds ORDER BY device_id LIMIT 5"
            )
            samples = [
                {
                    "device_id": r[0],
                    "pf_min": float(r[1]) if r[1] is not None else None,
                    "pf_max": float(r[2]) if r[2] is not None else None,
                    "i_on": float(r[3]) if r[3] is not None else None,
                    "i_off": float(r[4]) if r[4] is not None else None,
                    "p_on": float(r[5]) if r[5] is not None else None,
                    "p_off": float(r[6]) if r[6] is not None else None,
                    "f_on": float(r[7]) if r[7] is not None else None,
                    "f_off": float(r[8]) if r[8] is not None else None,
                }
                for r in cur.fetchall() or []
            ]
    summary.update(
        {
            "ok": True,
            "window": {"start": start.isoformat(), "end": end.isoformat()},
            "counts": {"total_rows": total, "pf_filled_rows": pf_filled, "i_p_f_onoff_filled_rows": io_filled},
            "samples": samples,
        }
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

