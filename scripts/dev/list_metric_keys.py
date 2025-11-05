from pathlib import Path
from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn
import json


def main():
    s = load_settings(Path("configs"))
    with get_conn(s) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, metric_key FROM public.dim_metric_config ORDER BY metric_key"
            )
            rows = cur.fetchall()
    print(
        json.dumps(
            {"count": len(rows), "sample": rows[:50]}, ensure_ascii=False, indent=2
        )
    )


if __name__ == "__main__":
    main()
