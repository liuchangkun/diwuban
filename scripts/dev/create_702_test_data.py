from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

# ensure repo root
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def main() -> int:
    """
    Create test data that will trigger 702 three-phase imbalance rule.
    We'll modify existing data for device_id=1 in a small window to create imbalance.
    """
    if len(sys.argv) < 3:
        print("usage: python scripts/dev/create_702_test_data.py <wsZ> <weZ>")
        return 2
    
    ws = sys.argv[1]
    we = sys.argv[2]
    
    s = load_settings(Path("configs"))
    
    with get_conn(s) as c:
        with c.cursor() as cur:
            # Get current threshold
            cur.execute("SELECT COALESCE(MAX(imbalance_max_pct), 0.15) FROM public.device_running_thresholds")
            threshold = float(cur.fetchone()[0])
            print(f"[INFO] Current 702 threshold: {threshold}")
            
            # Get metric IDs for three-phase current
            cur.execute("""
                SELECT id, metric_key FROM public.dim_metric_config 
                WHERE metric_key IN ('pump_current_a', 'pump_current_b', 'pump_current_c')
                ORDER BY metric_key
            """)
            metrics = cur.fetchall()
            if len(metrics) != 3:
                print(f"[ERROR] Expected 3 current metrics, got {len(metrics)}")
                return 1
            
            cur_a_id, cur_b_id, cur_c_id = [int(m[0]) for m in metrics]
            print(f"[INFO] Current metric IDs: A={cur_a_id}, B={cur_b_id}, C={cur_c_id}")
            
            # Check existing data in the window for device_id=1
            cur.execute("""
                SELECT COUNT(*) FROM public.fact_measurements
                WHERE device_id=1 AND ts_bucket >= %s AND ts_bucket < %s
                  AND metric_id IN (%s, %s, %s)
            """, (ws, we, cur_a_id, cur_b_id, cur_c_id))
            existing_count = int(cur.fetchone()[0])
            print(f"[INFO] Existing current measurements in window: {existing_count}")
            
            if existing_count == 0:
                print("[ERROR] No existing current data in window to modify")
                return 1
            
            # Get sample of existing data
            cur.execute("""
                SELECT ts_bucket, metric_id, value FROM public.fact_measurements
                WHERE device_id=1 AND ts_bucket >= %s AND ts_bucket < %s
                  AND metric_id IN (%s, %s, %s)
                ORDER BY ts_bucket, metric_id
                LIMIT 30
            """, (ws, we, cur_a_id, cur_b_id, cur_c_id))
            samples = cur.fetchall()
            
            print(f"[INFO] Sample data (first 10 rows):")
            for i, (ts, mid, val) in enumerate(samples[:10]):
                print(f"  {ts} | metric_id={mid} | value={val}")
            
            # Create artificial imbalance by modifying phase A values
            # We'll make phase A much higher than B and C to trigger imbalance
            print(f"[INFO] Creating artificial imbalance by boosting phase A current...")
            
            # Update phase A current to create imbalance > threshold
            # For device_id=1, we'll multiply phase A by 3 to create significant imbalance
            cur.execute("""
                UPDATE public.fact_measurements
                SET value = value * 3.0
                WHERE device_id=1 AND ts_bucket >= %s AND ts_bucket < %s
                  AND metric_id = %s
                  AND COALESCE(quality_status, 0) = 0
            """, (ws, we, cur_a_id))
            
            updated_count = cur.rowcount
            print(f"[INFO] Updated {updated_count} phase A current values")
            
            # Also ensure device is marked as running in mv_device_running_1s
            cur.execute("""
                INSERT INTO public.mv_device_running_1s (station_id, device_id, ts_bucket, running)
                SELECT DISTINCT 1, 1, ts_bucket, 1
                FROM public.fact_measurements
                WHERE device_id=1 AND ts_bucket >= %s AND ts_bucket < %s
                ON CONFLICT (station_id, device_id, ts_bucket) DO UPDATE SET running = 1
            """, (ws, we))
            
            running_count = cur.rowcount
            print(f"[INFO] Ensured {running_count} running status entries")
            
            c.commit()
            
            # Verify the imbalance we created
            cur.execute("""
                WITH cur3 AS (
                  SELECT fa.ts_bucket,
                         fa.value AS va, fb.value AS vb, fc.value AS vc
                  FROM public.fact_measurements fa
                  JOIN public.fact_measurements fb ON fb.device_id=fa.device_id AND fb.ts_bucket=fa.ts_bucket AND fb.metric_id=%s
                  JOIN public.fact_measurements fc ON fc.device_id=fa.device_id AND fc.ts_bucket=fa.ts_bucket AND fc.metric_id=%s
                  WHERE fa.device_id=1 AND fa.ts_bucket >= %s AND fa.ts_bucket < %s
                    AND fa.metric_id=%s
                  LIMIT 5
                ), imb AS (
                  SELECT ts_bucket, va, vb, vc,
                         CASE WHEN (va+vb+vc)>0 THEN (GREATEST(va,vb,vc)-LEAST(va,vb,vc))/NULLIF(((va+vb+vc)/3.0),0) ELSE NULL END AS imbalance
                  FROM cur3
                )
                SELECT ts_bucket, va, vb, vc, imbalance
                FROM imb
                WHERE imbalance IS NOT NULL
                ORDER BY ts_bucket
            """, (cur_b_id, cur_c_id, ws, we, cur_a_id))
            
            imbalance_samples = cur.fetchall()
            print(f"[INFO] Created imbalance samples:")
            for ts, va, vb, vc, imb in imbalance_samples:
                print(f"  {ts} | A={va:.2f} B={vb:.2f} C={vc:.2f} | imbalance={imb:.4f} (threshold={threshold})")
            
            result = {
                "ok": True,
                "window": {"start": ws, "end": we},
                "threshold": threshold,
                "updated_phase_a": updated_count,
                "running_entries": running_count,
                "imbalance_samples": len(imbalance_samples),
                "max_imbalance": max([float(imb) for _, _, _, _, imb in imbalance_samples]) if imbalance_samples else 0,
            }
            
            print(json.dumps(result, ensure_ascii=False))
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
