from __future__ import annotations

import sys
from pathlib import Path

# ensure repo root
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config.loader_new import load_settings
from app.services.quality.mark_window import mark_quality_window


def main() -> int:
    if len(sys.argv) < 5:
        print(
            "usage: python scripts/dev/run_mark_with_codes.py <wsZ> <weZ> <device_id> <codes_csv>"
        )
        return 2
    ws = sys.argv[1]
    we = sys.argv[2]
    device_id = int(sys.argv[3]) if sys.argv[3] not in ("", "None", "null") else None
    codes = [int(x) for x in sys.argv[4].split(",") if x.strip()]

    s = load_settings(Path("configs"))
    try:
        from app.core.logging.setup import (
            init_logging,  # local import 避免顶层导入顺序告警
        )

        init_logging("configs", s.system.timezone.default)
    except Exception:
        pass

    res = mark_quality_window(
        settings=s,
        start=ws,
        end=we,
        station_id=None,
        device_id=device_id,
        codes=codes,
        diag_level=None,
    )
    import json

    print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
