from __future__ import annotations

import json
import sys
from pathlib import Path

# ensure repo root
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.adapters.db.gateway import get_conn
from app.core.config.loader_new import load_settings


def main() -> int:
    if len(sys.argv) < 4:
        print("usage: python scripts/dev/debug_702_rule.py <wsZ> <weZ> <device_id>")
        return 2

    ws = sys.argv[1]
    we = sys.argv[2]
    device_id = int(sys.argv[3])

    s = load_settings(Path("configs"))

    with get_conn(s) as c:
        with c.cursor() as cur:
            # Get metric IDs
            cur.execute(
                """
                SELECT id, metric_key FROM public.dim_metric_config 
                WHERE metric_key IN ('pump_current_a', 'pump_current_b', 'pump_current_c')
                ORDER BY metric_key
            """
            )
            metrics = cur.fetchall()
            cur_a_id, cur_b_id, cur_c_id = [int(m[0]) for m in metrics]

            # Get threshold
            cur.execute(
                "SELECT COALESCE(MAX(imbalance_max_pct), 0.15) FROM public.device_running_thresholds"
            )
            threshold = float(cur.fetchone()[0])

            print(f"[DEBUG] Metric IDs: A={cur_a_id}, B={cur_b_id}, C={cur_c_id}")
            print(f"[DEBUG] Threshold: {threshold}")

            # Check if we have data in fwin (temp table from stored procedure)
            # Since we can't access temp tables, let's simulate the 702 logic manually

            # Step 1: Check three-phase current data
            cur.execute(
                """
                SELECT fa.ts_bucket, fa.id AS id_a, fb.id AS id_b, fc.id AS id_c,
                       fa.value AS va, fb.value AS vb, fc.value AS vc,
                       COALESCE(fa.quality_status, 0) AS qs_a,
                       COALESCE(fb.quality_status, 0) AS qs_b,
                       COALESCE(fc.quality_status, 0) AS qs_c
                FROM public.fact_measurements fa
                JOIN public.fact_measurements fb ON fb.station_id=fa.station_id AND fb.device_id=fa.device_id 
                     AND fb.ts_bucket=fa.ts_bucket AND fb.metric_id=%s
                JOIN public.fact_measurements fc ON fc.station_id=fa.station_id AND fc.device_id=fa.device_id 
                     AND fc.ts_bucket=fa.ts_bucket AND fc.metric_id=%s
                WHERE fa.device_id=%s AND fa.ts_bucket >= %s AND fa.ts_bucket < %s
                  AND fa.metric_id=%s
                ORDER BY fa.ts_bucket
                LIMIT 10
            """,
                (cur_b_id, cur_c_id, device_id, ws, we, cur_a_id),
            )

            three_phase_data = cur.fetchall()
            print(f"[DEBUG] Found {len(three_phase_data)} three-phase current records")

            if not three_phase_data:
                print("[DEBUG] No three-phase current data found")
                return 0

            # Step 2: Check running status
            cur.execute(
                """
                SELECT ts_bucket, running FROM public.mv_device_running_1s
                WHERE station_id=1 AND device_id=%s AND ts_bucket >= %s AND ts_bucket < %s
                ORDER BY ts_bucket
                LIMIT 10
            """,
                (device_id, ws, we),
            )

            running_data = cur.fetchall()
            print(f"[DEBUG] Found {len(running_data)} running status records")

            # Step 3: Calculate imbalances manually
            imbalances = []
            for row in three_phase_data:
                ts, id_a, id_b, id_c, va, vb, vc, qs_a, qs_b, qs_c = row

                # Check quality status (should be 0 for all phases)
                if qs_a != 0 or qs_b != 0 or qs_c != 0:
                    print(
                        f"[DEBUG] {ts}: Skipping due to quality status: A={qs_a}, B={qs_b}, C={qs_c}"
                    )
                    continue

                # Check if device is running at this timestamp
                running = any(r[1] == 1 for r in running_data if r[0] == ts)
                if not running:
                    print(f"[DEBUG] {ts}: Skipping due to device not running")
                    continue

                # Calculate imbalance
                va, vb, vc = float(va), float(vb), float(vc)
                if va + vb + vc > 0:
                    avg = (va + vb + vc) / 3.0
                    if avg != 0:
                        imb = (max(va, vb, vc) - min(va, vb, vc)) / avg
                        imbalances.append((ts, id_a, id_b, id_c, va, vb, vc, imb))

                        status = "TRIGGER" if imb > threshold else "OK"
                        print(
                            f"[DEBUG] {ts}: A={va:.2f} B={vb:.2f} C={vc:.2f} | imb={imb:.4f} | {status}"
                        )

            print(f"[DEBUG] Calculated {len(imbalances)} imbalance values")

            # Step 4: Check what would be updated
            trigger_count = sum(
                1 for _, _, _, _, _, _, _, imb in imbalances if imb > threshold
            )
            print(
                f"[DEBUG] {trigger_count} records would trigger 702 rule (imbalance > {threshold})"
            )

            # Step 5: Check actual fact_measurements quality_status
            cur.execute(
                """
                SELECT COUNT(*) FROM public.fact_measurements
                WHERE device_id=%s AND ts_bucket >= %s AND ts_bucket < %s
                  AND quality_status = 702
            """,
                (device_id, ws, we),
            )

            actual_702_count = int(cur.fetchone()[0])
            print(
                f"[DEBUG] Actual 702 records in fact_measurements: {actual_702_count}"
            )

            result = {
                "debug": True,
                "window": {"start": ws, "end": we, "device_id": device_id},
                "metric_ids": {
                    "current_a": cur_a_id,
                    "current_b": cur_b_id,
                    "current_c": cur_c_id,
                },
                "threshold": threshold,
                "three_phase_records": len(three_phase_data),
                "running_records": len(running_data),
                "calculated_imbalances": len(imbalances),
                "should_trigger": trigger_count,
                "actual_702_records": actual_702_count,
                "sample_imbalances": [
                    {
                        "ts": str(ts),
                        "values": {"a": float(va), "b": float(vb), "c": float(vc)},
                        "imbalance": float(imb),
                        "triggers": imb > threshold,
                    }
                    for ts, _, _, _, va, vb, vc, imb in imbalances[:5]
                ],
            }

            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
