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
from app.core.logging.setup import log_biz, log_sql, _global_cfg, log_db_pool
import logging

from app.core.exceptions import (
    DatabaseConnectionError,
    DatabaseError,
    DatabaseNetworkError,
    DatabaseResourceExhaustedError,
    PoolError,
    PoolExhaustedError,
    PoolShutdownError,
    PoolValidationError,
    error_handler,
)
from app.core.retry import smart_retry
from app.core.circuit_breaker import circuit_breaker
from app.core.error_analysis import error_monitor
from app.adapters.db.transaction import reset_connection_state


@dataclass
class PoolStats:
    """连接池统计信息（准确性优化版本）"""

    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    average_wait_time: float = 0.0
    peak_connections: int = 0
    created_at: float = field(default_factory=time.time)
    # 统计准确性：确保内部计数器与公开字段同步
    _wait_time_sum: float = field(default=0.0, init=False)
    _request_count: int = field(default=0, init=False)
    # 新增：统计验证字段
    _last_validation: float = field(default=0.0, init=False)
    _validation_errors: int = field(default=0, init=False)

    def update_wait_time_accurate(self, wait_time: float) -> None:
        """准确更新等待时间统计（确保计数器同步）"""
        self._wait_time_sum += wait_time
        self._request_count += 1

        # 使用简单平均而不是移动平均，减少计算开销
        if self._request_count > 0:
            self.average_wait_time = self._wait_time_sum / self._request_count

        # 确保内部计数器与公开字段同步（在计算平均值之后）
        # 只有当total_requests已经被设置时才同步
        if self.total_requests > 0 and self._request_count != self.total_requests:
            # 修正同步问题
            self._request_count = self.total_requests

    def update_wait_time_fast(self, wait_time: float) -> None:
        """快速更新等待时间统计（向后兼容）"""
        self.update_wait_time_accurate(wait_time)

    def validate_and_correct(
        self, actual_connections: int, actual_queue_size: int
    ) -> dict:
        """验证并修正统计信息准确性"""
        current_time = time.time()
        corrections = {}

        # 验证连接数准确性
        if self.total_connections != actual_connections:
            corrections["total_connections"] = {
                "old": self.total_connections,
                "new": actual_connections,
                "diff": actual_connections - self.total_connections,
            }
            self.total_connections = actual_connections
            self._validation_errors += 1

        # 验证空闲连接数
        if self.idle_connections != actual_queue_size:
            corrections["idle_connections"] = {
                "old": self.idle_connections,
                "new": actual_queue_size,
                "diff": actual_queue_size - self.idle_connections,
            }
            self.idle_connections = actual_queue_size

        # 验证活跃连接数不能为负数
        if self.active_connections < 0:
            corrections["active_connections"] = {
                "old": self.active_connections,
                "new": 0,
                '原因': "negative_value_corrected",
            }
            self.active_connections = 0
            self._validation_errors += 1

        # 验证活跃连接数不能超过总连接数
        if self.active_connections > self.total_connections:
            corrections["active_connections"] = {
                "old": self.active_connections,
                "new": max(0, self.total_connections - self.idle_connections),
                '原因': "exceeds_total_connections",
            }
            self.active_connections = max(
                0, self.total_connections - self.idle_connections
            )
            self._validation_errors += 1

        # 验证内部计数器同步
        if self._request_count != self.total_requests:
            corrections["request_count_sync"] = {
                "internal_count": self._request_count,
                "public_count": self.total_requests,
                "action": "sync_to_public",
            }
            # 只有当等待时间总和为0时才同步计数器（避免破坏已有的平均值）
            if self._wait_time_sum == 0.0:
                self._request_count = self.total_requests
            else:
                # 如果有等待时间数据，保持现有的内部计数器，只记录不一致
                pass

        self._last_validation = current_time

        if corrections:
            pass

        return corrections

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
            "validation_errors": self._validation_errors,
            "last_validation": self._last_validation,
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
        self._closed = False  # 添加关闭状态标记
        self._lock = threading.Lock()  # 添加实例级锁保护并发访问

    def mark_used(self):
        """标记连接被使用（线程安全）"""
        with self._lock:
            if self._closed:
                return
            self.last_used = time.time()
            self.use_count += 1

    def is_closed(self) -> bool:
        """线程安全地检查连接是否已关闭"""
        with self._lock:
            return self._closed

    def get_pool(self) -> Optional["ConnectionPool"]:
        """安全获取连接池引用"""
        try:
            pool = self.pool()
            if pool is None:
                pass
            return pool
        except Exception:
            pass
            return None

    def check_health(self, force_check: bool = False) -> bool:
        """检查连接健康状态（高性能优化版本）

        优化策略：
        1. 分层检查：轻量级状态检查 + 深度SQL检查
        2. 智能缓存：基于使用模式和错误历史的缓存策略
        3. 减少SQL查询：优先使用连接状态检查
        4. 动态检查频率：根据连接稳定性调整检查频率
        5. 性能监控：记录检查统计信息用于优化

        参数：
            force_check: 是否强制进行深度健康检查
        """
        from app.adapters.db.health_monitor import record_health_check

        start_time = time.time()
        current_time = start_time
        check_type = "unknown"
        success = False

        try:
            # 第一层：基础状态检查（无网络开销）
            if self.connection.closed:
                self.is_healthy = False
                self._last_health_check = current_time
                check_type = "lightweight"
                record_health_check(
                    check_type,
                    time.time() - start_time,
                    False,
                    {'原因': "connection_closed"},
                )
                return False

            # 第二层：智能缓存策略
            if not force_check:
                # 策略1：最近使用的活跃连接（高信任度）
                if current_time - self.last_used < 3.0:
                    check_type = "cached"
                    success = True
                    record_health_check(
                        check_type,
                        time.time() - start_time,
                        True,
                        {"cache_reason": "recently_used"},
                    )
                    # 连接池日志：健康检查（cached 快速路径）
                    try:
                        if _global_cfg and _global_cfg.db_pool_enabled:
                            dur_ms = int((time.time() - start_time) * 1000)
                            detail = {
                                "event": "health_check",
                                "type": check_type,
                                '耗时（毫秒）': dur_ms,
                                "result": True,
                            }
                            if _global_cfg.db_pool_include_thread:
                                import threading as _th

                                detail["threadName"] = _th.current_thread().name
                            if (
                                _global_cfg.db_pool_health_check_slow_ms
                                and dur_ms >= _global_cfg.db_pool_health_check_slow_ms
                            ):
                                detail["slow"] = True
                            log_db_pool("HEALTH_CHECK", detail, logging.INFO)
                    except Exception:
                        pass
                    return True

                # 策略2：最近检查过且健康的连接（中等信任度）
                if (
                    self.is_healthy
                    and hasattr(self, "_last_health_check")
                    and current_time - self._last_health_check < 10.0
                ):
                    check_type = "cached"
                    success = True
                    record_health_check(
                        check_type,
                        time.time() - start_time,
                        True,
                        {"cache_reason": "recently_checked"},
                    )
                    return True

                # 策略3：稳定连接的延长缓存（低频检查）
                if (
                    self.is_healthy
                    and hasattr(self, "_consecutive_healthy_checks")
                    and self._consecutive_healthy_checks >= 5
                    and hasattr(self, "_last_health_check")
                    and current_time - self._last_health_check < 30.0
                ):
                    check_type = "cached"
                    success = True
                    record_health_check(
                        check_type,
                        time.time() - start_time,
                        True,
                        {"cache_reason": "stable_connection"},
                    )
                    return True

            # 第三层：轻量级连接状态检查
            check_type = "lightweight"
            try:
                # 检查连接基本属性（无SQL查询）
                if hasattr(self.connection, "info") and self.connection.info:
                    # 检查连接信息是否可访问
                    _ = self.connection.info.host

                # 检查事务状态（无SQL查询）
                if hasattr(self.connection, "info") and hasattr(
                    self.connection.info, "transaction_status"
                ):
                    # PostgreSQL连接事务状态检查
                    status = self.connection.info.transaction_status
                    if status == 3:  # PQTRANS_INERROR
                        self.is_healthy = False
                        self._last_health_check = current_time
                        record_health_check(
                            check_type,
                            time.time() - start_time,
                            False,
                            {'原因': "transaction_error_state"},
                        )
                        return False

            except Exception as e:
                # 轻量级检查失败，标记为不健康
                if False:
                    pass
                self.is_healthy = False
                self._last_health_check = current_time
                record_health_check(
                    check_type,
                    time.time() - start_time,
                    False,
                    {'原因': "lightweight_check_failed", "error": str(e)},
                )
                return False

            # 第四层：深度SQL健康检查（仅在必要时执行）
            need_deep_check = (
                force_check
                or not self.is_healthy
                or not hasattr(self, "_last_deep_check")
                or current_time - getattr(self, "_last_deep_check", 0)
                > 60.0  # 1分钟深度检查一次
            )

            if need_deep_check:
                check_type = "deep"
                try:
                    # 使用自动提交模式进行健康检查，避免污染连接的事务状态
                    from app.adapters.db.transaction import auto_commit

                    with auto_commit(self.connection) as conn:
                        with conn.cursor() as cur:
                            # 使用更轻量的查询替代SELECT 1
                            cur.execute(
                                "SELECT current_setting('server_version_num')::int"
                            )
                            result = cur.fetchone()

                            # 验证查询结果（PostgreSQL版本号应该是正整数）
                            if (
                                not result
                                or not isinstance(result[0], int)
                                or result[0] <= 0
                            ):
                                self.is_healthy = False
                                self._reset_health_counters()
                                record_health_check(
                                    check_type,
                                    time.time() - start_time,
                                    False,
                                    {'原因': "invalid_query_result"},
                                )
                                return False

                    # 深度检查成功
                    self.is_healthy = True
                    self._last_deep_check = current_time
                    self._update_health_counters(True)
                    success = True

                except Exception as e:
                    # 深度检查失败
                    self.is_healthy = False
                    self._reset_health_counters()
                    record_health_check(
                        check_type,
                        time.time() - start_time,
                        False,
                        {'原因': "deep_check_failed", "error": str(e)},
                    )
                    return False
            else:
                # 跳过深度检查，使用轻量级检查结果
                success = True

            # 更新检查时间和计数器
            self._last_health_check = current_time
            # 连接池日志：健康检查结果（统一出口）
            try:
                if _global_cfg and _global_cfg.db_pool_enabled:
                    dur_ms = int((time.time() - start_time) * 1000)
                    detail = {
                        "event": "health_check",
                        "type": check_type,
                        '耗时（毫秒）': dur_ms,
                        "result": bool(success),
                        "pool_id": getattr(self.get_pool(), "_pool_id", None),
                    }
                    if _global_cfg.db_pool_include_thread:
                        import threading as _th

                        detail["threadName"] = _th.current_thread().name
                    if (
                        _global_cfg.db_pool_health_check_slow_ms
                        and dur_ms >= _global_cfg.db_pool_health_check_slow_ms
                    ):
                        detail["slow"] = True
                    log_db_pool(
                        "HEALTH_CHECK",
                        detail,
                        logging.INFO if success else logging.WARNING,
                    )
            except Exception:
                pass

            if self.is_healthy:
                self._update_health_counters(True)

            # 记录成功的检查
            if success and check_type != "cached":
                record_health_check(
                    check_type,
                    time.time() - start_time,
                    True,
                    {"deep_check_performed": need_deep_check},
                )

            return self.is_healthy

        except Exception:
            # 意外异常
            self.is_healthy = False
            record_health_check(
                check_type,
                time.time() - start_time,
                False,
                {'原因': "unexpected_error"},
            )
            return False

    def _update_health_counters(self, is_healthy: bool):
        """更新健康检查计数器"""
        if is_healthy:
            if not hasattr(self, "_consecutive_healthy_checks"):
                self._consecutive_healthy_checks = 0
            self._consecutive_healthy_checks += 1
            # 限制计数器最大值，避免无限增长
            if self._consecutive_healthy_checks > 10:
                self._consecutive_healthy_checks = 10
        else:
            self._reset_health_counters()

    def _reset_health_counters(self):
        """重置健康检查计数器"""
        self._consecutive_healthy_checks = 0

    def close(self):
        """关闭连接并清理资源（线程安全）"""
        with self._lock:
            if self._closed:
                return  # 避免重复关闭

            self._closed = True
            self.is_healthy = False

            # 记录关闭信息
            use_count = self.use_count
            lifetime = time.time() - self.created_at

        # 在锁外执行可能阻塞的操作
        try:
            if self.connection and not self.connection.closed:
                self.connection.close()
        except Exception:
            pass
        finally:
            # 清理引用，帮助垃圾回收
            with self._lock:
                self.connection = None
                self.pool = None

    def get_stats(self) -> dict:
        """获取连接统计信息（线程安全）"""
        with self._lock:
            return {
                "use_count": self.use_count,
                "created_at": self.created_at,
                "last_used": self.last_used,
                "is_healthy": self.is_healthy,
                "is_closed": self._closed,
                "age_seconds": time.time() - self.created_at,
                "idle_seconds": time.time() - self.last_used,
            }


