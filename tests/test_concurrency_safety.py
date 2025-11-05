"""
并发安全测试模块

测试连接池在多线程环境下的安全性和正确性。
"""

import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch, MagicMock
import queue

from app.adapters.db.pool import ConnectionPool, PooledConnection, PoolStats
from app.core.config.loader_new import (
    Settings,
    DbSettings,
    DbPoolSettings,
    DbTimeoutSettings,
)
from app.core.exceptions import DatabaseError, DatabaseConnectionError


class TestConcurrencySafety(unittest.TestCase):
    """并发安全测试"""

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

    def test_concurrent_connection_acquisition(self):
        """测试并发连接获取的线程安全性"""
        with patch("psycopg.connect") as mock_connect:
            # 模拟数据库连接
            mock_conn = Mock()
            mock_conn.closed = False
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            mock_connect.return_value = mock_conn

            pool = ConnectionPool(self.settings)

            # 并发获取连接
            results = []
            errors = []

            def get_connection_worker():
                try:
                    with pool.get_connection() as conn:
                        # 模拟一些工作
                        time.sleep(0.01)
                        results.append(True)
                except Exception as e:
                    errors.append(str(e))

            # 启动多个线程
            threads = []
            for _ in range(20):
                thread = threading.Thread(target=get_connection_worker)
                threads.append(thread)
                thread.start()

            # 等待所有线程完成
            for thread in threads:
                thread.join()

            pool.close()

            # 验证结果
            self.assertEqual(len(results), 20, "所有连接获取应该成功")
            self.assertEqual(len(errors), 0, f"不应该有错误: {errors}")

    def test_concurrent_pool_stats_consistency(self):
        """测试并发访问时统计信息的一致性"""
        with patch("psycopg.connect") as mock_connect:
            mock_conn = Mock()
            mock_conn.closed = False
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            mock_connect.return_value = mock_conn

            pool = ConnectionPool(self.settings)

            stats_snapshots = []

            def stats_worker():
                for _ in range(10):
                    stats = pool.get_stats()
                    stats_snapshots.append(stats.to_dict())
                    time.sleep(0.001)

            def connection_worker():
                for _ in range(5):
                    try:
                        with pool.get_connection() as conn:
                            time.sleep(0.002)
                    except Exception:
                        pass

            # 启动统计和连接线程
            threads = []
            for _ in range(3):
                threads.append(threading.Thread(target=stats_worker))
            for _ in range(5):
                threads.append(threading.Thread(target=connection_worker))

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

            pool.close()

            # 验证统计信息的一致性
            self.assertGreater(len(stats_snapshots), 0, "应该收集到统计信息")

            # 检查统计信息的合理性
            for stats in stats_snapshots:
                self.assertGreaterEqual(stats["total_requests"], 0)
                self.assertGreaterEqual(stats["active_connections"], 0)
                self.assertLessEqual(
                    stats["active_connections"], self.settings.db.pool.max_size
                )

    def test_pooled_connection_thread_safety(self):
        """测试 PooledConnection 的线程安全性"""
        with patch("psycopg.connect") as mock_connect:
            mock_conn = Mock()
            mock_conn.closed = False
            mock_connect.return_value = mock_conn

            pool = ConnectionPool(self.settings)
            pooled_conn = PooledConnection(mock_conn, pool)

            # 并发标记使用
            def mark_used_worker():
                for _ in range(100):
                    pooled_conn.mark_used()

            threads = []
            for _ in range(10):
                thread = threading.Thread(target=mark_used_worker)
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            # 验证使用次数
            self.assertEqual(pooled_conn.use_count, 1000, "使用次数应该正确累计")

            # 测试并发关闭
            close_results = []

            def close_worker():
                try:
                    pooled_conn.close()
                    close_results.append("closed")
                except Exception as e:
                    close_results.append(f"error: {e}")

            close_threads = []
            for _ in range(5):
                thread = threading.Thread(target=close_worker)
                close_threads.append(thread)
                thread.start()

            for thread in close_threads:
                thread.join()

            # 验证关闭操作的安全性
            self.assertTrue(pooled_conn.is_closed(), "连接应该被关闭")
            self.assertEqual(
                len([r for r in close_results if r == "closed"]),
                5,
                "所有关闭操作应该安全完成",
            )

            pool.close()

    def test_graceful_pool_shutdown(self):
        """测试连接池的优雅关闭"""
        with patch("psycopg.connect") as mock_connect:
            mock_conn = Mock()
            mock_conn.closed = False
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            mock_connect.return_value = mock_conn

            pool = ConnectionPool(self.settings)

            # 启动一些长时间运行的连接
            active_connections = []
            connection_finished = []

            def long_running_connection():
                try:
                    with pool.get_connection() as conn:
                        active_connections.append(threading.current_thread().ident)
                        time.sleep(0.5)  # 模拟长时间操作
                        connection_finished.append(threading.current_thread().ident)
                except Exception as e:
                    connection_finished.append(f"error: {e}")

            # 启动连接线程
            threads = []
            for _ in range(3):
                thread = threading.Thread(target=long_running_connection)
                threads.append(thread)
                thread.start()

            # 等待连接建立
            time.sleep(0.1)

            # 开始关闭连接池
            close_start_time = time.time()
            pool.close(timeout=1.0)
            close_duration = time.time() - close_start_time

            # 等待所有线程完成
            for thread in threads:
                thread.join()

            # 验证优雅关闭
            self.assertGreater(len(active_connections), 0, "应该有活跃连接")
            self.assertLessEqual(close_duration, 1.5, "关闭应该在合理时间内完成")
            self.assertTrue(pool._closed, "连接池应该被标记为已关闭")

    def test_connection_pool_state_consistency(self):
        """测试连接池状态的一致性"""
        with patch("psycopg.connect") as mock_connect:
            mock_conn = Mock()
            mock_conn.closed = False
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            mock_connect.return_value = mock_conn

            pool = ConnectionPool(self.settings)

            # 并发访问连接池状态
            state_checks = []

            def state_checker():
                for _ in range(50):
                    try:
                        available = pool._is_available()
                        closed = pool._closed
                        closing = pool._closing
                        state_checks.append((available, closed, closing))
                        time.sleep(0.001)
                    except Exception as e:
                        state_checks.append(f"error: {e}")

            def connection_user():
                for _ in range(10):
                    try:
                        with pool.get_connection() as conn:
                            time.sleep(0.002)
                    except Exception:
                        pass

            # 启动状态检查和连接使用线程
            threads = []
            for _ in range(3):
                threads.append(threading.Thread(target=state_checker))
            for _ in range(2):
                threads.append(threading.Thread(target=connection_user))

            for thread in threads:
                thread.start()

            # 运行一段时间后关闭
            time.sleep(0.1)
            pool.close()

            for thread in threads:
                thread.join()

            # 验证状态一致性
            valid_states = [s for s in state_checks if isinstance(s, tuple)]
            self.assertGreater(len(valid_states), 0, "应该收集到有效的状态信息")

            # 检查状态转换的合理性
            for available, closed, closing in valid_states:
                if closed:
                    self.assertFalse(available, "已关闭的连接池不应该可用")
                if closing and not closed:
                    self.assertFalse(available, "正在关闭的连接池不应该可用")


if __name__ == "__main__":
    unittest.main()
