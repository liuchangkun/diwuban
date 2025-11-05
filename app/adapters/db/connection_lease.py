"""
连接租借管理器（app.adapters.db.connection_lease）

本模块实现了数据库连接的租借机制，用于优化长时间运行的批量操作：
- 连接租借和自动释放
- 批量操作分片处理
- 连接使用时间限制
- 连接池耗尽预防

使用方式：
1. 使用 ConnectionLease 进行长时间操作的连接管理
2. 使用 batch_operation 装饰器自动分片批量操作
3. 使用 lease_connection 上下文管理器进行连接租借

设计原则：
- 防止连接长时间占用
- 自动分片大批量操作
- 监控连接池使用情况
- 提供优雅的连接释放机制
"""

from __future__ import annotations

import time
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Optional, Callable, Any, TypeVar, Generic
from functools import wraps

import psycopg
from psycopg import Connection

from app.core.config.loader_new import Settings


import logging

_act = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class LeaseConfig:
    """连接租借配置"""

    max_lease_time: float = 300.0  # 最大租借时间（秒），默认5分钟
    renewal_threshold: float = 0.8  # 续租阈值（租借时间的80%时自动续租）
    batch_size: int = 1000  # 批量操作的默认批次大小
    max_batch_time: float = 30.0  # 单个批次的最大执行时间（秒）
    pool_usage_threshold: float = 0.8  # 连接池使用率阈值


class ConnectionLease:
    """连接租借管理器"""

    def __init__(self, settings: Settings, config: Optional[LeaseConfig] = None):
        self.settings = settings
        self.config = config or LeaseConfig()
        self._lease_start_time: Optional[float] = None
        self._current_connection: Optional[Connection] = None
        self._lock = threading.Lock()

    def _get_connection(self) -> Connection:
        """获取新的数据库连接"""
        from app.adapters.db import get_connection

        _act.info("[核心-连接] [租借连接开始]")

        # 检查连接池使用情况
        self._check_pool_usage()

        # 获取连接的上下文管理器
        conn_manager = get_connection()
        conn = conn_manager.__enter__()

        # 保存连接管理器的退出方法，用于后续清理
        self._conn_exit = conn_manager.__exit__

        _act.info("[核心-连接] [租借连接成功]")

        return conn

    def _check_pool_usage(self):
        """检查连接池使用情况，防止耗尽"""
        try:
            from app.adapters.db.pool import get_pool_stats

            stats = get_pool_stats()

            if (
                isinstance(stats, dict)
                and "active_connections" in stats
                and "max_size" in stats
            ):
                usage_ratio = stats["active_connections"] / stats["max_size"]

                if usage_ratio > self.config.pool_usage_threshold:

                    # 如果使用率过高，稍微等待一下
                    if usage_ratio > 0.9:
                        time.sleep(0.1)

        except Exception:
            pass

    def _should_renew_lease(self) -> bool:
        """检查是否需要续租连接"""
        if self._lease_start_time is None:
            return False

        elapsed = time.time() - self._lease_start_time
        return elapsed >= (self.config.max_lease_time * self.config.renewal_threshold)

    def _renew_lease(self):
        """续租连接（释放当前连接并获取新连接）"""
        with self._lock:
            if self._current_connection is not None:
                try:
                    # 释放当前连接
                    self._conn_exit(None, None, None)
                except Exception:
                    pass

                # 获取新连接
                self._current_connection = self._get_connection()
                self._lease_start_time = time.time()

    @contextmanager
    def get_connection(self) -> Iterator[Connection]:
        """获取租借的连接"""
        with self._lock:
            if self._current_connection is None:
                self._current_connection = self._get_connection()
                self._lease_start_time = time.time()

        try:
            # 检查是否需要续租
            if self._should_renew_lease():
                self._renew_lease()

            yield self._current_connection

        except Exception:
            raise

    def close(self):
        """关闭租借管理器，释放连接"""
        with self._lock:
            if self._current_connection is not None:
                try:
                    self._conn_exit(None, None, None)
                except Exception:
                    raise
                finally:
                    self._current_connection = None
                    self._lease_start_time = None


@contextmanager
def lease_connection(
    settings: Settings, config: Optional[LeaseConfig] = None
) -> Iterator[ConnectionLease]:
    """
    连接租借上下文管理器

    参数：
        settings: 应用设置
        config: 租借配置

    用法：
        with lease_connection(settings) as lease:
            for batch in batches:
                with lease.get_connection() as conn:
                    # 执行批量操作
                    process_batch(conn, batch)
    """
    lease = ConnectionLease(settings, config)
    try:
        yield lease
    finally:
        lease.close()


def batch_operation(
    batch_size: Optional[int] = None,
    max_batch_time: Optional[float] = None,
    lease_config: Optional[LeaseConfig] = None,
):
    """
    批量操作装饰器，自动分片大批量操作

    参数：
        batch_size: 批次大小
        max_batch_time: 单个批次最大执行时间
        lease_config: 连接租借配置

    用法：
        @batch_operation(batch_size=500)
        def process_large_dataset(conn, data_items):
            # 这个函数会被自动分片执行
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 提取连接和数据参数
            conn = args[0] if args else None
            if not isinstance(conn, Connection):
                # 如果第一个参数不是连接，直接调用原函数
                return func(*args, **kwargs)

            # 提取数据参数（假设是第二个参数）
            data = args[1] if len(args) > 1 else None
            if not hasattr(data, "__iter__") or isinstance(data, (str, bytes)):
                # 如果数据不可迭代或是字符串，直接调用原函数
                return func(*args, **kwargs)

            # 配置批次参数
            config = lease_config or LeaseConfig()
            effective_batch_size = batch_size or config.batch_size
            effective_max_time = max_batch_time or config.max_batch_time

            # 分批处理
            data_list = list(data)
            total_processed = 0

            for i in range(0, len(data_list), effective_batch_size):
                batch_start_time = time.time()
                batch_data = data_list[i : i + effective_batch_size]

                # 构造新的参数列表，替换数据参数
                new_args = list(args)
                new_args[1] = batch_data

                try:
                    # 执行批次操作
                    result = func(*new_args, **kwargs)
                    batch_time = time.time() - batch_start_time
                    total_processed += len(batch_data)

                    # 检查批次执行时间
                    if batch_time > effective_max_time:
                        pass

                except Exception:
                    raise

            return total_processed

        return wrapper

    return decorator
