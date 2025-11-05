from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
import datetime as _dt

from app.services.reporting.presence_writer import run_presence_compute

import logging

_act = logging.getLogger(__name__)


def run_presence_compute_command(
    settings,
    station_name: Optional[str],
    station_id: Optional[int],
    device_id: Optional[int],
    start: Optional[str],
    end: Optional[str],
    batch_days: int,
    rolling_days: int,
    dry_run: bool,
) -> Dict[str, Any]:
    _act.info(
        "[流程-开始] [数据存在性计算]",
        extra={
            "extra_data": {
                "station_id": station_id,
                "device_id": device_id,
                "dry_run": dry_run,
            }
        },
    )

    s_dt = _dt.datetime.fromisoformat(start) if start else None
    e_dt = _dt.datetime.fromisoformat(end) if end else None

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "station_name": station_name,
            "station_id": station_id,
            "device_id": device_id,
            "start": start,
            "end": end,
            "batch_days": batch_days,
            "rolling_days": rolling_days,
        }

    summary = run_presence_compute(
        station_name=station_name,
        station_id=station_id,
        device_id=device_id,
        start=s_dt,
        end=e_dt,
        batch_days=batch_days,
        rolling_days=rolling_days,
    )
    return {"ok": True, **(summary or {})}

