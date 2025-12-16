from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from app.services.reporting.data_quality import generate_report

import logging

_act = logging.getLogger(__name__)


def run_data_report_command(
    settings,
    window_start: str,
    window_end: str,
    expected_interval: int,
    top_k: int,
    group_by: str,
    run_dir: Optional[str] = None,
) -> Dict[str, Any]:
    _act.info(
        "[流程-开始] [数据质量报告生成]",
        extra={
            "extra_data": {
                "window_start": window_start,
                "window_end": window_end,
                "group_by": group_by,
            }
        },
    )

    ws = datetime.fromisoformat(window_start.replace("Z", "+00:00"))
    we = datetime.fromisoformat(window_end.replace("Z", "+00:00"))
    _ = generate_report(
        settings,
        ws,
        we,
        run_dir=run_dir,
        expected_interval_seconds=expected_interval,
        top_k=top_k,
        group_by=group_by,
    )
    return {
        "ok": True,
        "window": {"start": window_start, "end": window_end},
        "expected_interval": expected_interval,
        "top_k": top_k,
        "group_by": group_by,
    }

