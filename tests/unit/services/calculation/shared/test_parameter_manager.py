"""
ParameterManager 单元测试

测试范围：
- 三级参数合并（全局 → 泵站 → 设备）
- 参数缓存
- 参数更新
- 缓存清除
"""

import pytest
from unittest.mock import MagicMock, patch

from app.services.calculation.shared.parameter_manager import ParameterManager


class TestParameterManager:
    """ParameterManager 单元测试"""

    @pytest.fixture
    def parameter_manager(self, mock_db_connection):
        """创建 ParameterManager 实例"""
        with patch('app.services.calculation.shared.parameter_manager.get_connection', return_value=mock_db_connection):
            manager = ParameterManager()
            manager._instance = None  # 重置单例
            return ParameterManager()

    def test_get_parameters_global(self, parameter_manager, mock_db_connection):
        """测试：获取全局参数"""
        # Mock 数据库查询结果（只有全局参数）
        cursor = mock_db_connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [
            ('alpha', '1.0'),
            ('beta', '1.0')
        ]

        # 执行查询
        params = parameter_manager.get_parameters(
            metric_key='pump_flow_rate',
            method_id='method_a',
            station_id=None,
            device_id=None
        )

        # 断言
        assert params == {'alpha': 1.0, 'beta': 1.0}
        assert cursor.execute.called

    def test_get_parameters_station_override(self, parameter_manager, mock_db_connection):
        """测试：泵站级参数覆盖全局参数"""
        # Mock 数据库查询结果（全局 + 泵站）
        cursor = mock_db_connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [
            ('alpha', '1.5'),  # 泵站级覆盖
            ('beta', '1.0')    # 全局级
        ]

        # 执行查询
        params = parameter_manager.get_parameters(
            metric_key='pump_flow_rate',
            method_id='method_a',
            station_id=1,
            device_id=None
        )

        # 断言
        assert params['alpha'] == 1.5  # 泵站级
        assert params['beta'] == 1.0   # 全局级

    def test_get_parameters_device_override(self, parameter_manager, mock_db_connection):
        """测试：设备级参数覆盖泵站和全局参数"""
        # Mock 数据库查询结果（全局 + 泵站 + 设备）
        cursor = mock_db_connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [
            ('alpha', '2.0'),  # 设备级覆盖
            ('beta', '1.0')    # 全局级
        ]

        # 执行查询
        params = parameter_manager.get_parameters(
            metric_key='pump_flow_rate',
            method_id='method_a',
            station_id=1,
            device_id=105
        )

        # 断言
        assert params['alpha'] == 2.0  # 设备级
        assert params['beta'] == 1.0   # 全局级

    def test_parameter_caching(self, parameter_manager, mock_db_connection):
        """测试：参数缓存"""
        # Mock 数据库查询结果
        cursor = mock_db_connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [
            ('alpha', '1.0'),
            ('beta', '1.0')
        ]

        # 第一次查询（从数据库）
        params1 = parameter_manager.get_parameters(
            metric_key='pump_flow_rate',
            method_id='method_a',
            station_id=1,
            device_id=105
        )

        # 第二次查询（从缓存）
        params2 = parameter_manager.get_parameters(
            metric_key='pump_flow_rate',
            method_id='method_a',
            station_id=1,
            device_id=105
        )

        # 断言：两次结果相同
        assert params1 == params2
        # 断言：只调用了一次数据库查询
        assert cursor.execute.call_count == 1

    def test_clear_cache(self, parameter_manager, mock_db_connection):
        """测试：清除缓存"""
        # Mock 数据库查询结果
        cursor = mock_db_connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [
            ('alpha', '1.0'),
            ('beta', '1.0')
        ]

        # 第一次查询（从数据库）
        parameter_manager.get_parameters(
            metric_key='pump_flow_rate',
            method_id='method_a',
            station_id=1,
            device_id=105
        )

        # 清除缓存
        parameter_manager.clear_cache()

        # 第二次查询（从数据库，因为缓存已清除）
        parameter_manager.get_parameters(
            metric_key='pump_flow_rate',
            method_id='method_a',
            station_id=1,
            device_id=105
        )

        # 断言：调用了两次数据库查询
        assert cursor.execute.call_count == 2

    def test_update_params(self, parameter_manager, mock_db_connection):
        """测试：更新参数"""
        # Mock 数据库操作
        cursor = mock_db_connection.cursor.return_value.__enter__.return_value

        # 执行更新
        parameter_manager.update_params(
            metric_key='pump_flow_rate',
            method_id='method_a',
            station_id=1,
            device_id=105,
            params={'alpha': 2.0, 'beta': 1.5}
        )

        # 断言：调用了 executemany
        assert cursor.executemany.called

    def test_reload_cache(self, parameter_manager, mock_db_connection):
        """测试：重新加载缓存"""
        # Mock 数据库查询结果
        cursor = mock_db_connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [
            ('alpha', '1.0'),
            ('beta', '1.0')
        ]

        # 第一次查询
        parameter_manager.get_parameters(
            metric_key='pump_flow_rate',
            method_id='method_a',
            station_id=1,
            device_id=105
        )

        # 重新加载缓存
        parameter_manager.reload_cache()

        # 断言：调用了两次数据库查询（第一次 + reload）
        assert cursor.execute.call_count == 2

    def test_singleton_pattern(self):
        """测试：单例模式"""
        # 创建两个实例
        manager1 = ParameterManager()
        manager2 = ParameterManager()

        # 断言：应该是同一个实例
        assert manager1 is manager2

    def test_get_default_params(self, parameter_manager):
        """测试：获取默认参数"""
        # 执行查询（使用默认参数）
        params = parameter_manager._get_default_params('pump_flow_rate', 'method_a')

        # 断言：返回默认参数
        assert isinstance(params, dict)
        assert 'alpha' in params or 'beta' in params or len(params) == 0

