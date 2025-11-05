from __future__ import annotations

import time
import logging

from app.adapters.db.gateway import create_staging_if_not_exists, get_conn
from app.core.config.loader_new import Settings


_act = logging.getLogger("activity")


def create_staging(settings: Settings) -> None:
    """创建 staging_raw/staging_rejects（若不存在）。幂等。"""
    t0 = time.perf_counter()
    _act.info("[流程-开始] [创建staging表]")

    try:
        with get_conn(settings) as conn:
            create_staging_if_not_exists(conn)

        dur_ms = int((time.perf_counter() - t0) * 1000)
        _act.info(
            "[流程-完成] [创建staging表]",
            extra={
                "extra_data": {
                    "duration_ms": dur_ms,
                    "tables": ["staging_raw", "staging_rejects"],
                }
            },
        )

    except Exception as e:
        _act.error(
            "[流程-错误] [创建staging表失败]",
            extra={
                "extra_data": {
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            },
            exc_info=True,
        )
        raise
