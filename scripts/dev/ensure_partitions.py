from __future__ import annotations
from datetime import datetime, timezone

from app.adapters.db.gateway import get_conn, _ensure_fact_weekly_partitions  # type: ignore
from app.core.config.loader import load_settings
from pathlib import Path as _P


def main() -> None:
    settings = load_settings(_P("configs"))
    # 手动确保 2025-02-24 ~ 2025-03-03 周分区存在（UTC）
    s = datetime(2025, 2, 24, 0, 0, 0, tzinfo=timezone.utc)
    e = datetime(2025, 3, 3, 0, 0, 0, tzinfo=timezone.utc)
    with get_conn(settings) as conn:
        _ensure_fact_weekly_partitions(conn, s, e)
    print("done")


if __name__ == "__main__":
    main()
