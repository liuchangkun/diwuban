"""
连接租借机制测试
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager

from app.adapters.db.connection_lease import (
    ConnectionLease,
    LeaseConfig,
    lease_connection,
    batch_operation,
)


class TestConnectionLease:
    """测试连接租借机制"""

    def test_lease_config_defaults(self):
        """测试租借配置默认值"""
        config = LeaseConfig()
        assert config.max_lease_time == 300.0
        assert config.renewal_threshold == 0.8
        assert config.batch_size == 1000
        assert config.max_batch_time == 30.0
        assert config.pool_usage_threshold == 0.8

    def test_lease_config_custom_values(self):
        """测试自定义租借配置"""
        config = LeaseConfig(
            max_lease_time=180.0,
            renewal_threshold=0.7,
            batch_size=500,
            max_batch_time=60.0,
            pool_usage_threshold=0.9,
        )
        assert config.max_lease_time == 180.0
        assert config.renewal_threshold == 0.7
        assert config.batch_size == 500
        assert config.max_batch_time == 60.0
        assert config.pool_usage_threshold == 0.9

    @patch("app.adapters.db.get_connection")
    @patch("app.adapters.db.pool.get_pool_stats")
    def test_connection_lease_basic_flow(self, mock_get_stats, mock_get_connection):
        """测试连接租借基本流程"""
        # 模拟设置
        mock_settings = Mock()

        # 模拟连接池统计
        mock_get_stats.return_value = {"active_connections": 5, "max_size": 10}

        # 模拟连接管理器
        mock_conn = Mock()
        mock_conn_manager = Mock()
        mock_conn_manager.__enter__ = Mock(return_value=mock_conn)
        mock_conn_manager.__exit__ = Mock(return_value=None)
        mock_get_connection.return_value = mock_conn_manager

        # 创建租借管理器
        lease = ConnectionLease(mock_settings)

        # 测试获取连接
        with lease.get_connection() as conn:
            assert conn == mock_conn
            assert lease._current_connection == mock_conn
            assert lease._lease_start_time is not None

        # 验证连接获取被调用
        mock_get_connection.assert_called_once()
        mock_conn_manager.__enter__.assert_called_once()

    @patch("app.adapters.db.get_connection")
    @patch("app.adapters.db.pool.get_pool_stats")
    def test_connection_lease_renewal(self, mock_get_stats, mock_get_connection):
        """测试连接租借续租机制"""
        # 模拟设置
        mock_settings = Mock()

        # 模拟连接池统计
        mock_get_stats.return_value = {"active_connections": 3, "max_size": 10}

        # 模拟连接管理器
        mock_conn1 = Mock()
        mock_conn2 = Mock()
        mock_conn_manager1 = Mock()
        mock_conn_manager1.__enter__ = Mock(return_value=mock_conn1)
        mock_conn_manager1.__exit__ = Mock(return_value=None)

        mock_conn_manager2 = Mock()
        mock_conn_manager2.__enter__ = Mock(return_value=mock_conn2)
        mock_conn_manager2.__exit__ = Mock(return_value=None)

        mock_get_connection.side_effect = [mock_conn_manager1, mock_conn_manager2]

        # 创建租借管理器，设置短的租借时间
        config = LeaseConfig(max_lease_time=0.1, renewal_threshold=0.5)
        lease = ConnectionLease(mock_settings, config)

        # 第一次获取连接
        with lease.get_connection() as conn:
            assert conn == mock_conn1

            # 等待超过续租阈值
            time.sleep(0.06)  # 超过 0.1 * 0.5 = 0.05 秒

            # 再次获取连接应该触发续租
            with lease.get_connection() as conn2:
                assert conn2 == mock_conn2  # 应该是新连接

        # 验证连接获取被调用两次（原始 + 续租）
        assert mock_get_connection.call_count == 2

    @patch("app.adapters.db.get_connection")
    @patch("app.adapters.db.pool.get_pool_stats")
    def test_connection_lease_pool_usage_warning(
        self, mock_get_stats, mock_get_connection
    ):
        """测试连接池使用率过高时的警告"""
        # 模拟设置
        mock_settings = Mock()

        # 模拟高使用率的连接池统计
        mock_get_stats.return_value = {
            "active_connections": 9,
            "max_size": 10,  # 90% 使用率
        }

        # 模拟连接管理器
        mock_conn = Mock()
        mock_conn_manager = Mock()
        mock_conn_manager.__enter__ = Mock(return_value=mock_conn)
        mock_conn_manager.__exit__ = Mock(return_value=None)
        mock_get_connection.return_value = mock_conn_manager

        # 创建租借管理器
        lease = ConnectionLease(mock_settings)

        # 测试获取连接（应该记录警告但不抛出异常）
        with lease.get_connection() as conn:
            assert conn == mock_conn

    @patch("app.adapters.db.get_connection")
    @patch("app.adapters.db.pool.get_pool_stats")
    def test_lease_connection_context_manager(
        self, mock_get_stats, mock_get_connection
    ):
        """测试连接租借上下文管理器"""
        # 模拟设置
        mock_settings = Mock()

        # 模拟连接池统计
        mock_get_stats.return_value = {"active_connections": 2, "max_size": 10}

        # 模拟连接管理器
        mock_conn = Mock()
        mock_conn_manager = Mock()
        mock_conn_manager.__enter__ = Mock(return_value=mock_conn)
        mock_conn_manager.__exit__ = Mock(return_value=None)
        mock_get_connection.return_value = mock_conn_manager

        # 测试上下文管理器
        with lease_connection(mock_settings) as lease:
            assert isinstance(lease, ConnectionLease)

            with lease.get_connection() as conn:
                assert conn == mock_conn

    def test_batch_operation_decorator_small_data(self):
        """测试批量操作装饰器处理小数据量"""
        # 模拟连接
        mock_conn = Mock()

        # 创建测试函数
        @batch_operation(batch_size=3)
        def test_func(conn, data):
            return len(data)

        # 测试小数据量（不会分批）
        data = [1, 2, 3, 4, 5]
        result = test_func(mock_conn, data)

        # 应该返回总处理数量
        assert result == 5

    def test_batch_operation_decorator_large_data(self):
        """测试批量操作装饰器处理大数据量"""
        # 模拟连接 - 需要让它通过isinstance(conn, Connection)检查
        from psycopg import Connection
        mock_conn = Mock(spec=Connection)

        # 创建测试函数，记录调用次数
        call_count = 0
        batch_sizes = []

        @batch_operation(batch_size=3)
        def test_func(conn, data):
            nonlocal call_count, batch_sizes
            call_count += 1
            batch_sizes.append(len(data))
            return len(data)

        # 测试大数据量（会分批）
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        result = test_func(mock_conn, data)

        # 应该分成 4 批：[3, 3, 3, 1]
        assert call_count == 4
        assert batch_sizes == [3, 3, 3, 1]
        assert result == 10  # 总处理数量

    def test_batch_operation_decorator_non_iterable_data(self):
        """测试批量操作装饰器处理非可迭代数据"""
        # 模拟连接
        mock_conn = Mock()

        # 创建测试函数
        @batch_operation(batch_size=3)
        def test_func(conn, data):
            return data * 2

        # 测试非可迭代数据（应该直接调用原函数）
        result = test_func(mock_conn, 5)
        assert result == 10

    def test_batch_operation_decorator_string_data(self):
        """测试批量操作装饰器处理字符串数据"""
        # 模拟连接
        mock_conn = Mock()

        # 创建测试函数
        @batch_operation(batch_size=3)
        def test_func(conn, data):
            return len(data)

        # 测试字符串数据（应该直接调用原函数，不分批）
        result = test_func(mock_conn, "hello")
        assert result == 5

    def test_batch_operation_decorator_no_connection(self):
        """测试批量操作装饰器处理无连接参数的情况"""

        # 创建测试函数
        @batch_operation(batch_size=3)
        def test_func(data):
            return len(data)

        # 测试无连接参数（应该直接调用原函数）
        data = [1, 2, 3, 4, 5]
        result = test_func(data)
        assert result == 5

    @patch("app.adapters.db.get_connection")
    @patch("app.adapters.db.pool.get_pool_stats")
    def test_connection_lease_close(self, mock_get_stats, mock_get_connection):
        """测试连接租借管理器关闭"""
        # 模拟设置
        mock_settings = Mock()

        # 模拟连接池统计
        mock_get_stats.return_value = {"active_connections": 2, "max_size": 10}

        # 模拟连接管理器
        mock_conn = Mock()
        mock_conn_manager = Mock()
        mock_conn_manager.__enter__ = Mock(return_value=mock_conn)
        mock_conn_manager.__exit__ = Mock(return_value=None)
        mock_get_connection.return_value = mock_conn_manager

        # 创建租借管理器
        lease = ConnectionLease(mock_settings)

        # 获取连接
        with lease.get_connection() as conn:
            assert conn == mock_conn

        # 关闭租借管理器
        lease.close()

        # 验证连接被释放
        mock_conn_manager.__exit__.assert_called()
        assert lease._current_connection is None
        assert lease._lease_start_time is None

    @patch("app.adapters.db.get_connection")
    @patch("app.adapters.db.pool.get_pool_stats")
    def test_connection_lease_exception_handling(
        self, mock_get_stats, mock_get_connection
    ):
        """测试连接租借异常处理"""
        # 模拟设置
        mock_settings = Mock()

        # 模拟连接池统计
        mock_get_stats.return_value = {"active_connections": 2, "max_size": 10}

        # 模拟连接获取失败
        mock_get_connection.side_effect = Exception("连接获取失败")

        # 创建租借管理器
        lease = ConnectionLease(mock_settings)

        # 测试异常处理
        with pytest.raises(Exception, match="连接获取失败"):
            with lease.get_connection() as conn:
                pass
