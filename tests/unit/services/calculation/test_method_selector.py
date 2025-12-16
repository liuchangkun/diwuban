"""
测试 calculation/method_selector.py - 方法选择器

测试场景:
1. 初始化测试 (2个)
2. 依赖检查测试 (4个)
3. 条件判断测试 (5个)
4. 方法选择测试 (4个)

总计: 15个测试场景
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from app.services.calculation.method_selector import MethodSelector


class TestMethodSelectorInitialization:
    """方法选择器初始化测试"""

    @patch('app.services.calculation.method_selector.get_connection')
    def test_initialization_loads_methods_from_db(self, mock_get_conn):
        """场景1: 初始化时从数据库加载方法注册表"""
        # Mock数据库连接和查询结果
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('method_001', 'pump_flow_rate', 'Method A', 'A', 10, ['dep1'], {'cond1': 'val1'}, 'high', True, ['pump']),
            ('method_002', 'pump_flow_rate', 'Method B', 'B', 5, ['dep2'], {'cond2': 'val2'}, 'medium', True, ['pump']),
            ('method_003', 'pump_head', 'Method C', 'C', 8, [], {}, 'high', True, []),
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        # 创建选择器
        selector = MethodSelector()
        
        # 验证注册表已加载
        assert 'pump_flow_rate' in selector._method_registry
        assert 'pump_head' in selector._method_registry
        assert len(selector._method_registry['pump_flow_rate']) == 2
        assert len(selector._method_registry['pump_head']) == 1

    @patch('app.services.calculation.method_selector.get_connection')
    def test_initialization_handles_db_error(self, mock_get_conn):
        """场景2: 初始化时数据库错误应该抛出异常"""
        # Mock数据库连接失败
        mock_get_conn.side_effect = Exception("Database connection failed")
        
        # 验证抛出异常
        with pytest.raises(Exception) as exc_info:
            MethodSelector()
        
        assert "Database connection failed" in str(exc_info.value)


class TestDependencyChecking:
    """依赖检查测试"""

    @patch('app.services.calculation.method_selector.get_connection')
    def test_check_dependencies_all_satisfied(self, mock_get_conn):
        """场景3: 所有依赖都满足"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        selector = MethodSelector()
        
        # 测试依赖检查
        dependencies = ['pump_active_power', 'pump_frequency']
        available_metrics = ['pump_active_power', 'pump_frequency', 'pump_inlet_pressure']
        
        result = selector.check_dependencies(dependencies, available_metrics)
        
        assert result is True

    @patch('app.services.calculation.method_selector.get_connection')
    def test_check_dependencies_missing(self, mock_get_conn):
        """场景4: 部分依赖缺失"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        selector = MethodSelector()
        
        # 测试依赖检查
        dependencies = ['pump_active_power', 'pump_frequency', 'pump_flow_rate']
        available_metrics = ['pump_active_power', 'pump_frequency']
        
        result = selector.check_dependencies(dependencies, available_metrics)
        
        assert result is False

    @patch('app.services.calculation.method_selector.get_connection')
    def test_check_dependencies_with_valid_data(self, mock_get_conn):
        """场景5: 检查依赖数据有效性（有效数据）"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        selector = MethodSelector()
        
        # 准备测试数据
        dependencies = ['pump_frequency', 'pump_power']
        available_metrics = ['pump_frequency', 'pump_power']
        data = {
            'pump_frequency': np.array([50.0, 50.5, 49.8, 50.2]),
            'pump_power': np.array([100.0, 105.0, 98.0, 102.0])
        }
        
        result = selector.check_dependencies(dependencies, available_metrics, data)
        
        assert result is True

    @patch('app.services.calculation.method_selector.get_connection')
    def test_check_dependencies_with_invalid_data(self, mock_get_conn):
        """场景6: 检查依赖数据有效性（全部为NaN）"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        selector = MethodSelector()
        
        # 准备测试数据（全部为NaN）
        dependencies = ['pump_frequency']
        available_metrics = ['pump_frequency']
        data = {
            'pump_frequency': np.array([np.nan, np.nan, np.nan])
        }
        
        result = selector.check_dependencies(dependencies, available_metrics, data)
        
        assert result is False


class TestConditionChecking:
    """条件判断测试"""

    @patch('app.services.calculation.method_selector.get_connection')
    def test_check_conditions_empty_conditions(self, mock_get_conn):
        """场景7: 空条件应该返回True"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        selector = MethodSelector()
        
        result = selector.check_conditions({}, {'running_count': 2})
        
        assert result is True

    @patch('app.services.calculation.method_selector.get_connection')
    def test_check_conditions_exact_match(self, mock_get_conn):
        """场景8: 精确匹配条件"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        selector = MethodSelector()
        
        conditions = {'running_count': {'exact': 2}}
        context = {'running_count': 2}
        
        result = selector.check_conditions(conditions, context)
        
        assert result is True

    @patch('app.services.calculation.method_selector.get_connection')
    def test_check_conditions_min_max_range(self, mock_get_conn):
        """场景9: 最小最大范围条件"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        selector = MethodSelector()
        
        conditions = {'running_count': {'min': 1, 'max': 5}}
        context = {'running_count': 3}
        
        result = selector.check_conditions(conditions, context)
        
        assert result is True

    @patch('app.services.calculation.method_selector.get_connection')
    def test_check_conditions_min_running_pumps(self, mock_get_conn):
        """场景10: min_running_pumps条件"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        selector = MethodSelector()
        
        conditions = {'min_running_pumps': 2}
        context = {'running_count': 3}
        
        result = selector.check_conditions(conditions, context)
        
        assert result is True

    @patch('app.services.calculation.method_selector.get_connection')
    def test_check_conditions_not_satisfied(self, mock_get_conn):
        """场景11: 条件不满足"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        selector = MethodSelector()
        
        conditions = {'running_count': {'exact': 2}}
        context = {'running_count': 3}
        
        result = selector.check_conditions(conditions, context)
        
        assert result is False


