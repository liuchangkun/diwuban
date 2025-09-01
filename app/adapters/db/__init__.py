"""
数据库适配器模块初始化（app.adapters.db）

本模块提供数据库相关的适配器功能：
- 连接池管理和初始化
- 数据库网关操作
- 统一的数据库访问接口

使用方式：
1. 在应用启动时调用 init_database(settings) 初始化连接池
2. 使用 get_connection() 获取数据库连接
3. 在应用关闭时调用 cleanup_database() 清理资源

示例：
    from app.adapters.db import init_database, get_connection, cleanup_database
    from app.core.config.loader import load_settings

    # 应用启动
    settings = load_settings()
    init_database(settings)

    # 使用连接
    with get_connection() as conn:
        # 数据库操作
        pass

    # 应用关闭
    cleanup_database()
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator, Optional

import psycopg

from app.core.config.loader_new import Settings
from app.core.exceptions import DatabaseError, error_handler

logger = logging.getLogger(__name__)

# 连接池状态标记
_pool_initialized = False


@error_handler(context_fields=["settings"])
def init_database(settings: Settings) -> None:
    """
    初始化数据库连接池

    参数：
        settings: 应用配置

    异常：
        DatabaseError: 初始化失败时抛出
    """
    global _pool_initialized

    if _pool_initialized:
        logger.warning("数据库连接池已经初始化，跳过重复初始化")
        return

    try:
        from app.adapters.db.pool import initialize_pool

        # 初始化连接池
        pool = initialize_pool(settings)

        # 验证连接池是否正常工作
        with pool.get_connection(timeout=5.0) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 as connectivity_test")
                result = cur.fetchone()
                if not result or result[0] != 1:
                    raise DatabaseError("连接池验证失败：无法执行测试查询")

        _pool_initialized = True

        logger.info(
            "数据库连接池初始化成功",
            extra={
                "event": "db.init.success",
                "extra": {
                    "min_size": settings.db.pool.min_size,
                    "max_size": settings.db.pool.max_size,
                    "host": settings.db.host,
                    "database": settings.db.name,
                },
            },
        )

    except Exception as e:
        logger.error(
            f"数据库连接池初始化失败: {e}",
            extra={
                "event": "db.init.failed",
                "extra": {
                    "error": str(e),
                    "host": settings.db.host,
                    "database": settings.db.name,
                },
            },
            exc_info=True,
        )
        raise DatabaseError(f"数据库初始化失败: {e}") from e


def cleanup_database() -> None:
    """
    清理数据库资源，关闭连接池
    """
    global _pool_initialized

    if not _pool_initialized:
        logger.debug("数据库连接池未初始化，无需清理")
        return

    try:
        from app.adapters.db.pool import close_pool

        close_pool()
        _pool_initialized = False

        logger.info("数据库连接池已清理", extra={"event": "db.cleanup.success"})

    except Exception as e:
        logger.error(
            f"数据库清理失败: {e}",
            extra={"event": "db.cleanup.failed", "extra": {"error": str(e)}},
        )


def is_initialized() -> bool:
    """
    检查数据库连接池是否已初始化

    返回：
        bool: 是否已初始化
    """
    return _pool_initialized


@contextmanager
def get_connection(timeout: Optional[float] = None) -> Iterator[psycopg.Connection]:
    """
    获取数据库连接的便捷函数

    这是一个统一的连接获取接口，会根据初始化状态自动选择：
    - 如果连接池已初始化，使用连接池
    - 如果连接池未初始化，抛出错误提示

    参数：
        timeout: 获取连接的超时时间（秒）

    用法：
        with get_connection() as conn:
            # 使用连接进行数据库操作
            pass

    异常：
        DatabaseError: 如果连接池未初始化或获取连接失败
    """
    if not _pool_initialized:
        raise DatabaseError("数据库连接池未初始化，请先调用 init_database(settings)")

    try:
        from app.adapters.db.pool import get_connection as pool_get_connection

        with pool_get_connection(timeout=timeout) as conn:
            yield conn

    except Exception as e:
        logger.error(
            f"获取数据库连接失败: {e}",
            extra={
                "event": "db.connection.get_failed",
                "extra": {"error": str(e), "timeout": timeout},
            },
        )
        raise DatabaseError(f"获取数据库连接失败: {e}") from e


def get_pool_stats() -> dict:
    """
    获取连接池统计信息

    返回：
        dict: 包含连接池统计信息的字典
    """
    if not _pool_initialized:
        return {"error": "连接池未初始化"}

    try:
        from app.adapters.db.pool import get_pool_stats

        return get_pool_stats()
    except Exception as e:
        logger.warning(f"获取连接池统计信息失败: {e}")
        return {"error": str(e)}


# 向后兼容的导入
try:
    from app.adapters.db.gateway import (
        get_conn,
        make_dsn,
        create_staging_if_not_exists,
        copy_valid_rows,
        copy_valid_lines,
        insert_rejects,
        count_tz_fallback,
    )

    # 导出公共接口
    __all__ = [
        # 初始化和清理
        "init_database",
        "cleanup_database",
        "is_initialized",
        # 连接管理
        "get_connection",
        "get_pool_stats",
        # 网关操作（向后兼容）
        "get_conn",
        "make_dsn",
        "create_staging_if_not_exists",
        "copy_valid_rows",
        "copy_valid_lines",
        "insert_rejects",
        "count_tz_fallback",
    ]

except ImportError as e:
    logger.warning(f"导入数据库网关模块失败: {e}")

    # 最小导出
    __all__ = [
        "init_database",
        "cleanup_database",
        "is_initialized",
        "get_connection",
        "get_pool_stats",
    ]
