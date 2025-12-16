from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict

from app.services.ingest.merge_service import merge_window

_act = logging.getLogger(__name__)


def run_merge_fact_command(settings, window_start: str, window_end: str) -> Dict[str, Any]:
    """执行数据合并命令（CLI入口）。"""
    _act.info(
        "[流程-开始] [数据合并命令]",
        extra={
            "extra_data": {
                "window_start": window_start,
                "window_end": window_end,
            }
        },
    )

    try:
        ws = datetime.fromisoformat(window_start.replace("Z", "+00:00"))
        we = datetime.fromisoformat(window_end.replace("Z", "+00:00"))
        stats = merge_window(settings, ws, we)

        _act.info(
            "[流程-完成] [数据合并命令]",
            extra={
                "extra_data": {
                    "window_start": window_start,
                    "window_end": window_end,
                    "stats": stats,
                }
            },
        )

        return {"ok": True, "stats": stats, "window": {"start": window_start, "end": window_end}}

    except Exception as e:
        _act.error(
            "[流程-错误] [数据合并命令失败]",
            extra={
                "extra_data": {
                    "window_start": window_start,
                    "window_end": window_end,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            },
            exc_info=True,
        )
        raise

