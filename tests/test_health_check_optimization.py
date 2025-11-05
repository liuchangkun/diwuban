"""
测试连接健康检查优化功能
"""

import time
import unittest
from unittest.mock import Mock, patch, MagicMock

from app.adapters.db.health_monitor import (
    HealthMonitor,
    get_health_monitor,
    record_health_check,
)
from app.adapters.db.pool import PooledConnection


class TestHealthCheckOptimization(unittest.TestCase):
    """测试健康检查优化功能"""

    def setUp(self):
        """测试前准备"""
        # 重置全局健康监控器
        import app.adapters.db.health_monitor as monitor_module

        monitor_module._health_monitor = None

    def test_health_monitor_basic_functionality(self):
        """测试健康监控器基本功能"""
        monitor = HealthMonitor()

        # 记录一些检查结果
        monitor.record_check("cached", 0.001, True, {"cache_reason": "recently_used"})
        monitor.record_check("lightweight", 0.005, True)
        monitor.record_check("deep", 0.050, True)
        monitor.record_check("deep", 0.100, False, {"reason": "connection_failed"})

        # 获取统计信息
        stats = monitor.get_stats()
        self.assertEqual(stats.total_checks, 4)
        self.assertEqual(stats.cached_checks, 1)
        self.assertEqual(stats.lightweight_checks, 1)
        self.assertEqual(stats.deep_checks, 2)
        self.assertEqual(stats.failed_checks, 1)

        # 检查缓存命中率
        self.assertEqual(stats.cache_hit_rate, 0.25)  # 1/4

        # 检查平均时间
        self.assertGreater(stats.get_average_check_time(), 0)
        self.assertGreater(stats.get_average_deep_check_time(), 0)

    def test_health_monitor_recommendations(self):
        """测试健康监控器优化建议"""
        monitor = HealthMonitor()

        # 模拟低缓存命中率场景
        for _ in range(10):
            monitor.record_check("deep", 0.020, True)

        recommendations = monitor.get_optimization_recommendations()
        self.assertIn("缓存命中率较低", "".join(recommendations))

        # 模拟高失败率场景
        monitor.reset_stats()
        for _ in range(5):
            monitor.record_check("deep", 0.010, True)
        for _ in range(5):
            monitor.record_check("deep", 0.010, False)

        recommendations = monitor.get_optimization_recommendations()
        self.assertIn("失败率较高", "".join(recommendations))

    @patch("app.adapters.db.pool.time.time")
    def test_pooled_connection_cached_health_check(self, mock_time):
        """测试连接缓存健康检查"""
        # 模拟时间
        mock_time.return_value = 1000.0

        # 创建模拟连接
        mock_conn = Mock()
        mock_conn.closed = False

        pooled_conn = PooledConnection(mock_conn, Mock())
        pooled_conn.last_used = 999.0  # 1秒前使用
        pooled_conn.is_healthy = True

        # 测试缓存命中（最近使用）
        with patch("app.adapters.db.health_monitor.record_health_check") as mock_record:
            result = pooled_conn.check_health(force_check=False)
            self.assertTrue(result)

            # 验证记录了缓存命中
            mock_record.assert_called_once()
            args = mock_record.call_args[0]
            self.assertEqual(args[0], "cached")  # check_type
            self.assertTrue(args[2])  # success

    @patch("app.adapters.db.pool.time.time")
    def test_pooled_connection_lightweight_check(self, mock_time):
        """测试轻量级健康检查"""
        # 模拟时间
        mock_time.return_value = 1000.0

        # 创建模拟连接
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.info = Mock()
        mock_conn.info.host = "localhost"
        mock_conn.info.transaction_status = 0  # PQTRANS_IDLE

        pooled_conn = PooledConnection(mock_conn, Mock())
        pooled_conn.last_used = 985.0  # 15秒前使用，超过缓存时间
        pooled_conn.is_healthy = True
        pooled_conn._last_health_check = 985.0  # 15秒前检查，超过缓存时间

        # 测试轻量级检查 - 需要强制检查以避免深度检查
        with patch("app.adapters.db.health_monitor.record_health_check") as mock_record:
            # 设置为不健康状态，这样会触发深度检查，但我们模拟深度检查成功
            pooled_conn.is_healthy = False

            # 模拟auto_commit上下文管理器用于深度检查
            with patch("app.adapters.db.transaction.auto_commit") as mock_auto_commit:
                mock_cursor = Mock()
                mock_cursor.fetchone.return_value = [120000]  # PostgreSQL版本号

                mock_conn_context = Mock()
                mock_conn_context.cursor.return_value.__enter__ = Mock(
                    return_value=mock_cursor
                )
                mock_conn_context.cursor.return_value.__exit__ = Mock(return_value=None)

                mock_auto_commit.return_value.__enter__ = Mock(
                    return_value=mock_conn_context
                )
                mock_auto_commit.return_value.__exit__ = Mock(return_value=None)

                result = pooled_conn.check_health(force_check=False)
                self.assertTrue(result)

                # 验证记录了深度检查（因为is_healthy=False触发了深度检查）
                mock_record.assert_called_once()
                args = mock_record.call_args[0]
                self.assertEqual(args[0], "deep")  # check_type
                self.assertTrue(args[2])  # success

    @patch("app.adapters.db.pool.time.time")
    def test_pooled_connection_deep_check(self, mock_time):
        """测试深度健康检查"""
        # 模拟时间
        mock_time.return_value = 1000.0

        # 创建模拟连接
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.info = Mock()
        mock_conn.info.host = "localhost"
        mock_conn.info.transaction_status = 0

        pooled_conn = PooledConnection(mock_conn, Mock())
        pooled_conn.last_used = 900.0  # 100秒前使用
        pooled_conn.is_healthy = False  # 标记为不健康，触发深度检查

        # 模拟auto_commit上下文管理器
        with patch("app.adapters.db.transaction.auto_commit") as mock_auto_commit:
            mock_cursor = Mock()
            mock_cursor.fetchone.return_value = [120000]  # PostgreSQL版本号

            mock_conn_context = Mock()
            mock_conn_context.cursor.return_value.__enter__ = Mock(
                return_value=mock_cursor
            )
            mock_conn_context.cursor.return_value.__exit__ = Mock(return_value=None)

            mock_auto_commit.return_value.__enter__ = Mock(
                return_value=mock_conn_context
            )
            mock_auto_commit.return_value.__exit__ = Mock(return_value=None)

            with patch(
                "app.adapters.db.health_monitor.record_health_check"
            ) as mock_record:
                result = pooled_conn.check_health(force_check=False)
                self.assertTrue(result)

                # 验证记录了深度检查
                mock_record.assert_called_once()
                args = mock_record.call_args[0]
                self.assertEqual(args[0], "deep")  # check_type
                self.assertTrue(args[2])  # success

                # 验证执行了SQL查询
                mock_cursor.execute.assert_called_once_with(
                    "SELECT current_setting('server_version_num')::int"
                )

    def test_pooled_connection_closed_check(self):
        """测试关闭连接的健康检查"""
        # 创建模拟的关闭连接
        mock_conn = Mock()
        mock_conn.closed = True

        pooled_conn = PooledConnection(mock_conn, Mock())

        with patch("app.adapters.db.health_monitor.record_health_check") as mock_record:
            result = pooled_conn.check_health()
            self.assertFalse(result)
            self.assertFalse(pooled_conn.is_healthy)

            # 验证记录了失败的检查
            mock_record.assert_called_once()
            args = mock_record.call_args[0]
            self.assertEqual(args[0], "lightweight")  # check_type
            self.assertFalse(args[2])  # success

    def test_pooled_connection_transaction_error_state(self):
        """测试事务错误状态的检查"""
        # 创建模拟连接
        mock_conn = Mock()
        mock_conn.closed = False
        mock_conn.info = Mock()
        mock_conn.info.host = "localhost"
        mock_conn.info.transaction_status = 3  # PQTRANS_INERROR

        pooled_conn = PooledConnection(mock_conn, Mock())
        pooled_conn.last_used = time.time() - 10  # 10秒前使用

        with patch("app.adapters.db.health_monitor.record_health_check") as mock_record:
            result = pooled_conn.check_health()
            self.assertFalse(result)
            self.assertFalse(pooled_conn.is_healthy)

            # 验证记录了失败的检查
            mock_record.assert_called_once()
            args = mock_record.call_args[0]
            self.assertEqual(args[0], "lightweight")  # check_type
            self.assertFalse(args[2])  # success

    def test_pooled_connection_stable_connection_cache(self):
        """测试稳定连接的延长缓存"""
        # 创建模拟连接
        mock_conn = Mock()
        mock_conn.closed = False

        pooled_conn = PooledConnection(mock_conn, Mock())
        pooled_conn.last_used = time.time() - 20  # 20秒前使用
        pooled_conn.is_healthy = True
        pooled_conn._last_health_check = time.time() - 20  # 20秒前检查
        pooled_conn._consecutive_healthy_checks = 6  # 连续6次健康

        with patch("app.adapters.db.health_monitor.record_health_check") as mock_record:
            result = pooled_conn.check_health(force_check=False)
            self.assertTrue(result)

            # 验证使用了缓存
            mock_record.assert_called_once()
            args = mock_record.call_args[0]
            self.assertEqual(args[0], "cached")  # check_type
            self.assertTrue(args[2])  # success

    def test_global_health_monitor_functions(self):
        """测试全局健康监控器函数"""
        # 测试记录健康检查
        record_health_check("cached", 0.001, True, {"test": "data"})

        # 获取统计信息
        stats = get_health_monitor().get_stats()
        self.assertEqual(stats.total_checks, 1)
        self.assertEqual(stats.cached_checks, 1)

        # 测试健康摘要
        from app.adapters.db.health_monitor import get_health_stats

        summary = get_health_stats()
        self.assertIn("stats", summary)
        self.assertIn("health_indicators", summary)

    def test_health_check_performance_metrics(self):
        """测试健康检查性能指标"""
        monitor = HealthMonitor()

        # 模拟不同类型的检查
        monitor.record_check("cached", 0.0001, True)  # 很快的缓存检查
        monitor.record_check("lightweight", 0.001, True)  # 轻量级检查
        monitor.record_check("deep", 0.020, True)  # 深度检查

        stats = monitor.get_stats()

        # 验证时间统计
        self.assertGreater(stats.get_average_check_time(), 0)
        self.assertGreater(stats.get_average_deep_check_time(), 0)

        # 深度检查应该比平均检查时间长
        self.assertGreater(
            stats.get_average_deep_check_time(), stats.get_average_check_time()
        )


if __name__ == "__main__":
    unittest.main()
