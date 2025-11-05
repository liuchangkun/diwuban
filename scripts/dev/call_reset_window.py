from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional


# Ensure repository root on sys.path for package imports
import sys as _sys
_root = Path(__file__).resolve().parents[2]
if str(_root) not in _sys.path:
    _sys.path.insert(0, str(_root))
from app.core.config.loader_new import load_settings


from app.adapters.db.gateway import get_conn


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print({
            "ok": False,
            "usage": "python scripts/dev/call_reset_window.py <start-iso> <end-iso> [station_id] [device_id]",
        })
        return 2
    start = argv[1]
    end = argv[2]
    station_id: Optional[int] = int(argv[3]) if len(argv) >= 4 and argv[3] not in ("", "null", "None") else None
    device_id: Optional[int] = int(argv[4]) if len(argv) >= 5 and argv[4] not in ("", "null", "None") else None

    settings = load_settings(Path("configs"))
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "CALL public.sp_reset_quality_window(%s,%s,%s,%s)",
                (start, end, station_id, device_id),
            )
        conn.commit()
    print({
        "ok": True,
        "method": "sp_reset_quality_window",
        "window": {"start": start, "end": end},
        "station_id": station_id,
        "device_id": device_id,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

