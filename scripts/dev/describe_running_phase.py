from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure repo root on sys.path so we can import app.*
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def main() -> int:
    settings = load_settings(Path("configs"))
    out: dict[str, object] = {}

    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            def cols(schema: str, table: str):
                cur.execute(
                    """
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema=%s AND table_name=%s
                    ORDER BY ordinal_position
                    """,
                    (schema, table),
                )
                return cur.fetchall()

            def sample(schema: str, table: str, limit: int = 5):
                cur.execute(f"SELECT * FROM {schema}.{table} ORDER BY 1,2,3 LIMIT %s", (limit,))
                names = [d[0] for d in cur.description]
                rows = cur.fetchall()
                return {"columns": names, "rows": rows}

            # Describe mv_device_running_1s
            out["mv_device_running_1s_cols"] = cols("public", "mv_device_running_1s")
            try:
                out["mv_device_running_1s_sample"] = sample("public", "mv_device_running_1s")
            except Exception as e:
                out["mv_device_running_1s_sample_error"] = str(e)

            # Describe fact_measurements and check op columns
            out["fact_measurements_cols"] = cols("public", "fact_measurements")
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema='public' AND table_name='fact_measurements' AND column_name IN ('operation_phase','operation_phase_type')"
            )
            out["fact_has_op_columns"] = bool(cur.fetchone()[0])

            # Check device_running/device_phase metric ids and row counts
            cur.execute("SELECT id FROM public.dim_metric_config WHERE metric_key='device_running'")
            r = cur.fetchone()
            out["metric_device_running_id"] = int(r[0]) if r else None
            cur.execute("SELECT id FROM public.dim_metric_config WHERE metric_key='device_phase'")
            r = cur.fetchone()
            out["metric_device_phase_id"] = int(r[0]) if r else None
            if out["metric_device_running_id"]:
                cur.execute("SELECT COUNT(*) FROM public.fact_measurements WHERE metric_id=%s", (out["metric_device_running_id"],))
                out["fact_rows_device_running"] = int(cur.fetchone()[0])
            if out["metric_device_phase_id"]:
                cur.execute("SELECT COUNT(*) FROM public.fact_measurements WHERE metric_id=%s", (out["metric_device_phase_id"],))
                out["fact_rows_device_phase"] = int(cur.fetchone()[0])

    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

