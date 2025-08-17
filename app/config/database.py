from contextlib import asynccontextmanager
import asyncpg
from app.config.settings import settings


@asynccontextmanager
async def get_ro_pool():  # 占位，后续完善类型
    pool = await asyncpg.create_pool(dsn=settings.db_url_read, min_size=1, max_size=5)
    try:
        yield pool
    finally:
        await pool.close()
