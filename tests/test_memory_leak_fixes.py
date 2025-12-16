"""
内存泄漏修复测试
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
import psycopg

from app.adapters.db.pool import (
    PooledConnection,
    ConnectionPool,
    diagnose_memory_leaks,
    force_cleanup_connections,
)
from app.core.circuit_breaker import get_circuit_breaker


class TestMemoryLeakFixes:
    """测试内存泄漏修复功能"""

    @pytest.fixture(autouse=True)
    def reset_circuit_breakers(self):
        """每个测试后重置circuit breaker状态，确保测试隔离"""
        yield
        # 测试后清理：重置数据库连接创建的circuit breaker
        breaker = get_circuit_breaker("database_connection_creation")
        if breaker:
            breaker.reset()

    def test_pooled_connection_close_cleanup(self):
        """测试PooledConnection关闭时的资源清理"""
        # 创建Mock连接和连接池
        mock_conn = Mock()
        mock_conn.closed = False
        mock_pool = Mock()

        # 创建PooledConnection
        pooled_conn = PooledConnection(mock_conn, mock_pool)

        # 验证初始状态
        assert not pooled_conn._closed
        assert pooled_conn.connection is not None
        assert pooled_conn.pool is not None

        # 关闭连接
        pooled_conn.close()

        # 验证资源被清理
        assert pooled_conn._closed
        assert not pooled_conn.is_healthy
        assert pooled_conn.connection is None
        assert pooled_conn.pool is None

        # 验证数据库连接被关闭
        mock_conn.close.assert_called_once()

    def test_pooled_connection_double_close(self):
        """测试PooledConnection重复关闭的安全性"""
        mock_conn = Mock()
        mock_conn.closed = False
        mock_pool = Mock()

        pooled_conn = PooledConnection(mock_conn, mock_pool)

        # 第一次关闭
        pooled_conn.close()

        # 第二次关闭应该安全（不抛异常）
        pooled_conn.close()

        # 验证数据库连接只被关闭一次
        mock_conn.close.assert_called_once()

    def test_pooled_connection_weak_reference_handling(self):
        """测试弱引用的正确处理"""
        mock_conn = Mock()
        mock_conn.closed = False
        mock_pool = Mock()

        pooled_conn = PooledConnection(mock_conn, mock_pool)

        # 测试正常的池引用获取
        pool_ref = pooled_conn.get_pool()
        assert pool_ref is mock_pool

        # 模拟池被垃圾回收
        pooled_conn.pool = lambda: None
        pool_ref = pooled_conn.get_pool()
        assert pool_ref is None

    def test_connection_pool_close_with_leak_detection(self):
        """测试连接池关闭时的泄漏检测"""
        # 创建Mock设置
        mock_settings = Mock()
        mock_settings.db.pool.min_size = 1
        mock_settings.db.pool.max_size = 5
        mock_settings.db.pool.max_inactive_connection_lifetime = 3600
        mock_settings.db.timeouts.connect_timeout_ms = 5000
        mock_settings.db.timeouts.statement_timeout_ms = 30000
        mock_settings.db.dsn_write = "postgresql://test"
        mock_settings.db.dsn_read = None
        mock_settings.db.host = "localhost"
        mock_settings.db.name = "test"
        mock_settings.db.user = "test"
        mock_settings.db.password = None

        # 创建连接池但不初始化连接
        with patch("app.adapters.db.pool.psycopg.connect"):
            pool = ConnectionPool.__new__(ConnectionPool)
            pool.settings = mock_settings
            pool._pool = Mock()
            pool._pool.qsize.return_value = 0
            pool._pool.empty.return_value = True
            pool._all_connections = set()
            pool._lock = threading.RLock()
            # 创建真实的PoolStats对象
            from app.adapters.db.pool import PoolStats

            pool._stats = PoolStats()
            pool._stats.total_connections = 2
            pool._stats.active_connections = 0
            pool._stats.idle_connections = 2
            pool._closed = False
            pool._closing = False  # 添加正在关闭状态
            pool._close_event = threading.Event()  # 添加关闭事件

            # 添加一些模拟的连接
            mock_conn1 = Mock()
            mock_conn1.closed = False
            pooled_conn1 = PooledConnection(mock_conn1, pool)
            pooled_conn1.use_count = 5
            pooled_conn1.created_at = time.time() - 100
            pooled_conn1.last_used = time.time() - 50

            mock_conn2 = Mock()
            mock_conn2.closed = False
            pooled_conn2 = PooledConnection(mock_conn2, pool)
            pooled_conn2.use_count = 10
            pooled_conn2.created_at = time.time() - 200
            pooled_conn2.last_used = time.time() - 10

            pool._all_connections.add(pooled_conn1)
            pool._all_connections.add(pooled_conn2)

            # 关闭连接池
            pool.close()

            # 验证连接被关闭
            assert pooled_conn1._closed
            assert pooled_conn2._closed
            assert len(pool._all_connections) == 0

    def test_memory_leak_diagnosis(self):
        """测试内存泄漏诊断功能"""
        mock_settings = Mock()
        mock_settings.db.pool.max_size = 10
        mock_settings.db.pool.max_inactive_connection_lifetime = 3600

        # 创建连接池
        pool = ConnectionPool.__new__(ConnectionPool)
        pool.settings = mock_settings
        pool._pool = Mock()
        pool._pool.qsize.return_value = 2
        pool._all_connections = set()
        pool._lock = threading.RLock()
        pool._stats = Mock()
        pool._stats.active_connections = 3
        pool._closed = False

        # 添加不同类型的连接进行测试
        current_time = time.time()

        # 长期存活的连接
        old_conn = Mock()
        old_pooled = PooledConnection(old_conn, pool)
        old_pooled.created_at = current_time - 7200  # 2小时前
        old_pooled.last_used = current_time - 3600  # 1小时前
        old_pooled.use_count = 50
        pool._all_connections.add(old_pooled)

        # 高使用频率的连接
        busy_conn = Mock()
        busy_pooled = PooledConnection(busy_conn, pool)
        busy_pooled.created_at = current_time - 1800  # 30分钟前
        busy_pooled.last_used = current_time - 60  # 1分钟前
        busy_pooled.use_count = 1500
        pool._all_connections.add(busy_pooled)

        # 执行诊断
        diagnosis = pool.diagnose_memory_leaks()

        # 验证诊断结果
        assert diagnosis["total_connections"] == 2
        assert diagnosis["queue_size"] == 2
        assert diagnosis["active_connections"] == 3
        assert len(diagnosis["long_lived_connections"]) == 1
        assert len(diagnosis["high_usage_connections"]) == 1
        assert len(diagnosis["recommendations"]) > 0

    def test_force_cleanup_functionality(self):
        """测试强制清理功能"""
        mock_settings = Mock()
        mock_settings.db.pool.max_inactive_connection_lifetime = 3600

        pool = ConnectionPool.__new__(ConnectionPool)
        pool.settings = mock_settings
        pool._all_connections = set()
        pool._lock = threading.RLock()
        pool._closed = False

        # 添加需要清理的连接
        current_time = time.time()

        # 不健康的连接
        unhealthy_conn = Mock()
        unhealthy_pooled = PooledConnection(unhealthy_conn, pool)
        unhealthy_pooled.is_healthy = False
        pool._all_connections.add(unhealthy_pooled)

        # 长时间空闲的连接
        idle_conn = Mock()
        idle_pooled = PooledConnection(idle_conn, pool)
        idle_pooled.last_used = current_time - 2000  # 超过30分钟
        pool._all_connections.add(idle_pooled)

        # Mock _remove_connection 方法
        removed_connections = []

        def mock_remove_connection(conn):
            removed_connections.append(conn)
            pool._all_connections.discard(conn)

        pool._remove_connection = mock_remove_connection

        # 执行强制清理
        result = pool.force_cleanup()

        # 验证清理结果
        assert result["cleaned_connections"] == 2
        assert result["failed_cleanups"] == 0
        assert len(removed_connections) == 2

    def test_global_memory_leak_functions(self):
        """测试全局内存泄漏诊断函数"""
        # 测试连接池未初始化的情况
        from app.adapters.db.pool import DatabaseError

        with patch(
            "app.adapters.db.pool.get_pool", side_effect=DatabaseError("连接池未初始化")
        ):
            result = diagnose_memory_leaks()
            assert "error" in result

            result = force_cleanup_connections()
            assert "error" in result

    def test_connection_creation_exception_cleanup(self):
        """测试连接创建异常时的资源清理"""
        mock_settings = Mock()
        mock_settings.db.timeouts.connect_timeout_ms = 5000
        mock_settings.db.timeouts.statement_timeout_ms = 30000
        mock_settings.db.dsn_write = "postgresql://test"
        mock_settings.db.dsn_read = None
        mock_settings.db.host = "localhost"
        mock_settings.db.name = "test"
        mock_settings.db.user = "test"
        mock_settings.db.password = None

        pool = ConnectionPool.__new__(ConnectionPool)
        pool.settings = mock_settings
        pool._all_connections = set()
        pool._lock = threading.RLock()
        pool._stats = Mock()
        pool._stats.total_connections = 0
        pool._stats.peak_connections = 0
        pool._dsn = "postgresql://test"

        # Mock psycopg.connect 抛出异常
        with patch(
            "app.adapters.db.pool.psycopg.connect", side_effect=Exception("连接失败")
        ):
            with pytest.raises(Exception):
                pool._create_connection()

        # 验证没有连接被添加到集合中
        assert len(pool._all_connections) == 0
        assert pool._stats.total_connections == 0

    def test_connection_creation_partial_failure_cleanup(self):
        """测试连接创建部分失败时的清理"""
        mock_settings = Mock()
        mock_settings.db.timeouts.connect_timeout_ms = 5000
        mock_settings.db.timeouts.statement_timeout_ms = 30000

        pool = ConnectionPool.__new__(ConnectionPool)
        pool.settings = mock_settings
        pool._all_connections = set()
        pool._lock = threading.RLock()
        pool._stats = Mock()
        pool._stats.total_connections = 0
        pool._stats.peak_connections = 0
        pool._dsn = "postgresql://test"
        # 添加性能优化所需的预计算属性
        pool._connect_timeout = mock_settings.db.timeouts.connect_timeout_ms // 1000
        pool._statement_timeout_sql = f"SET statement_timeout TO '{mock_settings.db.timeouts.statement_timeout_ms}ms'"

        # Mock连接创建成功但后续操作失败
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor.execute.side_effect = Exception("设置参数失败")
        mock_conn.cursor.return_value = mock_cursor

        with patch("app.adapters.db.pool.psycopg.connect", return_value=mock_conn):
            with pytest.raises(Exception):
                pool._create_connection()

        # 验证连接被正确清理
        assert len(pool._all_connections) == 0
        # 注意：由于_create_connection有@smart_retry()装饰器，会重试多次
        # 每次重试都会调用close()，所以close被调用多次是正常的
        assert mock_conn.close.call_count >= 1  # 至少被调用1次

    def test_pooled_connection_mark_used_after_close(self):
        """测试关闭后标记使用的安全性"""
        mock_conn = Mock()
        mock_pool = Mock()

        pooled_conn = PooledConnection(mock_conn, mock_pool)
        pooled_conn.close()

        # 关闭后标记使用应该安全（不抛异常）
        original_use_count = pooled_conn.use_count
        pooled_conn.mark_used()

        # 使用次数不应该增加
        assert pooled_conn.use_count == original_use_count
