from contextlib import asynccontextmanager
from pathlib import Path

import asyncpg

from app.core.config.loader import load_settings


@asynccontextmanager
async def get_ro_pool():  # 占位，后续完善类型
    # 严格使用 YAML 配置，不读取 ENV/代码硬编码
    settings = load_settings(Path("configs"))
    pool_min = settings.db.pool.min_size
    pool_max = settings.db.pool.max_size
    if settings.db.dsn_read:
        pool = await asyncpg.create_pool(
            dsn=settings.db.dsn_read,
            min_size=pool_min,
            max_size=pool_max,
            max_inactive_connection_lifetime=float(
                settings.db.pool.max_inactive_connection_lifetime
            ),
            timeout=float(settings.db.timeouts.connect_timeout_ms) / 1000.0,
        )
    else:
        # 若无 dsn_read，依赖 libpq 免密（host/name/user）
        pool = await asyncpg.create_pool(
            host=settings.db.host,
            database=settings.db.name,
            user=settings.db.user,
            min_size=pool_min,
            max_size=pool_max,
            max_inactive_connection_lifetime=float(
                settings.db.pool.max_inactive_connection_lifetime
            ),
            timeout=float(settings.db.timeouts.connect_timeout_ms) / 1000.0,
        )
    try:
        yield pool
    finally:
        await pool.close()
