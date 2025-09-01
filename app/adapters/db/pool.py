"""
数据库连接池管理（app.adapters.db.pool）

本模块实现了基于 psycopg 的连接池管理，提供：
- 连接池的创建和管理
- 连接的获取和释放
- 连接健康检查和自动恢复
- 连接使用统计和监控
- 优雅的关闭和清理

使用方式：
1. 在应用启动时调用 initialize_pool() 初始化连接池
2. 使用 get_connection() 上下文管理器获取连接
3. 在应用关闭时调用 close_pool() 清理资源

性能特点：
- 避免频繁的连接建立和关闭
- 支持并发访问的连接复用
- 自动处理连接超时和重连
- 提供连接使用指标监控
"""

from __future__ import annotations

import logging
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator, Optional
from queue import Queue, Empty, Full
import weakref

import psycopg
from psycopg import Connection

from app.core.config.loader_new import Settings
from app.core.exceptions import DatabaseConnectionError, DatabaseError, error_handler

logger = logging.getLogger(__name__)


@dataclass
class PoolStats:
    """连接池统计信息"""

    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    average_wait_time: float = 0.0
    peak_connections: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "total_connections": self.total_connections,
            "active_connections": self.active_connections,
            "idle_connections": self.idle_connections,
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "average_wait_time": self.average_wait_time,
            "peak_connections": self.peak_connections,
            "uptime_seconds": time.time() - self.created_at,
        }


class PooledConnection:
    """池化连接包装器"""

    def __init__(self, connection: Connection, pool: "ConnectionPool"):
        self.connection = connection
        self.pool = weakref.ref(pool)  # 避免循环引用
        self.created_at = time.time()
        self.last_used = time.time()
        self.use_count = 0
        self.is_healthy = True

    def mark_used(self):
        """标记连接被使用"""
        self.last_used = time.time()
        self.use_count += 1

    def check_health(self) -> bool:
        """检查连接健康状态"""
        try:
            if self.connection.closed:
                self.is_healthy = False
                return False

            # 简单的健康检查查询
            with self.connection.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()

            self.is_healthy = True
            return True
        except Exception as e:
            logger.debug(f"连接健康检查失败: {e}")
            self.is_healthy = False
            return False

    def close(self):
        """关闭连接"""
        try:
            if not self.connection.closed:
                self.connection.close()
        except Exception as e:
            logger.debug(f"关闭连接时出错: {e}")
        finally:
            self.is_healthy = False


