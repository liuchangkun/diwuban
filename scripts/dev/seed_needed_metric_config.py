from pathlib import Path
import sys
sys.path.insert(0, str(Path('.').resolve()))

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn
from psycopg.rows import tuple_row

NEEDED = [
    ("frequency", "Hz", "Hz"),
    ("voltage_a", "V", "V"),
    ("voltage_b", "V", "V"),
    ("voltage_c", "V", "V"),
    ("current_a", "A", "A"),
    ("current_b", "A", "A"),
    ("current_c", "A", "A"),
    ("power", "kW", "kW"),
    ("kwh", "kWh", "kWh"),
    ("power_factor", "", ""),
    ("pressure", "MPa", "MPa"),
    ("flow_rate", "m3/h", "m3/h"),
    ("cumulative_flow", "m3", "m3"),
]


def run() -> int:
    settings = load_settings(Path("configs"))
    inserted = 0
    with get_conn(settings) as conn:
        with conn.cursor(row_factory=tuple_row) as cur:
            for k, u, ud in NEEDED:
                cur.execute(
                    """
                    INSERT INTO public.dim_metric_config(metric_key, unit, unit_display, decimals_policy)
                    SELECT %s, %s, %s, 'as_is'
                    WHERE NOT EXISTS (
                      SELECT 1 FROM public.dim_metric_config m WHERE m.metric_key = %s
                    )
                    """,
                    (k, u, ud, k),
                )
                if cur.rowcount and cur.rowcount > 0:
                    inserted += cur.rowcount
        conn.commit()
    print(f"[SEED] dim_metric_config inserted={inserted}")

    with get_conn(settings) as conn:
        with conn.cursor(row_factory=tuple_row) as cur:
            cur.execute(
                "SELECT COUNT(*) FROM public.dim_metric_config WHERE metric_key = ANY(%s)",
                ([k for k, _, _ in NEEDED],),
            )
            present = cur.fetchone()[0]
            print(f"[SEED] dim_metric_config present_keys={present}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