class ConnectionPool:
    """数据库连接池"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._pool: Queue[PooledConnection] = Queue(maxsize=settings.db.pool.max_size)
        self._all_connections: set[PooledConnection] = set()
        self._lock = threading.RLock()
        self._stats = PoolStats()
        self._closed = False
        self._closing = False  # 添加正在关闭状态
        self._close_event = threading.Event()  # 关闭事件，用于通知等待的线程
        self._pool_id = hex(id(self))

        # 从配置生成 DSN
        self._dsn = self._make_dsn()

        # 性能优化：预计算连接参数，避免每次创建连接时重复计算
        self._connect_timeout = int(self.settings.db.timeouts.connect_timeout_seconds())
        self._statement_timeout_sql = self.settings.db.timeouts.statement_timeout_sql()
        self._connection_acquire_timeout = (
            self.settings.db.timeouts.connection_acquire_timeout_seconds()
        )
        self._connection_validation_timeout = (
            self.settings.db.timeouts.connection_validation_timeout_seconds()
        )
        self._pool_shutdown_timeout = (
            self.settings.db.timeouts.pool_shutdown_timeout_seconds()
        )

        # 预创建最小数量的连接
        self._create_initial_connections()

    def _is_available(self) -> bool:
        """检查连接池是否可用（线程安全）"""
        with self._lock:
            return not self._closed and not self._closing

    def _make_dsn(self) -> str:
        """根据配置生成 DSN"""
        db = self.settings.db
        if db.dsn_write:
            return db.dsn_write
        if db.dsn_read:
            return db.dsn_read

        # 构建 DSN 字符串，包含密码（如果有）
        dsn_parts = [f"host={db.host}", f"dbname={db.name}", f"user={db.user}"]
        if db.password:
            dsn_parts.append(f"password={db.password}")
        return " ".join(dsn_parts)

    @error_handler(context_fields=["min_size"])
    def _create_initial_connections(self):
        """创建初始连接"""
        min_size = self.settings.db.pool.min_size
        for i in range(min_size):
            try:
                conn = self._create_connection()
                if conn:
                    self._pool.put_nowait(conn)
            except Exception as e:
                pass

    @smart_retry()
    @circuit_breaker("database_connection_creation")
    @error_monitor
    def _create_connection(self) -> Optional[PooledConnection]:
        """创建新的数据库连接（性能优化版本）"""
        conn = None
        pooled_conn = None

        try:
            create_start = time.time()
            # 性能优化：使用预计算的超时值
            conn = psycopg.connect(
                self._dsn,
                connect_timeout=self._connect_timeout,
            )

            # 性能优化：使用预计算的SQL语句
            with conn.cursor() as cur:
                cur.execute(self._statement_timeout_sql)

            pooled_conn = PooledConnection(conn, self)

            # 连接池日志：创建成功（带耗时与慢标记）
            try:
                if _global_cfg and _global_cfg.db_pool_enabled:
                    dur_ms = int((time.time() - create_start) * 1000)
                    detail = {
                        "event": "create",
                        '耗时（毫秒）': dur_ms,
                        "dsn_preview": (self._dsn[:50] + "...") if self._dsn else None,
                        "pool_id": getattr(self, "_pool_id", None),
                    }
                    if _global_cfg.db_pool_include_thread:
                        detail["threadName"] = threading.current_thread().name
                    if (
                        _global_cfg.db_pool_create_slow_ms
                        and dur_ms >= _global_cfg.db_pool_create_slow_ms
                    ):
                        detail["slow"] = True
                    log_db_pool("CREATE", detail, logging.INFO)
            except Exception:
                pass

            # 原子性地添加到连接集合和更新统计
            with self._lock:
                self._all_connections.add(pooled_conn)
                self._stats.total_connections += 1
                if self._stats.total_connections > self._stats.peak_connections:
                    self._stats.peak_connections = self._stats.total_connections

            # 性能优化：只在debug模式下记录详细日志
            if False:
                pass

            return pooled_conn

        except Exception as e:
            # 异常时清理已创建的资源
            if pooled_conn is not None:
                # 如果 pooled_conn 已创建，从集合中移除
                with self._lock:
                    if pooled_conn in self._all_connections:
                        self._all_connections.remove(pooled_conn)
                        self._stats.total_connections -= 1
                # 关闭 pooled_conn
                pooled_conn.close()
            elif conn is not None:
                # 如果只有原始连接被创建，直接关闭
                try:
                    conn.close()
                except Exception:
                    pass  # 忽略关闭时的异常

            # 连接创建失败（日志已移除）
            # 根据异常类型抛出更具体的错误
            if "network" in str(e).lower() or "connection refused" in str(e).lower():
                raise DatabaseNetworkError(
                    f"网络连接失败: {e}",
                    context={"dsn_preview": self._dsn[:50] + "..."},
                ) from e
            elif "authentication" in str(e).lower() or "password" in str(e).lower():
                raise DatabaseConnectionError(
                    f"数据库认证失败: {e}",
                    context={"dsn_preview": self._dsn[:50] + "..."},
                ) from e
            else:
                raise DatabaseConnectionError(
                    f"无法创建数据库连接: {e}",
                    context={"dsn_preview": self._dsn[:50] + "..."},
                ) from e

    @contextmanager
    def get_connection(self, timeout: Optional[float] = None) -> Iterator[Connection]:
        """
        获取数据库连接的上下文管理器（线程安全）

        参数：
            timeout: 获取连接的超时时间（秒），None表示使用默认超时

        用法：
            with pool.get_connection() as conn:
                # 使用连接进行数据库操作
                pass
        """
        # 原子性地检查连接池状态
        if not self._is_available():
            if self._closed:
                raise DatabaseError("连接池已关闭")
            elif self._closing:
                raise DatabaseError("连接池正在关闭，无法获取新连接")

            # 连接池日志：获取开始（记录开始时间）
            acquire_start = time.time()

        start_time = time.time()
        pooled_conn = None

        try:
            # 原子性地更新统计信息
            with self._lock:
                if not self._is_available():
                    raise DatabaseError("连接池在获取过程中被关闭")
                self._stats.total_requests += 1

            # 尝试从池中获取连接
            pooled_conn = self._get_pooled_connection(timeout)

            # 准确性优化：使用准确统计更新
            wait_time = time.time() - start_time
            # 使用准确的等待时间统计方法
            with self._lock:
                self._stats.update_wait_time_accurate(wait_time)
                self._stats.active_connections += 1
            # 连接池日志：获取成功（使用 wait_time 统计）
            try:
                if _global_cfg and _global_cfg.db_pool_enabled:
                    dur_ms = int(wait_time * 1000)
                    detail = {
                        "event": "acquire",
                        "wait_ms": dur_ms,
                        "active": self._stats.active_connections,
                        "total": self._stats.total_connections,
                        "idle": self._stats.idle_connections,
                    }
                    if _global_cfg.db_pool_include_thread:
                        import threading as _th

                        detail["threadName"] = _th.current_thread().name
                    if (
                        _global_cfg.db_pool_acquire_slow_ms
                        and dur_ms >= _global_cfg.db_pool_acquire_slow_ms
                    ):
                        detail["slow"] = True
                    log_db_pool("ACQUIRE", detail, logging.INFO)
            except Exception:
                pass

            # 标记连接使用
            pooled_conn.mark_used()

            # 性能优化：只在debug模式下记录详细日志
            # （日志已移除）
            yield pooled_conn.connection

        except Exception as e:
            # 原子性地更新失败统计
            with self._lock:
                self._stats.failed_requests += 1

            raise

        finally:
            # 归还连接到池中
            if pooled_conn:
                self._return_connection(pooled_conn)

                # 原子性地更新活跃连接数
                with self._lock:
                    self._stats.active_connections = max(
                        0, self._stats.active_connections - 1
                    )

    def _get_pooled_connection(self, timeout: Optional[float]) -> PooledConnection:
        """从池中获取连接（线程安全）"""
        if timeout is None:
            timeout = self._connection_acquire_timeout

        # 首次尝试：从池中获取现有连接
        try:
            pooled_conn = self._pool.get(timeout=min(timeout, 0.1))  # 短超时，快速失败

            # 检查连接健康状态和状态一致性
            if self._validate_pooled_connection(pooled_conn):
                return pooled_conn
            else:
                # 连接不健康或状态不一致，移除并继续尝试
                self._remove_connection(pooled_conn)

        except Empty:
            # 池中没有可用连接，继续下一步
            pass

        # 第二次尝试：创建新连接（如果未达到最大连接数）
        can_create_new = False
        with self._lock:
            if not self._is_available():
                raise DatabaseError("连接池在获取连接过程中被关闭")

            if len(self._all_connections) < self.settings.db.pool.max_size:
                can_create_new = True

        if can_create_new:
            try:
                new_conn = self._create_connection()
                if new_conn:
                    return new_conn
            except Exception as e:
                pass

        # 第三次尝试：等待现有连接释放
        remaining_timeout = max(0, timeout - 0.1)  # 减去之前的等待时间
        if remaining_timeout > 0:
            try:
                pooled_conn = self._pool.get(timeout=remaining_timeout)
                if self._validate_pooled_connection(pooled_conn):
                    return pooled_conn
                else:
                    self._remove_connection(pooled_conn)
                    raise DatabaseConnectionError("获取的连接不健康且无法创建新连接")
            except Empty:
                pass

        # 所有尝试都失败，抛出连接池耗尽错误
        raise PoolExhaustedError(
            f"连接池耗尽：在 {timeout} 秒内无法获取数据库连接",
            context={
                "timeout": timeout,
                "pool_size": len(self._all_connections),
                "max_size": self.settings.db.pool.max_size,
                "active_connections": self._stats.active_connections,
            },
        )

    def _validate_pooled_connection(self, pooled_conn: PooledConnection) -> bool:
        """验证池化连接的健康状态和状态一致性（高性能版本）"""
        try:
            current_time = time.time()

            # 第一层：快速路径 - 最近活跃的连接
            if current_time - pooled_conn.last_used < 1.0:
                # 1秒内使用的连接直接认为健康，跳过所有检查
                return True

            # 第二层：轻量级健康检查（优先使用缓存）
            if not pooled_conn.check_health(force_check=False):
                return False

            # 第三层：状态一致性验证（仅对长时间未使用的连接）
            if current_time - pooled_conn.last_used > 60.0:  # 1分钟未使用才进行详细验证
                # 连接状态验证
                from app.adapters.db.transaction import validate_connection_state

                state = validate_connection_state(pooled_conn.connection)

                if not state["healthy"]:
                    return False

                # 验证连接是否处于预期的自动提交状态
                if not pooled_conn.connection.autocommit:
                    return False

            return True

        except Exception as e:
            if True:
                pass
            return False

    def _return_connection(self, pooled_conn: PooledConnection):
        """将连接归还到池中（线程安全）"""
        if pooled_conn is None:
            return

        try:
            # 检查连接池和连接状态
            pool_available = self._is_available()
            connection_healthy = False
            # 连接池日志：RELEASE 前的健康状态
            try:
                if _global_cfg and _global_cfg.db_pool_enabled:
                    detail = {
                        "event": "release_pre",
                        "pool_id": getattr(self, "_pool_id", None),
                        "connection_healthy": connection_healthy,
                    }
                    log_db_pool("RELEASE", detail, logging.DEBUG)
            except Exception:
                pass

            if pool_available and not pooled_conn.is_closed():
                try:
                    connection_healthy = pooled_conn.check_health()
                except Exception:
                    connection_healthy = False

            if pool_available and connection_healthy:
                # 调试日志：记录重置前的连接状态
                try:
                    if _global_cfg and _global_cfg.db_pool_enabled:
                        detail = {
                            "event": "before_reset",
                            '事务状态': str(pooled_conn.connection.info.transaction_status),
                            '自动提交': pooled_conn.connection.autocommit,
                        }
                        log_db_pool("RESET_STATE", detail, logging.DEBUG)
                except Exception:
                    pass

                # 重置连接状态，确保连接处于干净状态
                try:
                    reset_connection_state(pooled_conn.connection)
                except Exception:
                    self._remove_connection(pooled_conn)
                    return

                # 检查连接是否超过最大生存时间
                max_lifetime = self.settings.db.pool.max_inactive_connection_lifetime
                if time.time() - pooled_conn.created_at < max_lifetime:
                    try:
                        self._pool.put_nowait(pooled_conn)
                        # 连接池日志：RELEASE（可选采样）
                        try:
                            if _global_cfg and _global_cfg.db_pool_enabled:
                                detail = {
                                    "event": "release",
                                    "use_count": pooled_conn.use_count,
                                    "age_ms": int(
                                        (time.time() - pooled_conn.created_at) * 1000
                                    ),
                                    "idle_ms": int(
                                        (time.time() - pooled_conn.last_used) * 1000
                                    ),
                                    "pool_id": getattr(self, "_pool_id", None),
                                }
                                if _global_cfg.db_pool_include_thread:
                                    import threading as _th

                                    detail["threadName"] = _th.current_thread().name
                                log_db_pool("RELEASE", detail, logging.INFO)
                        except Exception:
                            pass
                        return
                    except Full:
                        # 池已满，移除连接
                        self._remove_connection(pooled_conn)
                        return
                else:
                    # 超过最大生存时间，移除连接
                    self._remove_connection(pooled_conn)
                    return

            # 连接不健康、超时或连接池不可用，移除连接
            self._remove_connection(pooled_conn)

        except Exception:
            # 发生异常时，安全地移除连接
            try:
                self._remove_connection(pooled_conn)
            except Exception:
                pass

    def _remove_connection(self, pooled_conn: PooledConnection):
        """从池中移除连接"""
        with self._lock:
            if pooled_conn in self._all_connections:
                self._all_connections.remove(pooled_conn)
                self._stats.total_connections -= 1

        pooled_conn.close()

    def get_stats(self) -> PoolStats:
        """获取连接池统计信息（带准确性验证）"""
        with self._lock:
            # 获取实际状态用于验证
            actual_connections = len(self._all_connections)
            actual_queue_size = self._pool.qsize()

            # 验证并修正统计信息
            corrections = self._stats.validate_and_correct(
                actual_connections, actual_queue_size
            )

            # 如果有修正，记录详细信息
            if corrections and False:
                pass

            # 创建返回的统计信息副本
            stats_copy = PoolStats(
                total_connections=self._stats.total_connections,
                active_connections=self._stats.active_connections,
                idle_connections=self._stats.idle_connections,
                total_requests=self._stats.total_requests,
                failed_requests=self._stats.failed_requests,
                average_wait_time=self._stats.average_wait_time,
                peak_connections=self._stats.peak_connections,
                created_at=self._stats.created_at,
            )

            # 复制内部字段
            stats_copy._wait_time_sum = self._stats._wait_time_sum
            stats_copy._request_count = self._stats._request_count
            stats_copy._last_validation = self._stats._last_validation
            stats_copy._validation_errors = self._stats._validation_errors

            return stats_copy

    @error_monitor
    def close(self, timeout: float = 30.0):
        """优雅关闭连接池，清理所有连接（线程安全）

        参数：
            timeout: 等待活跃连接完成的超时时间（秒）
        """
        with self._lock:
            if self._closed:
                return

            # 设置正在关闭状态，阻止新的连接请求
            self._closing = True

        # 获取关闭前的统计信息
        final_stats = self.get_stats().to_dict()
        # 连接池日志：CLOSE 开始
        try:
            if _global_cfg and _global_cfg.db_pool_enabled:
                detail = {
                    "event": "close_begin",
                    "pool_id": getattr(self, "_pool_id", None),
                    "active": self._stats.active_connections,
                    "idle": self._stats.idle_connections,
                    "total": self._stats.total_connections,
                }
                log_db_pool("CLOSE", detail, logging.INFO)
        except Exception:
            pass

        # 等待活跃连接完成
        start_time = time.time()
        # 连接池日志：CLOSE 结束（统计与耗时）
        try:
            if _global_cfg and _global_cfg.db_pool_enabled:
                duration_ms = int((time.time() - start_time) * 1000)
                detail = {
                    "event": "close_end",
                    "pool_id": getattr(self, "_pool_id", None),
                    '耗时（毫秒）': duration_ms,
                    "active": self._stats.active_connections,
                    "idle": self._stats.idle_connections,
                    "total": self._stats.total_connections,
                }
                log_db_pool("CLOSE", detail, logging.INFO)
        except Exception:
            pass

        while time.time() - start_time < timeout:
            with self._lock:
                if self._stats.active_connections == 0:
                    break

            time.sleep(0.1)

        # 设置最终关闭标志
        with self._lock:
            self._closed = True
            self._close_event.set()  # 通知等待的线程

        # 强制关闭所有连接
        closed_count = 0
        leaked_connections = []

        with self._lock:
            # 记录可能泄漏的连接
            for pooled_conn in self._all_connections:
                if pooled_conn.use_count > 0 and not pooled_conn.is_closed():
                    leaked_connections.append(
                        {
                            "use_count": pooled_conn.use_count,
                            "created_at": pooled_conn.created_at,
                            "last_used": pooled_conn.last_used,
                            "age_seconds": time.time() - pooled_conn.created_at,
                        }
                    )

            # 关闭所有连接
            for pooled_conn in list(self._all_connections):
                try:
                    pooled_conn.close()
                    closed_count += 1
                except Exception as e:
                    pass

            self._all_connections.clear()

        # 清空队列并关闭队列中的连接
        queue_closed_count = 0
        while not self._pool.empty():
            try:
                pooled_conn = self._pool.get_nowait()
                if pooled_conn and not pooled_conn._closed:
                    pooled_conn.close()
                    queue_closed_count += 1
            except Empty:
                break
            except Exception as e:
                pass

        # 重置统计信息
        self._reset_stats()

        # 记录关闭信息
        close_info = {
            "closed_connections": closed_count,
            "queue_connections": queue_closed_count,
            "leaked_connections": len(leaked_connections),
            "final_stats": final_stats,
        }

        if leaked_connections:
            pass

        # 连接池日志：CLOSE 完成详情
        try:
            if _global_cfg and _global_cfg.db_pool_enabled:
                detail = {
                    "event": "close_summary",
                    "pool_id": getattr(self, "_pool_id", None),
                    **close_info,
                }
                log_db_pool("CLOSE", detail, logging.INFO)
        except Exception:
            pass

    def _reset_stats(self):
        """重置统计信息（准确性优化版本）"""
        with self._lock:
            # 重置连接状态统计
            self._stats.total_connections = 0
            self._stats.active_connections = 0
            self._stats.idle_connections = 0

            # 保留累计统计信息，只重置当前状态
            # total_requests, failed_requests, average_wait_time, peak_connections 保持不变

            # 重置验证相关字段
            self._stats._last_validation = time.time()

    def diagnose_memory_leaks(self) -> dict:
        """诊断内存泄漏风险"""
        with self._lock:
            current_time = time.time()
            diagnosis = {
                "total_connections": len(self._all_connections),
                "queue_size": self._pool.qsize(),
                "active_connections": self._stats.active_connections,
                "potential_leaks": [],
                "long_lived_connections": [],
                "high_usage_connections": [],
                "recommendations": [],
            }

            # 检查可能的泄漏连接
            for pooled_conn in self._all_connections:
                conn_age = current_time - pooled_conn.created_at
                idle_time = current_time - pooled_conn.last_used

                # 检查长期存活的连接
                if conn_age > 3600:  # 超过1小时
                    diagnosis["long_lived_connections"].append(
                        {
                            "age_seconds": conn_age,
                            "idle_seconds": idle_time,
                            "use_count": pooled_conn.use_count,
                            "is_healthy": pooled_conn.is_healthy,
                        }
                    )

                # 检查高使用频率的连接
                if pooled_conn.use_count > 1000:
                    diagnosis["high_usage_connections"].append(
                        {
                            "use_count": pooled_conn.use_count,
                            "age_seconds": conn_age,
                            "uses_per_hour": (
                                pooled_conn.use_count / (conn_age / 3600)
                                if conn_age > 0
                                else 0
                            ),
                        }
                    )

                # 检查可能泄漏的连接（长时间未归还）
                if (
                    hasattr(pooled_conn, "_in_use")
                    and pooled_conn._in_use
                    and idle_time > 300
                ):  # 5分钟
                    diagnosis["potential_leaks"].append(
                        {
                            "idle_seconds": idle_time,
                            "use_count": pooled_conn.use_count,
                            "age_seconds": conn_age,
                        }
                    )

            # 生成建议
            if len(diagnosis.get("long_lived_connections", [])) > 0:
                diagnosis["recommendations"] = diagnosis.get("recommendations", [])
                diagnosis["recommendations"].append(
                    "考虑降低 max_inactive_connection_lifetime 设置"
                )

            if len(diagnosis["potential_leaks"]) > 0:
                diagnosis["recommendations"].append(
                    "检查应用代码是否正确使用 with 语句管理连接"
                )

            if diagnosis["total_connections"] > self.settings.db.pool.max_size * 0.8:
                diagnosis["recommendations"].append(
                    "连接池使用率较高，考虑增加 max_size"
                )

            return diagnosis

    def force_cleanup(self) -> dict:
        """强制清理可能泄漏的资源"""
        if self._closed:
            return {"error": "连接池已关闭"}

        cleanup_result = {"cleaned_connections": 0, "failed_cleanups": 0, "errors": []}

        current_time = time.time()
        connections_to_remove = []

        with self._lock:
            for pooled_conn in list(self._all_connections):
                should_remove = False

                # 移除不健康的连接
                if not pooled_conn.is_healthy:
                    should_remove = True

                # 移除超过最大生存时间的连接
                max_lifetime = self.settings.db.pool.max_inactive_connection_lifetime
                if current_time - pooled_conn.created_at > max_lifetime:
                    should_remove = True

                # 移除长时间空闲的连接
                if current_time - pooled_conn.last_used > 1800:  # 30分钟
                    should_remove = True

                if should_remove:
                    connections_to_remove.append(pooled_conn)

        # 清理标记的连接
        for pooled_conn in connections_to_remove:
            try:
                self._remove_connection(pooled_conn)
                cleanup_result["cleaned_connections"] += 1
            except Exception as e:
                cleanup_result["failed_cleanups"] += 1
                cleanup_result["errors"].append(str(e))

        return cleanup_result


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
    log_db_pool("INITIALIZE", {"event": "init_start"}, logging.INFO)

    global _pool

    with _pool_lock:
        if _pool is not None:
            _pool.close()

        # 初始化错误处理机制
        from app.core.error_handling_manager import initialize_error_handling

        error_handling_success = initialize_error_handling(settings=settings)
        if not error_handling_success:
            pass

        _pool = ConnectionPool(settings)

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

        # 关闭错误处理机制
        from app.core.error_handling_manager import shutdown_error_handling

        shutdown_error_handling()


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


def diagnose_memory_leaks() -> dict:
    """
    诊断连接池内存泄漏风险

    返回：
        诊断结果字典
    """
    try:
        pool = get_pool()
        return pool.diagnose_memory_leaks()
    except DatabaseError:
        return {"error": "连接池未初始化"}


def force_cleanup_connections() -> dict:
    """
    强制清理可能泄漏的连接

    返回：
        清理结果字典
    """
    try:
        pool = get_pool()
        return pool.force_cleanup()
    except DatabaseError:
        return {"error": "连接池未初始化"}
