from __future__ import annotations

import logging

from app.adapters.db.gateway import create_staging_if_not_exists, get_conn
from app.core.config.loader import Settings

logger = logging.getLogger(__name__)


def create_staging(settings: Settings) -> None:
    """创建 staging_raw/staging_rejects（若不存在）。幂等。"""
    with get_conn(settings) as conn:
        create_staging_if_not_exists(conn)
    logger.info(
        "staging 表已创建或已存在", extra={"event": "staging.create", "extra": {}}
    )
