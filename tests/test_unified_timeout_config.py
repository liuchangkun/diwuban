"""
测试统一连接超时配置
"""

import unittest
from unittest.mock import Mock, patch

from app.core.config.database import DbTimeoutSettings
from app.adapters.db.pool import ConnectionPool
from app.core.config.loader_new import (
    Settings,
    DbSettings,
    DbPoolSettings,
    DbRetrySettings,
)


class TestUnifiedTimeoutConfig(unittest.TestCase):
    """测试统一超时配置"""

    def test_timeout_settings_conversion_methods(self):
        """测试超时配置的转换方法"""
        timeouts = DbTimeoutSettings(
            connect_timeout_ms=5000,
            statement_timeout_ms=30000,
            query_timeout_ms=60000,
            connection_acquire_timeout_ms=10000,
            connection_validation_timeout_ms=1000,
            pool_shutdown_timeout_ms=30000,
        )

        # 测试秒转换
        self.assertEqual(timeouts.connect_timeout_seconds(), 5.0)
        self.assertEqual(timeouts.query_timeout_seconds(), 60.0)
        self.assertEqual(timeouts.connection_acquire_timeout_seconds(), 10.0)
        self.assertEqual(timeouts.connection_validation_timeout_seconds(), 1.0)
        self.assertEqual(timeouts.pool_shutdown_timeout_seconds(), 30.0)

        # 测试SQL语句生成
        self.assertEqual(
            timeouts.statement_timeout_sql(), "SET statement_timeout TO '30000ms'"
        )

    def test_timeout_settings_validation(self):
        """测试超时配置验证"""
        # 正常配置
        valid_timeouts = DbTimeoutSettings()
        errors = valid_timeouts.validate()
        self.assertEqual(len(errors), 0)

        # 负数超时
        invalid_timeouts = DbTimeoutSettings(connect_timeout_ms=-1)
        errors = invalid_timeouts.validate()
        self.assertIn("connect_timeout_ms 必须大于 0", errors)

        # 超时过大
        large_timeouts = DbTimeoutSettings(connect_timeout_ms=400000)  # 超过5分钟
        errors = large_timeouts.validate()
        self.assertIn("connect_timeout_ms 不应超过 300000ms (5分钟)", errors)

        # 逻辑关系错误
        logic_error_timeouts = DbTimeoutSettings(
            statement_timeout_ms=70000, query_timeout_ms=60000  # 大于query_timeout_ms
        )
        errors = logic_error_timeouts.validate()
        self.assertIn("statement_timeout_ms 不应大于 query_timeout_ms", errors)

    def test_timeout_settings_to_dict(self):
        """测试超时配置字典转换"""
        timeouts = DbTimeoutSettings(
            connect_timeout_ms=5000,
            statement_timeout_ms=30000,
            query_timeout_ms=60000,
        )

        timeout_dict = timeouts.to_dict()

        # 验证毫秒单位
        self.assertEqual(timeout_dict["connect_timeout_ms"], 5000)
        self.assertEqual(timeout_dict["statement_timeout_ms"], 30000)
        self.assertEqual(timeout_dict["query_timeout_ms"], 60000)

        # 验证秒单位
        self.assertEqual(timeout_dict["connect_timeout_seconds"], 5.0)
        self.assertEqual(timeout_dict["statement_timeout_seconds"], 30.0)
        self.assertEqual(timeout_dict["query_timeout_seconds"], 60.0)

        # 验证SQL语句
        self.assertEqual(
            timeout_dict["statement_timeout_sql"], "SET statement_timeout TO '30000ms'"
        )

    @patch("app.adapters.db.pool.psycopg.connect")
    def test_connection_pool_uses_unified_timeouts(self, mock_connect):
        """测试连接池使用统一超时配置"""
        # 模拟数据库连接
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock()
        mock_connect.return_value = mock_conn

        # 创建自定义超时配置
        custom_timeouts = DbTimeoutSettings(
            connect_timeout_ms=8000,
            statement_timeout_ms=45000,
            connection_acquire_timeout_ms=15000,
            connection_validation_timeout_ms=2000,
            pool_shutdown_timeout_ms=60000,
        )

        settings = Settings(
            db=DbSettings(
                host="localhost",
                name="test_db",
                user="test_user",
                timeouts=custom_timeouts,
                pool=DbPoolSettings(min_size=1, max_size=5),
                retry=DbRetrySettings(max_retries=3),
            )
        )

        pool = ConnectionPool(settings)

        try:
            # 验证预计算的超时值
            self.assertEqual(pool._connect_timeout, 8)  # 8000ms -> 8s (整数)
            self.assertEqual(
                pool._statement_timeout_sql, "SET statement_timeout TO '45000ms'"
            )
            self.assertEqual(pool._connection_acquire_timeout, 15.0)  # 15000ms -> 15.0s
            self.assertEqual(pool._connection_validation_timeout, 2.0)  # 2000ms -> 2.0s
            self.assertEqual(pool._pool_shutdown_timeout, 60.0)  # 60000ms -> 60.0s

            # 验证连接创建时使用正确的超时
            pool._create_connection()
            mock_connect.assert_called_with(
                pool._dsn,
                connect_timeout=8,  # 使用预计算的整数超时值
            )

            # 验证语句超时设置
            mock_cursor.execute.assert_called_with("SET statement_timeout TO '45000ms'")

        finally:
            pool.close()

    def test_timeout_config_backward_compatibility(self):
        """测试超时配置向后兼容性"""
        # 只设置基础超时配置，新配置应使用默认值
        basic_timeouts = DbTimeoutSettings(
            connect_timeout_ms=3000,
            statement_timeout_ms=20000,
            query_timeout_ms=40000,
        )

        # 验证新配置字段有默认值
        self.assertEqual(basic_timeouts.connection_acquire_timeout_ms, 10000)
        self.assertEqual(basic_timeouts.connection_validation_timeout_ms, 1000)
        self.assertEqual(basic_timeouts.pool_shutdown_timeout_ms, 30000)

        # 验证转换方法正常工作
        self.assertEqual(basic_timeouts.connect_timeout_seconds(), 3.0)
        self.assertEqual(basic_timeouts.connection_acquire_timeout_seconds(), 10.0)

    def test_timeout_edge_cases(self):
        """测试超时配置边界情况"""
        # 最小有效值
        min_timeouts = DbTimeoutSettings(
            connect_timeout_ms=1,
            statement_timeout_ms=1,
            query_timeout_ms=1,
            connection_acquire_timeout_ms=1,
            connection_validation_timeout_ms=1,
            pool_shutdown_timeout_ms=1,
        )
        errors = min_timeouts.validate()
        self.assertEqual(len(errors), 0)

        # 最大有效值
        max_timeouts = DbTimeoutSettings(
            connect_timeout_ms=300000,  # 5分钟
            statement_timeout_ms=3600000,  # 1小时
            query_timeout_ms=7200000,  # 2小时
            connection_acquire_timeout_ms=60000,  # 1分钟
            connection_validation_timeout_ms=10000,  # 10秒
            pool_shutdown_timeout_ms=300000,  # 5分钟
        )
        errors = max_timeouts.validate()
        self.assertEqual(len(errors), 0)

        # 超过最大值
        over_max_timeouts = DbTimeoutSettings(
            connect_timeout_ms=300001,  # 超过5分钟
            statement_timeout_ms=3600001,  # 超过1小时
            query_timeout_ms=7200001,  # 超过2小时
            connection_acquire_timeout_ms=60001,  # 超过1分钟
            connection_validation_timeout_ms=10001,  # 超过10秒
            pool_shutdown_timeout_ms=300001,  # 超过5分钟
        )
        errors = over_max_timeouts.validate()
        self.assertEqual(len(errors), 6)  # 所有字段都超过最大值

    def test_timeout_precision_conversion(self):
        """测试超时转换精度"""
        # 测试毫秒到秒的精确转换
        timeouts = DbTimeoutSettings(
            connect_timeout_ms=1500,  # 1.5秒
            statement_timeout_ms=2500,  # 2.5秒
            query_timeout_ms=3333,  # 3.333秒
        )

        self.assertEqual(timeouts.connect_timeout_seconds(), 1.5)
        self.assertEqual(timeouts.statement_timeout_ms / 1000.0, 2.5)
        self.assertEqual(timeouts.query_timeout_seconds(), 3.333)

        # 验证字典输出的精度
        timeout_dict = timeouts.to_dict()
        self.assertEqual(timeout_dict["connect_timeout_seconds"], 1.5)
        self.assertEqual(timeout_dict["statement_timeout_seconds"], 2.5)
        self.assertEqual(timeout_dict["query_timeout_seconds"], 3.333)

    def test_timeout_config_integration_with_validation(self):
        """测试超时配置与验证的集成"""
        from app.core.config.validation import ConfigValidator

        # 有效的超时配置
        valid_db_config = {
            "host": "localhost",
            "dbname": "test_db",
            "user": "test_user",
            "timeouts": {
                "connect_timeout_ms": 5000,
                "statement_timeout_ms": 30000,
                "query_timeout_ms": 60000,
                "connection_acquire_timeout_ms": 10000,
                "connection_validation_timeout_ms": 1000,
                "pool_shutdown_timeout_ms": 30000,
            },
            "pool": {
                "min_size": 1,
                "max_size": 10,
            },
        }

        result = ConfigValidator.validate_database_config(valid_db_config)
        if not result.is_valid:
            print(f"验证失败，错误信息: {[error.message for error in result.errors]}")
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)

        # 无效的超时配置
        invalid_db_config = {
            "host": "localhost",
            "dbname": "test_db",
            "user": "test_user",
            "timeouts": {
                "connect_timeout_ms": -1,  # 负数
                "statement_timeout_ms": 70000,  # 大于query_timeout_ms
                "query_timeout_ms": 60000,
                "connection_validation_timeout_ms": 15000,  # 大于connection_acquire_timeout_ms
                "connection_acquire_timeout_ms": 10000,
            },
            "pool": {
                "min_size": 1,
                "max_size": 10,
            },
        }

        result = ConfigValidator.validate_database_config(invalid_db_config)
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)

        # 验证错误信息包含预期内容
        error_messages = [error.message for error in result.errors]
        self.assertTrue(
            any("connect_timeout_ms 必须大于 0" in msg for msg in error_messages)
        )


if __name__ == "__main__":
    unittest.main()
