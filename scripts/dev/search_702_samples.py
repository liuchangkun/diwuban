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
from app.services.quality.mark_window import mark_quality_window


def main() -> int:
    days_back = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    top_devices = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    s = load_settings(Path("configs"))
    
    print(f"[INFO] Searching for 702 samples in last {days_back} days, top {top_devices} devices")
    
    with get_conn(s) as c:
        with c.cursor() as cur:
            # Get time range
            cur.execute("SELECT MAX(ts_bucket) FROM public.fact_measurements")
            max_ts = cur.fetchone()[0]
            if not max_ts:
                print(json.dumps({"ok": False, "error": "no data"}))
                return 0
            
            start_search = max_ts - dt.timedelta(days=days_back)
            end_search = max_ts
            
            # Get top active devices in the period
            cur.execute(
                """
                SELECT device_id, COUNT(*) AS cnt
                FROM public.fact_measurements
                WHERE ts_bucket >= %s AND ts_bucket < %s
                GROUP BY device_id
                ORDER BY cnt DESC
                LIMIT %s
                """,
                (start_search, end_search, top_devices),
            )
            devices = [int(row[0]) for row in cur.fetchall()]
            
            print(f"[INFO] Found {len(devices)} active devices: {devices}")
            
            # For each device, try daily windows
            for device_id in devices:
                print(f"[INFO] Testing device {device_id}")
                
                # Try 4-hour windows within the search period
                current = start_search
                while current < end_search:
                    window_end = min(current + dt.timedelta(hours=4), end_search)
                    
                    # Convert to UTC Z strings
                    if current.tzinfo is None:
                        ws_utc = current.replace(tzinfo=dt.timezone.utc)
                    else:
                        ws_utc = current.astimezone(dt.timezone.utc)
                    if window_end.tzinfo is None:
                        we_utc = window_end.replace(tzinfo=dt.timezone.utc)
                    else:
                        we_utc = window_end.astimezone(dt.timezone.utc)
                    
                    ws = ws_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
                    we = we_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
                    
                    print(f"[INFO] Testing window {ws} to {we} for device {device_id}")
                    
                    # Check if there's any data in this window for this device
                    cur.execute(
                        """
                        SELECT COUNT(*) FROM public.fact_measurements
                        WHERE device_id=%s AND ts_bucket >= %s AND ts_bucket < %s
                        """,
                        (device_id, ws_utc, we_utc),
                    )
                    row_count = int(cur.fetchone()[0])
                    if row_count == 0:
                        print(f"[INFO] No data in window, skipping")
                        current += dt.timedelta(hours=4)
                        continue
                    
                    print(f"[INFO] Found {row_count} rows, testing 702 rule")
                    
                    # Reset quality in this window for this device
                    cur.execute(
                        "CALL public.sp_reset_quality_window(%s::timestamptz,%s::timestamptz,%s::bigint,%s::bigint)",
                        (ws_utc, we_utc, None, device_id),
                    )
                    c.commit()
                    
                    # Run only 702 rule
                    try:
                        mark_quality_window(
                            settings=s,
                            start=ws,
                            end=we,
                            station_id=None,
                            device_id=device_id,
                            codes=[702],
                        )
                    except Exception as e:
                        print(f"[ERROR] mark_quality_window failed: {e}")
                        current += dt.timedelta(hours=4)
                        continue
                    
                    # Check for 702 hits
                    cur.execute(
                        """
                        SELECT COUNT(*), 
                               COUNT(NULLIF((quality_meta->>'imbalance') IS NOT NULL, FALSE))
                        FROM public.fact_measurements
                        WHERE device_id=%s AND ts_bucket >= %s AND ts_bucket < %s
                          AND quality_status=702
                        """,
                        (device_id, ws_utc, we_utc),
                    )
                    hits_702, hits_with_imb = cur.fetchone()
                    hits_702 = int(hits_702 or 0)
                    hits_with_imb = int(hits_with_imb or 0)
                    
                    if hits_702 > 0:
                        print(f"[SUCCESS] Found {hits_702} hits of 702, {hits_with_imb} with imbalance meta")
                        
                        # Get samples
                        cur.execute(
                            """
                            SELECT ts_bucket, (quality_meta->>'imbalance') AS imb,
                                   (quality_meta->>'thr') AS thr
                            FROM public.fact_measurements
                            WHERE device_id=%s AND ts_bucket >= %s AND ts_bucket < %s
                              AND quality_status=702
                            ORDER BY ts_bucket
                            LIMIT 5
                            """,
                            (device_id, ws_utc, we_utc),
                        )
                        samples = cur.fetchall()
                        
                        result = {
                            "ok": True,
                            "found": True,
                            "window": {"start": ws, "end": we, "device_id": device_id},
                            "hits_702": hits_702,
                            "hits_with_imbalance": hits_with_imb,
                            "samples": [
                                {
                                    "ts": str(ts),
                                    "imbalance": imb,
                                    "threshold": thr,
                                }
                                for ts, imb, thr in samples
                            ],
                        }
                        print(json.dumps(result, ensure_ascii=False))
                        return 0
                    else:
                        print(f"[INFO] No 702 hits in this window")
                    
                    current += dt.timedelta(hours=4)
            
            # No 702 samples found
            result = {
                "ok": True,
                "found": False,
                "searched_days": days_back,
                "searched_devices": len(devices),
                "devices": devices,
                "message": "No 702 samples found in search range",
            }
            print(json.dumps(result, ensure_ascii=False))
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