class ConnectionPool:
    """数据库连接池"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._pool: Queue[PooledConnection] = Queue(maxsize=settings.db.pool.max_size)
        self._all_connections: set[PooledConnection] = set()
        self._lock = threading.RLock()
        self._stats = PoolStats()
        self._closed = False

        # 从配置生成 DSN
        self._dsn = self._make_dsn()

        # 预创建最小数量的连接
        self._create_initial_connections()

    def _make_dsn(self) -> str:
        """根据配置生成 DSN"""
        db = self.settings.db
        if db.dsn_write:
            return db.dsn_write
        if db.dsn_read:
            return db.dsn_read
        return f"host={db.host} dbname={db.name} user={db.user}"

    @error_handler(context_fields=["min_size"])
    def _create_initial_connections(self):
        """创建初始连接"""
        min_size = self.settings.db.pool.min_size
        for i in range(min_size):
            try:
                conn = self._create_connection()
                if conn:
                    self._pool.put_nowait(conn)
                    logger.debug(f"预创建连接 {i+1}/{min_size}")
            except Exception as e:
                logger.warning(
                    f"预创建连接失败 {i+1}/{min_size}: {e}",
                    extra={
                        "event": "pool.initial_connection.failed",
                        "extra": {
                            "index": i + 1,
                            "min_size": min_size,
                            "error": str(e),
                        },
                    },
                )

    def _create_connection(self) -> Optional[PooledConnection]:
        """创建新的数据库连接"""
        try:
            conn = psycopg.connect(
                self._dsn,
                connect_timeout=self.settings.db.timeouts.connect_timeout_ms // 1000,
            )

            # 设置连接参数
            with conn.cursor() as cur:
                # PostgreSQL需要时间单位字符串格式
                timeout_ms = self.settings.db.timeouts.statement_timeout_ms
                cur.execute(f"SET statement_timeout TO '{timeout_ms}ms'")

            pooled_conn = PooledConnection(conn, self)

            with self._lock:
                self._all_connections.add(pooled_conn)
                self._stats.total_connections += 1
                if self._stats.total_connections > self._stats.peak_connections:
                    self._stats.peak_connections = self._stats.total_connections

            logger.debug(
                "创建新连接成功",
                extra={
                    "event": "pool.connection.created",
                    "extra": {"total_connections": self._stats.total_connections},
                },
            )

            return pooled_conn

        except Exception as e:
            logger.error(
                f"创建数据库连接失败: {e}",
                extra={
                    "event": "pool.connection.create_failed",
                    "extra": {"error": str(e), "dsn_preview": self._dsn[:50] + "..."},
                },
            )
            raise DatabaseConnectionError(
                f"无法创建数据库连接: {e}",
                context={"dsn_preview": self._dsn[:50] + "..."},
            ) from e

    @contextmanager
    def get_connection(self, timeout: Optional[float] = None) -> Iterator[Connection]:
        """
        获取数据库连接的上下文管理器

        参数：
            timeout: 获取连接的超时时间（秒），None表示使用默认超时

        用法：
            with pool.get_connection() as conn:
                # 使用连接进行数据库操作
                pass
        """
        if self._closed:
            raise DatabaseError("连接池已关闭")

        start_time = time.time()
        pooled_conn = None

        try:
            # 更新统计信息
            with self._lock:
                self._stats.total_requests += 1

            # 尝试从池中获取连接
            pooled_conn = self._get_pooled_connection(timeout)

            # 更新等待时间统计
            wait_time = time.time() - start_time
            with self._lock:
                # 简单的移动平均
                self._stats.average_wait_time = (
                    self._stats.average_wait_time * 0.9 + wait_time * 0.1
                )
                self._stats.active_connections += 1

            # 标记连接使用
            pooled_conn.mark_used()

            logger.debug(
                "获取连接成功",
                extra={
                    "event": "pool.connection.acquired",
                    "extra": {
                        "wait_time_ms": wait_time * 1000,
                        "active_connections": self._stats.active_connections,
                    },
                },
            )

            yield pooled_conn.connection

        except Exception as e:
            with self._lock:
                self._stats.failed_requests += 1

            logger.error(
                f"获取连接失败: {e}",
                extra={
                    "event": "pool.connection.acquire_failed",
                    "extra": {
                        "error": str(e),
                        "wait_time_ms": (time.time() - start_time) * 1000,
                    },
                },
            )
            raise

        finally:
            # 归还连接到池中
            if pooled_conn:
                self._return_connection(pooled_conn)

                with self._lock:
                    self._stats.active_connections = max(
                        0, self._stats.active_connections - 1
                    )

    def _get_pooled_connection(self, timeout: Optional[float]) -> PooledConnection:
        """从池中获取连接"""
        if timeout is None:
            timeout = self.settings.db.timeouts.connect_timeout_ms / 1000.0

        try:
            # 尝试从池中获取现有连接
            pooled_conn = self._pool.get(timeout=timeout)

            # 检查连接健康状态
            if pooled_conn.check_health():
                return pooled_conn
            else:
                # 连接不健康，移除并创建新连接
                self._remove_connection(pooled_conn)
                logger.debug("移除不健康的连接，创建新连接")

        except Empty:
            # 池中没有可用连接
            logger.debug("池中无可用连接，尝试创建新连接")

        # 检查是否可以创建新连接
        with self._lock:
            if len(self._all_connections) < self.settings.db.pool.max_size:
                return self._create_connection()

        # 达到最大连接数，等待现有连接释放
        try:
            pooled_conn = self._pool.get(timeout=timeout)
            if pooled_conn.check_health():
                return pooled_conn
            else:
                self._remove_connection(pooled_conn)
                raise DatabaseConnectionError("获取的连接不健康且无法创建新连接")
        except Empty:
            raise DatabaseConnectionError(f"在 {timeout} 秒内无法获取数据库连接")

    def _return_connection(self, pooled_conn: PooledConnection):
        """将连接归还到池中"""
        try:
            if not self._closed and pooled_conn.check_health():
                # 检查连接是否超过最大生存时间
                max_lifetime = self.settings.db.pool.max_inactive_connection_lifetime
                if time.time() - pooled_conn.created_at < max_lifetime:
                    self._pool.put_nowait(pooled_conn)
                    return

            # 连接不健康或超时，移除它
            self._remove_connection(pooled_conn)

        except Full:
            # 池已满，关闭连接
            self._remove_connection(pooled_conn)

    def _remove_connection(self, pooled_conn: PooledConnection):
        """从池中移除连接"""
        with self._lock:
            if pooled_conn in self._all_connections:
                self._all_connections.remove(pooled_conn)
                self._stats.total_connections -= 1

        pooled_conn.close()

    def get_stats(self) -> PoolStats:
        """获取连接池统计信息"""
        with self._lock:
            # 更新空闲连接数
            self._stats.idle_connections = self._pool.qsize()
            return PoolStats(
                total_connections=self._stats.total_connections,
                active_connections=self._stats.active_connections,
                idle_connections=self._stats.idle_connections,
                total_requests=self._stats.total_requests,
                failed_requests=self._stats.failed_requests,
                average_wait_time=self._stats.average_wait_time,
                peak_connections=self._stats.peak_connections,
                created_at=self._stats.created_at,
            )

    def close(self):
        """关闭连接池，清理所有连接"""
        if self._closed:
            return

        logger.info("正在关闭连接池...")
        self._closed = True

        # 关闭所有连接
        with self._lock:
            for pooled_conn in list(self._all_connections):
                pooled_conn.close()
            self._all_connections.clear()

        # 清空队列
        while not self._pool.empty():
            try:
                self._pool.get_nowait()
            except Empty:
                break

        logger.info(
            "连接池已关闭",
            extra={"event": "pool.closed", "extra": self.get_stats().to_dict()},
        )


# 全局连接池实例
_pool: Optional[ConnectionPool] = None
_pool_lock = threading.Lock()


def initialize_pool(settings: Settings) -> ConnectionPool:
    """
    初始化全局连接池

    参数：
        settings: 应用配置

    返回：
        连接池实例
    """
    global _pool

    with _pool_lock:
        if _pool is not None:
            logger.warning("连接池已经初始化，关闭现有连接池并重新创建")
            _pool.close()

        _pool = ConnectionPool(settings)
        logger.info(
            "连接池初始化完成",
            extra={
                "event": "pool.initialized",
                "extra": {
                    "min_size": settings.db.pool.min_size,
                    "max_size": settings.db.pool.max_size,
                },
            },
        )
        return _pool


def get_pool() -> ConnectionPool:
    """
    获取全局连接池实例

    返回：
        连接池实例

    异常：
        DatabaseError: 如果连接池未初始化
    """
    if _pool is None:
        raise DatabaseError("连接池未初始化，请先调用 initialize_pool()")
    return _pool


@contextmanager
def get_connection(timeout: Optional[float] = None) -> Iterator[Connection]:
    """
    获取数据库连接的便捷函数

    参数：
        timeout: 获取连接的超时时间（秒）

    用法：
        with get_connection() as conn:
            # 使用连接进行数据库操作
            pass
    """
    pool = get_pool()
    with pool.get_connection(timeout=timeout) as conn:
        yield conn


def close_pool():
    """关闭全局连接池"""
    global _pool

    with _pool_lock:
        if _pool is not None:
            _pool.close()
            _pool = None
            logger.info("全局连接池已关闭")


def get_pool_stats() -> dict:
    """
    获取连接池统计信息

    返回：
        统计信息字典
    """
    try:
        pool = get_pool()
        return pool.get_stats().to_dict()
    except DatabaseError:
        return {"error": "连接池未初始化"}
