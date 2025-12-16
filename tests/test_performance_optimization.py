"""
连接池性能优化测试模块

测试连接池性能优化的效果和正确性。
"""

import time
import unittest
from unittest.mock import Mock, patch
import threading

from app.adapters.db.pool import ConnectionPool, PooledConnection, PoolStats
from app.core.config.loader_new import (
    Settings,
    DbSettings,
    DbPoolSettings,
    DbTimeoutSettings,
)
from app.core.exceptions import DatabaseError


class TestPerformanceOptimization(unittest.TestCase):
    """性能优化测试"""

    def setUp(self):
        """设置测试环境"""
        self.settings = Settings(
            db=DbSettings(
                host="localhost",
                name="test_db",
                user="test_user",
                password="test_pass",
                pool=DbPoolSettings(min_size=2, max_size=5),
                timeouts=DbTimeoutSettings(connect_timeout_ms=1000),
            )
        )

    def test_pool_stats_fast_update(self):
        """测试统计信息快速更新方法"""
        stats = PoolStats()

        # 测试快速等待时间更新
        wait_times = [0.1, 0.2, 0.15, 0.3, 0.25]
        for wait_time in wait_times:
            stats.update_wait_time_fast(wait_time)

        # 验证平均值计算正确
        expected_avg = sum(wait_times) / len(wait_times)
        self.assertAlmostEqual(stats.average_wait_time, expected_avg, places=6)

        # 验证内部计数器正确
        self.assertEqual(stats._request_count, len(wait_times))
        self.assertAlmostEqual(stats._wait_time_sum, sum(wait_times), places=6)

    def test_connection_health_check_caching(self):
        """测试连接健康检查的缓存机制"""
        with patch("psycopg.connect") as mock_connect:
            mock_conn = Mock()
            mock_conn.closed = False
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            # 模拟健康检查查询返回正确结果
            mock_cursor.fetchone.return_value = (1,)
            mock_connect.return_value = mock_conn

            pool = ConnectionPool(self.settings)
            pooled_conn = PooledConnection(mock_conn, pool)

            # 模拟auto_commit上下文管理器
            with patch("app.adapters.db.transaction.auto_commit") as mock_auto_commit:
                mock_auto_commit.return_value.__enter__ = Mock(return_value=mock_conn)
                mock_auto_commit.return_value.__exit__ = Mock(return_value=None)

                # 第一次健康检查
                result1 = pooled_conn.check_health(force_check=True)
                self.assertTrue(result1)

                # 记录第一次检查的调用次数
                first_call_count = mock_cursor.execute.call_count

                # 立即进行第二次健康检查（应该使用缓存）
                result2 = pooled_conn.check_health(force_check=False)
                self.assertTrue(result2)

                # 验证第二次检查没有执行SQL（使用了缓存）
                self.assertEqual(mock_cursor.execute.call_count, first_call_count)

                # 等待超过缓存时间后再检查
                # 需要同时设置last_used、_last_health_check和_last_deep_check都超过缓存时间
                # 深度检查的缓存时间是60秒
                pooled_conn.last_used = time.time() - 61  # 模拟61秒前使用
                pooled_conn._last_health_check = time.time() - 61  # 模拟61秒前检查
                pooled_conn._last_deep_check = time.time() - 61  # 模拟61秒前深度检查
                result3 = pooled_conn.check_health(force_check=False)
                self.assertTrue(result3)

                # 验证这次执行了SQL查询
                self.assertGreater(mock_cursor.execute.call_count, first_call_count)

            pool.close()

    def test_connection_validation_optimization(self):
        """测试连接验证的性能优化"""
        with patch("psycopg.connect") as mock_connect:
            mock_conn = Mock()
            mock_conn.closed = False
            mock_conn.autocommit = True
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            # 模拟健康检查查询返回正确结果
            mock_cursor.fetchone.return_value = (1,)
            mock_connect.return_value = mock_conn

            pool = ConnectionPool(self.settings)
            pooled_conn = PooledConnection(mock_conn, pool)

            # 模拟最近使用的连接
            pooled_conn.last_used = time.time() - 1  # 1秒前使用

            with patch(
                "app.adapters.db.transaction.validate_connection_state"
            ) as mock_validate:
                mock_validate.return_value = {"healthy": True}

                with patch(
                    "app.adapters.db.transaction.auto_commit"
                ) as mock_auto_commit:
                    mock_auto_commit.return_value.__enter__ = Mock(
                        return_value=mock_conn
                    )
                    mock_auto_commit.return_value.__exit__ = Mock(return_value=None)

                    # 验证最近使用的连接跳过详细验证
                    result = pool._validate_pooled_connection(pooled_conn)
                    self.assertTrue(result)

                    # 验证没有调用详细的状态验证
                    mock_validate.assert_not_called()

                    # 模拟长时间未使用的连接
                    pooled_conn.last_used = time.time() - 60  # 60秒前使用

                    result = pool._validate_pooled_connection(pooled_conn)
                    self.assertTrue(result)

                    # 验证调用了详细的状态验证
                    mock_validate.assert_called_once()

            pool.close()

    def test_precomputed_connection_parameters(self):
        """测试预计算连接参数的优化"""
        with patch("psycopg.connect") as mock_connect:
            mock_conn = Mock()
            mock_conn.closed = False
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            mock_connect.return_value = mock_conn

            pool = ConnectionPool(self.settings)

            # 验证预计算的参数存在
            self.assertTrue(hasattr(pool, "_connect_timeout"))
            self.assertTrue(hasattr(pool, "_statement_timeout_sql"))

            # 验证预计算的值正确
            expected_timeout = self.settings.db.timeouts.connect_timeout_ms // 1000
            self.assertEqual(pool._connect_timeout, expected_timeout)

            expected_sql = f"SET statement_timeout TO '{self.settings.db.timeouts.statement_timeout_ms}ms'"
            self.assertEqual(pool._statement_timeout_sql, expected_sql)

            # 创建连接时验证使用了预计算的参数
            pool._create_connection()

            # 验证使用了预计算的超时值
            mock_connect.assert_called_with(
                pool._dsn, connect_timeout=pool._connect_timeout
            )

            # 验证使用了预计算的SQL语句
            mock_cursor.execute.assert_called_with(pool._statement_timeout_sql)

            pool.close()

    # 注意：test_reduced_logging_overhead 已删除
    # 原因：测试的条件日志功能已从代码中移除

    def test_performance_under_load(self):
        """测试高负载下的性能表现"""
        with patch("psycopg.connect") as mock_connect:
            mock_conn = Mock()
            mock_conn.closed = False
            mock_conn.autocommit = True
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            mock_connect.return_value = mock_conn

            pool = ConnectionPool(self.settings)

            # 测试大量连接获取的性能
            start_time = time.time()
            connection_count = 100

            for _ in range(connection_count):
                try:
                    with pool.get_connection() as conn:
                        pass  # 模拟使用连接
                except Exception:
                    pass  # 忽略异常，专注于性能测试

            end_time = time.time()
            total_time = end_time - start_time

            # 验证平均每次连接获取时间合理（应该很快）
            avg_time_per_connection = total_time / connection_count
            self.assertLess(
                avg_time_per_connection, 0.01, "连接获取平均时间应该小于10ms"
            )

            # 验证统计信息正确更新
            stats = pool.get_stats()
            self.assertGreaterEqual(stats.to_dict()["total_requests"], connection_count)

            pool.close()


if __name__ == "__main__":
    unittest.main()
