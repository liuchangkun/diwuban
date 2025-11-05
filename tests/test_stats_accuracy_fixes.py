"""
测试连接池统计信息准确性修复
"""

import unittest
import time
import threading
from unittest.mock import Mock, patch

from app.adapters.db.pool import PoolStats, ConnectionPool
from app.core.config.loader_new import (
    Settings,
    DbSettings,
    DbPoolSettings,
    DbTimeoutSettings,
    DbRetrySettings,
)


class TestStatsAccuracyFixes(unittest.TestCase):
    """测试统计信息准确性修复"""

    def setUp(self):
        """测试前准备"""
        self.settings = Settings(
            db=DbSettings(
                host="localhost",
                name="test_db",
                user="test_user",
                pool=DbPoolSettings(min_size=1, max_size=5),
                timeouts=DbTimeoutSettings(connect_timeout_ms=5000),
                retry=DbRetrySettings(max_retries=3),
            )
        )

    def test_pool_stats_validation_and_correction(self):
        """测试统计信息验证和修正功能"""
        stats = PoolStats()

        # 模拟不准确的统计信息
        stats.total_connections = 5
        stats.active_connections = 3
        stats.idle_connections = 1
        stats.total_requests = 10
        stats._request_count = 8  # 不同步的内部计数器

        # 验证并修正
        corrections = stats.validate_and_correct(
            actual_connections=4, actual_queue_size=2
        )

        # 验证修正结果
        self.assertIn("total_connections", corrections)
        self.assertEqual(stats.total_connections, 4)
        self.assertEqual(corrections["total_connections"]["old"], 5)
        self.assertEqual(corrections["total_connections"]["new"], 4)

        self.assertIn("idle_connections", corrections)
        self.assertEqual(stats.idle_connections, 2)

        self.assertIn("request_count_sync", corrections)
        self.assertEqual(stats._request_count, 10)  # 同步到公开字段

    def test_negative_active_connections_correction(self):
        """测试负数活跃连接数修正"""
        stats = PoolStats()
        stats.active_connections = -2  # 异常的负数

        corrections = stats.validate_and_correct(
            actual_connections=3, actual_queue_size=2
        )

        self.assertIn("active_connections", corrections)
        self.assertEqual(stats.active_connections, 0)
        self.assertEqual(
            corrections["active_connections"]["reason"], "negative_value_corrected"
        )

    def test_active_connections_exceeds_total_correction(self):
        """测试活跃连接数超过总连接数的修正"""
        stats = PoolStats()
        stats.total_connections = 5
        stats.active_connections = 8  # 超过总连接数
        stats.idle_connections = 2

        corrections = stats.validate_and_correct(
            actual_connections=5, actual_queue_size=2
        )

        self.assertIn("active_connections", corrections)
        self.assertEqual(stats.active_connections, 3)  # max(0, 5-2)
        self.assertEqual(
            corrections["active_connections"]["reason"], "exceeds_total_connections"
        )

    def test_wait_time_accurate_update_with_sync_check(self):
        """测试准确的等待时间更新和同步检查"""
        stats = PoolStats()
        stats.total_requests = 5
        stats._request_count = 3  # 不同步

        # 更新等待时间，应该检测到不同步并修正
        # 注意：日志功能已从代码中移除，只测试同步修正功能
        stats.update_wait_time_accurate(0.1)

        # 验证同步修正
        # update_wait_time_accurate会先增加_request_count（变成4）
        # 然后检测到与total_requests不同步，修正为total_requests（5）
        self.assertEqual(stats._request_count, stats.total_requests)

    def test_stats_to_dict_includes_validation_info(self):
        """测试统计信息字典包含验证信息"""
        stats = PoolStats()
        stats._validation_errors = 3
        stats._last_validation = time.time()

        stats_dict = stats.to_dict()

        self.assertIn("validation_errors", stats_dict)
        self.assertEqual(stats_dict["validation_errors"], 3)
        self.assertIn("last_validation", stats_dict)
        self.assertGreater(stats_dict["last_validation"], 0)

    @patch("app.adapters.db.pool.psycopg.connect")
    def test_connection_pool_stats_validation_integration(self, mock_connect):
        """测试连接池统计验证集成"""
        # 模拟数据库连接
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock()
        mock_connect.return_value = mock_conn

        pool = ConnectionPool(self.settings)

        try:
            # 人为制造统计不一致
            with pool._lock:
                pool._stats.total_connections = 10  # 错误的值
                pool._stats.active_connections = -1  # 负数

            # 获取统计信息，应该触发验证和修正
            # 注意：日志功能已从代码中移除，只测试修正功能
            stats = pool.get_stats()

            # 验证统计信息被修正
            self.assertEqual(stats.total_connections, len(pool._all_connections))
            self.assertEqual(stats.active_connections, 0)  # 负数被修正为0

        finally:
            pool.close()

    def test_concurrent_stats_update_accuracy(self):
        """测试并发统计更新的准确性"""
        stats = PoolStats()
        errors = []

        def update_stats(thread_id):
            try:
                for i in range(100):
                    stats.update_wait_time_accurate(0.01 * thread_id)
                    stats.total_requests += 1
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        # 启动多个线程并发更新
        threads = []
        for i in range(5):
            thread = threading.Thread(target=update_stats, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证没有错误
        self.assertEqual(len(errors), 0, f"并发更新出现错误: {errors}")

        # 验证统计信息合理性
        self.assertEqual(stats.total_requests, 500)  # 5个线程 * 100次更新
        self.assertGreater(stats.average_wait_time, 0)

    def test_stats_reset_preserves_cumulative_data(self):
        """测试统计重置保留累计数据"""
        stats = PoolStats()

        # 设置一些累计数据和内部状态
        stats.total_requests = 100
        stats.failed_requests = 5
        stats.average_wait_time = 0.05
        stats.peak_connections = 8
        stats._validation_errors = 3
        stats._wait_time_sum = 5.0  # 设置等待时间总和以保护平均值
        stats._request_count = 100  # 与total_requests同步

        # 设置当前状态数据
        stats.total_connections = 5
        stats.active_connections = 3
        stats.idle_connections = 2

        # 模拟重置（通过验证修正实现）
        corrections = stats.validate_and_correct(
            actual_connections=0, actual_queue_size=0
        )

        # 验证累计数据保留
        self.assertEqual(stats.total_requests, 100)
        self.assertEqual(stats.failed_requests, 5)
        self.assertEqual(stats.average_wait_time, 0.05)
        self.assertEqual(stats.peak_connections, 8)

        # 验证当前状态被重置
        self.assertEqual(stats.total_connections, 0)
        self.assertEqual(stats.idle_connections, 0)

    def test_validation_error_counting(self):
        """测试验证错误计数"""
        stats = PoolStats()
        initial_errors = stats._validation_errors

        # 触发多个验证错误
        stats.total_connections = 10
        stats.active_connections = -5
        corrections1 = stats.validate_and_correct(
            actual_connections=3, actual_queue_size=1
        )

        stats.active_connections = 15  # 超过总连接数
        corrections2 = stats.validate_and_correct(
            actual_connections=3, actual_queue_size=1
        )

        # 验证错误计数增加
        self.assertGreater(stats._validation_errors, initial_errors)
        self.assertGreater(len(corrections1), 0)
        self.assertGreater(len(corrections2), 0)

    def test_backward_compatibility_fast_update(self):
        """测试向后兼容的快速更新方法"""
        stats = PoolStats()

        # 先设置total_requests，再使用快速更新方法
        stats.total_requests = 1
        stats.update_wait_time_fast(0.1)

        # 验证结果与新方法一致
        self.assertEqual(stats.average_wait_time, 0.1)
        self.assertEqual(stats._wait_time_sum, 0.1)
        self.assertEqual(stats._request_count, 1)


if __name__ == "__main__":
    unittest.main()