class TestMethodSelection:
    """方法选择测试"""

    @patch('app.services.calculation.method_selector.get_connection')
    def test_select_method_success(self, mock_get_conn):
        """场景12: 成功选择方法"""
        # Mock数据库返回方法
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('method_001', 'pump_flow_rate', 'Method A', 'A', 10, ['pump_power'], {}, 'high', True, []),
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        selector = MethodSelector()
        
        # 选择方法
        method = selector.select_method(
            'pump_flow_rate',
            ['pump_power', 'pump_frequency'],
            {}
        )
        
        assert method is not None
        assert method['method_code'] == 'A'

    @patch('app.services.calculation.method_selector.get_connection')
    def test_select_method_no_methods_registered(self, mock_get_conn):
        """场景13: 没有注册的方法"""
        # Mock数据库返回空
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        selector = MethodSelector()
        
        # 选择方法
        method = selector.select_method(
            'unknown_metric',
            ['pump_power'],
            {}
        )
        
        assert method is None

    @patch('app.services.calculation.method_selector.get_connection')
    def test_select_method_dependencies_not_satisfied(self, mock_get_conn):
        """场景14: 依赖不满足"""
        # Mock数据库返回方法
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('method_001', 'pump_flow_rate', 'Method A', 'A', 10, ['pump_power', 'pump_frequency'], {}, 'high', True, []),
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        selector = MethodSelector()
        
        # 选择方法（缺少pump_frequency）
        method = selector.select_method(
            'pump_flow_rate',
            ['pump_power'],  # 缺少pump_frequency
            {}
        )
        
        assert method is None

    @patch('app.services.calculation.method_selector.get_connection')
    def test_get_union_dependencies(self, mock_get_conn):
        """场景15: 获取指标所有方法的依赖并集"""
        # Mock数据库返回多个方法
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('method_001', 'pump_flow_rate', 'Method A', 'A', 10, ['dep1', 'dep2'], {}, 'high', True, []),
            ('method_002', 'pump_flow_rate', 'Method B', 'B', 5, ['dep2', 'dep3'], {}, 'medium', True, []),
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        selector = MethodSelector()
        
        # 获取依赖并集
        deps = selector.get_union_dependencies('pump_flow_rate')
        
        # 验证去重和排序
        assert deps == ['dep1', 'dep2', 'dep3']
        assert isinstance(deps, list)

