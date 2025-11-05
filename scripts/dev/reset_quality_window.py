from __future__ import annotations

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
        print(
            "usage: python scripts/dev/reset_quality_window.py <wsZ> <weZ> <device_id>"
        )
        return 2
    ws = sys.argv[1]
    we = sys.argv[2]
    device_id = int(sys.argv[3]) if sys.argv[3] not in ("", "None", "null") else None

    s = load_settings(Path("configs"))
    try:
        from app.core.logging.setup import (
            init_logging,  # local import 避免顶层导入顺序告警
        )

        init_logging("configs", s.system.timezone.default)
    except Exception:
        pass

    with get_conn(s) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "CALL public.sp_reset_quality_window(%s::timestamptz,%s::timestamptz,%s::bigint,%s::bigint)",
                (ws, we, None, device_id),
            )
        conn.commit()
    print("reset_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
