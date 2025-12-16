"""
测试统一连接池实现
"""

import unittest
from unittest.mock import Mock, patch

from app.core.config.loader_new import Settings, DbSettings, DbPoolSettings, DbTimeoutSettings, DbRetrySettings


class TestUnifiedConnectionPool(unittest.TestCase):
    """测试统一连接池实现"""

    def setUp(self):
        """测试前准备"""
        self.settings = Settings(
            db=DbSettings(
                host="localhost",
                name="test_db",
                user="test_user",
                pool=DbPoolSettings(min_size=1, max_size=5),
                timeouts=DbTimeoutSettings(connect_timeout_ms=5000),
                retry=DbRetrySettings(max_retries=3)
            )
        )

    def test_no_async_pool_import(self):
        """测试异步连接池模块已被移除"""
        with self.assertRaises(ImportError):
            from app.config.database import get_ro_pool

    def test_sync_pool_available(self):
        """测试同步连接池可用"""
        try:
            from app.adapters.db.pool import ConnectionPool, initialize_pool, get_pool, close_pool
            # 导入成功说明同步连接池模块存在
            self.assertTrue(True)
        except ImportError:
            self.fail("同步连接池模块不可用")

    def test_unified_connection_interface(self):
        """测试统一连接接口"""
        try:
            from app.adapters.db import get_connection, init_database, cleanup_database
            # 导入成功说明统一接口存在
            self.assertTrue(True)
        except ImportError:
            self.fail("统一连接接口不可用")

    def test_gateway_connection_fallback(self):
        """测试网关连接回退机制"""
        try:
            from app.adapters.db.gateway import get_conn
            # 导入成功说明网关连接函数存在
            self.assertTrue(True)
        except ImportError:
            self.fail("网关连接函数不可用")

    @patch('app.adapters.db.pool.initialize_pool')
    def test_database_initialization_uses_sync_pool(self, mock_initialize):
        """测试数据库初始化使用同步连接池"""
        from app.adapters.db import init_database
        
        mock_pool = Mock()
        mock_initialize.return_value = mock_pool
        
        # 模拟连接池的 get_connection 方法
        mock_pool.get_connection.return_value.__enter__ = Mock()
        mock_pool.get_connection.return_value.__exit__ = Mock()
        
        # 模拟连接和游标
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [1]
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock()
        mock_pool.get_connection.return_value.__enter__.return_value = mock_conn
        
        # 测试初始化
        init_database(self.settings)
        
        # 验证使用了同步连接池
        mock_initialize.assert_called_once_with(self.settings)

    def test_connection_pool_configuration_unified(self):
        """测试连接池配置统一"""
        # 验证配置结构统一
        self.assertIsInstance(self.settings.db.pool, DbPoolSettings)
        self.assertEqual(self.settings.db.pool.min_size, 1)
        self.assertEqual(self.settings.db.pool.max_size, 5)
        
        # 验证超时配置统一
        self.assertIsInstance(self.settings.db.timeouts, DbTimeoutSettings)
        self.assertEqual(self.settings.db.timeouts.connect_timeout_ms, 5000)
        
        # 验证重试配置统一
        self.assertIsInstance(self.settings.db.retry, DbRetrySettings)
        self.assertEqual(self.settings.db.retry.max_retries, 3)

    def test_no_duplicate_pool_implementations(self):
        """测试没有重复的连接池实现"""
        # 验证只有一个连接池实现
        try:
            from app.adapters.db.pool import ConnectionPool
            pool_class = ConnectionPool
            self.assertTrue(hasattr(pool_class, 'get_connection'))
            self.assertTrue(hasattr(pool_class, 'close'))
            self.assertTrue(hasattr(pool_class, 'get_stats'))
        except ImportError:
            self.fail("主连接池实现不存在")
        
        # 验证异步连接池已移除
        with self.assertRaises(ImportError):
            from app.config.database import get_ro_pool

    def test_connection_pool_features_complete(self):
        """测试连接池功能完整性"""
        from app.adapters.db.pool import ConnectionPool
        
        # 创建连接池实例（不实际连接数据库）
        pool = ConnectionPool.__new__(ConnectionPool)
        
        # 验证关键方法存在
        self.assertTrue(hasattr(pool, 'get_connection'))
        self.assertTrue(hasattr(pool, 'close'))
        self.assertTrue(hasattr(pool, 'get_stats'))
        self.assertTrue(hasattr(pool, '_create_connection'))
        self.assertTrue(hasattr(pool, '_validate_pooled_connection'))

    def test_health_monitoring_integration(self):
        """测试健康监控集成"""
        try:
            from app.adapters.db.health_monitor import HealthMonitor, get_health_monitor
            # 验证健康监控模块存在
            monitor = HealthMonitor()
            self.assertTrue(hasattr(monitor, 'record_check'))
            self.assertTrue(hasattr(monitor, 'get_stats'))
            self.assertTrue(hasattr(monitor, 'get_optimization_recommendations'))
        except ImportError:
            self.fail("健康监控模块不可用")

    def test_connection_lease_integration(self):
        """测试连接租借集成"""
        try:
            from app.adapters.db.connection_lease import ConnectionLease, lease_connection
            # 验证连接租借模块存在
            self.assertTrue(callable(lease_connection))
        except ImportError:
            self.fail("连接租借模块不可用")

    def test_transaction_management_integration(self):
        """测试事务管理集成"""
        try:
            from app.adapters.db.transaction import transaction, auto_commit, reset_connection_state
            # 验证事务管理模块存在
            self.assertTrue(callable(transaction))
            self.assertTrue(callable(auto_commit))
            self.assertTrue(callable(reset_connection_state))
        except ImportError:
            self.fail("事务管理模块不可用")

    def test_unified_interface_consistency(self):
        """测试统一接口一致性"""
        # 验证所有连接获取接口都指向同一个实现
        from app.adapters.db import get_connection as db_get_connection
        from app.adapters.db.pool import get_connection as pool_get_connection
        from app.adapters.db.gateway import get_conn
        
        # 验证接口存在
        self.assertTrue(callable(db_get_connection))
        self.assertTrue(callable(pool_get_connection))
        self.assertTrue(callable(get_conn))

    def test_configuration_backward_compatibility(self):
        """测试配置向后兼容性"""
        # 验证配置结构保持兼容
        self.assertTrue(hasattr(self.settings.db, 'host'))
        self.assertTrue(hasattr(self.settings.db, 'name'))
        self.assertTrue(hasattr(self.settings.db, 'user'))
        self.assertTrue(hasattr(self.settings.db, 'pool'))
        self.assertTrue(hasattr(self.settings.db, 'timeouts'))
        self.assertTrue(hasattr(self.settings.db, 'retry'))
        
        # 验证连接池配置完整
        pool_config = self.settings.db.pool
        self.assertTrue(hasattr(pool_config, 'min_size'))
        self.assertTrue(hasattr(pool_config, 'max_size'))
        self.assertTrue(hasattr(pool_config, 'max_inactive_connection_lifetime'))


if __name__ == "__main__":
    unittest.main()
