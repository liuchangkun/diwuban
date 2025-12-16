from pathlib import Path
import json
import time
import sys

sys.path.insert(0, str(Path(".").resolve()))
from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def main() -> None:
    s = load_settings(Path("configs"))
    t0 = time.perf_counter()
    with get_conn(s) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("SET LOCAL statement_timeout TO '600000ms'")
            except Exception:
                pass
            cur.execute("CALL public.sp_seed_config_from_current_data(%s)", (7,))
        conn.commit()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT MIN(ts_bucket), MAX(ts_bucket) FROM public.fact_measurements"
            )
            mn_mx = cur.fetchone() or (None, None)
            cur.execute("SELECT COUNT(*) FROM public.device_running_thresholds")
            total = int(cur.fetchone()[0])
            cur.execute(
                "SELECT COUNT(*) FROM public.device_running_thresholds WHERE pf_min IS NOT NULL OR pf_max IS NOT NULL"
            )
            pf_rows = int(cur.fetchone()[0])
            cur.execute(
                """
                SELECT device_id, pf_min, pf_max, start_pre_secs, start_post_secs, stop_pre_secs, stop_post_secs, imbalance_max_pct
                FROM public.device_running_thresholds
                WHERE pf_min IS NOT NULL OR pf_max IS NOT NULL
                ORDER BY device_id
                LIMIT 5
                """
            )
            samples = [
                {
                    "device_id": r[0],
                    "pf_min": float(r[1]) if r[1] is not None else None,
                    "pf_max": float(r[2]) if r[2] is not None else None,
                    "start_pre": int(r[3]) if r[3] is not None else None,
                    "start_post": int(r[4]) if r[4] is not None else None,
                    "stop_pre": int(r[5]) if r[5] is not None else None,
                    "stop_post": int(r[6]) if r[6] is not None else None,
                    "imbalance": float(r[7]) if r[7] is not None else None,
                }
                for r in cur.fetchall() or []
            ]
    res = {
        "ok": True,
        "window": {
            "min": mn_mx[0].isoformat() if mn_mx and mn_mx[0] else None,
            "max": mn_mx[1].isoformat() if mn_mx and mn_mx[1] else None,
        },
        "counts": {"threshold_rows": total, "pf_filled_rows": pf_rows},
        "samples": samples,
        "elapsed_ms": int((time.perf_counter() - t0) * 1000),
    }
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
