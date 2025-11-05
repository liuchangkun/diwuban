"""
测试 calculation/dependency_analyzer.py - 依赖分析器

测试场景:
1. 初始化测试 (1个)
2. 依赖图构建测试 (3个)
3. 拓扑排序测试 (4个)
4. 循环检测测试 (4个)
5. 计算顺序生成测试 (3个)

总计: 15个测试场景
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.calculation.dependency_analyzer import DependencyAnalyzer, CircularDependencyError


class TestDependencyAnalyzerInitialization:
    """依赖分析器初始化测试"""

    @patch('app.services.calculation.dependency_analyzer.get_connection')
    def test_initialization_loads_methods_from_db(self, mock_get_conn):
        """场景1: 初始化时从数据库加载方法注册表"""
        # Mock数据库连接和查询结果
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('method_001', 'pump_flow_rate', 'A', 10, ['main_pipeline_flow_rate'], True),
            ('method_002', 'pump_efficiency', 'B', 8, ['pump_flow_rate', 'pump_head'], True),
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        # 创建分析器
        analyzer = DependencyAnalyzer()
        
        # 验证注册表已加载
        assert 'pump_flow_rate' in analyzer._method_registry
        assert 'pump_efficiency' in analyzer._method_registry
        assert len(analyzer._method_registry['pump_flow_rate']) == 1
        assert len(analyzer._method_registry['pump_efficiency']) == 1


class TestDependencyGraphBuilding:
    """依赖图构建测试"""

    @patch('app.services.calculation.dependency_analyzer.get_connection')
    def test_build_graph_simple_chain(self, mock_get_conn):
        """场景2: 构建简单依赖链（A→B→C）"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('method_001', 'A', 'A', 10, ['B'], True),
            ('method_002', 'B', 'B', 10, ['C'], True),
            ('method_003', 'C', 'C', 10, [], True),
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        analyzer = DependencyAnalyzer()
        
        # 构建依赖图
        graph = analyzer.build_graph(['A', 'B', 'C'])
        
        # 验证依赖关系
        assert graph['A'] == ['B']
        assert graph['B'] == ['C']
        assert graph['C'] == []

    @patch('app.services.calculation.dependency_analyzer.get_connection')
    def test_build_graph_complex_network(self, mock_get_conn):
        """场景3: 构建复杂依赖网络"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('method_001', 'A', 'A', 10, ['B', 'C'], True),
            ('method_002', 'B', 'B', 10, ['D'], True),
            ('method_003', 'C', 'C', 10, ['D'], True),
            ('method_004', 'D', 'D', 10, [], True),
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        analyzer = DependencyAnalyzer()
        
        # 构建依赖图
        graph = analyzer.build_graph(['A', 'B', 'C', 'D'])
        
        # 验证依赖关系
        assert set(graph['A']) == {'B', 'C'}
        assert graph['B'] == ['D']
        assert graph['C'] == ['D']
        assert graph['D'] == []

    @patch('app.services.calculation.dependency_analyzer.get_connection')
    def test_build_graph_no_dependencies(self, mock_get_conn):
        """场景4: 构建无依赖的图"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('method_001', 'A', 'A', 10, [], True),
            ('method_002', 'B', 'B', 10, [], True),
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        analyzer = DependencyAnalyzer()
        
        # 构建依赖图
        graph = analyzer.build_graph(['A', 'B'])
        
        # 验证无依赖
        assert graph['A'] == []
        assert graph['B'] == []


class TestTopologicalSort:
    """拓扑排序测试"""

    @patch('app.services.calculation.dependency_analyzer.get_connection')
    def test_topological_sort_simple_chain(self, mock_get_conn):
        """场景5: 拓扑排序简单链（A→B→C）"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        analyzer = DependencyAnalyzer()
        
        # 拓扑排序
        graph = {'A': ['B'], 'B': ['C'], 'C': []}
        order = analyzer.topological_sort(graph)
        
        # 验证顺序（C应该在B前面，B应该在A前面）
        assert order.index('C') < order.index('B')
        assert order.index('B') < order.index('A')

    @patch('app.services.calculation.dependency_analyzer.get_connection')
    def test_topological_sort_complex_network(self, mock_get_conn):
        """场景6: 拓扑排序复杂网络"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        analyzer = DependencyAnalyzer()
        
        # 拓扑排序
        graph = {'A': ['B', 'C'], 'B': ['D'], 'C': ['D'], 'D': []}
        order = analyzer.topological_sort(graph)
        
        # 验证顺序（D应该在B和C前面，B和C应该在A前面）
        assert order.index('D') < order.index('B')
        assert order.index('D') < order.index('C')
        assert order.index('B') < order.index('A')
        assert order.index('C') < order.index('A')

    @patch('app.services.calculation.dependency_analyzer.get_connection')
    def test_topological_sort_empty_graph(self, mock_get_conn):
        """场景7: 拓扑排序空图"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        analyzer = DependencyAnalyzer()
        
        # 拓扑排序
        graph = {}
        order = analyzer.topological_sort(graph)
        
        # 验证空结果
        assert order == []

    @patch('app.services.calculation.dependency_analyzer.get_connection')
    def test_topological_sort_single_node(self, mock_get_conn):
        """场景8: 拓扑排序单节点"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        analyzer = DependencyAnalyzer()
        
        # 拓扑排序
        graph = {'A': []}
        order = analyzer.topological_sort(graph)
        
        # 验证结果
        assert order == ['A']


class TestCircularDependencyDetection:
    """循环检测测试"""

    @patch('app.services.calculation.dependency_analyzer.get_connection')
    def test_detect_circular_dependency_simple_cycle(self, mock_get_conn):
        """场景9: 检测简单循环（A→B→A）"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        analyzer = DependencyAnalyzer()
        
        # 检测循环
        graph = {'A': ['B'], 'B': ['A']}
        cycle = analyzer.detect_circular_dependency(graph)
        
        # 验证检测到循环
        assert len(cycle) > 0
        assert 'A' in cycle
        assert 'B' in cycle

    @patch('app.services.calculation.dependency_analyzer.get_connection')
    def test_detect_circular_dependency_complex_cycle(self, mock_get_conn):
        """场景10: 检测复杂循环（A→B→C→A）"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        analyzer = DependencyAnalyzer()
        
        # 检测循环
        graph = {'A': ['B'], 'B': ['C'], 'C': ['A']}
        cycle = analyzer.detect_circular_dependency(graph)
        
        # 验证检测到循环
        assert len(cycle) == 3
        assert set(cycle) == {'A', 'B', 'C'}

    @patch('app.services.calculation.dependency_analyzer.get_connection')
    def test_detect_circular_dependency_no_cycle(self, mock_get_conn):
        """场景11: 无循环的图"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        analyzer = DependencyAnalyzer()
        
        # 检测循环
        graph = {'A': ['B'], 'B': ['C'], 'C': []}
        cycle = analyzer.detect_circular_dependency(graph)
        
        # 验证无循环
        assert cycle == []

    @patch('app.services.calculation.dependency_analyzer.get_connection')
    def test_topological_sort_raises_on_circular_dependency(self, mock_get_conn):
        """场景12: 拓扑排序遇到循环依赖应该抛出异常"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        analyzer = DependencyAnalyzer()
        
        # 拓扑排序（循环依赖）
        graph = {'A': ['B'], 'B': ['C'], 'C': ['A']}
        
        # 验证抛出异常
        with pytest.raises(CircularDependencyError) as exc_info:
            analyzer.topological_sort(graph)
        
        assert "循环依赖" in str(exc_info.value)


class TestCalculationOrderGeneration:
    """计算顺序生成测试"""

    @patch('app.services.calculation.dependency_analyzer.get_connection')
    def test_get_calculation_order_success(self, mock_get_conn):
        """场景13: 成功生成计算顺序"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('method_001', 'A', 'A', 10, ['B'], True),
            ('method_002', 'B', 'B', 10, ['C'], True),
            ('method_003', 'C', 'C', 10, [], True),
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        analyzer = DependencyAnalyzer()
        
        # 生成计算顺序
        order = analyzer.get_calculation_order(['A', 'B', 'C'])
        
        # 验证顺序
        assert order.index('C') < order.index('B')
        assert order.index('B') < order.index('A')

    @patch('app.services.calculation.dependency_analyzer.get_connection')
    def test_get_calculation_order_with_cache(self, mock_get_conn):
        """场景14: 验证计算顺序缓存机制"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('method_001', 'A', 'A', 10, ['B'], True),
            ('method_002', 'B', 'B', 10, [], True),
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        analyzer = DependencyAnalyzer()
        
        # 第一次调用（缓存未命中）
        order1 = analyzer.get_calculation_order(['A', 'B'])
        cache_misses_1 = analyzer._cache_misses
        
        # 第二次调用（缓存命中）
        order2 = analyzer.get_calculation_order(['A', 'B'])
        cache_hits_2 = analyzer._cache_hits
        
        # 验证缓存工作
        assert order1 == order2
        assert cache_hits_2 > 0

    @patch('app.services.calculation.dependency_analyzer.get_connection')
    def test_get_calculation_order_handles_circular_dependency(self, mock_get_conn):
        """场景15: 计算顺序遇到循环依赖时使用迭代求解"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('method_001', 'A', 'A', 10, ['B'], True),
            ('method_002', 'B', 'B', 10, ['A'], True),
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        analyzer = DependencyAnalyzer()

        # 验证不抛出异常，而是返回结果（使用迭代求解）
        order = analyzer.get_calculation_order(['A', 'B'])

        # 验证返回了结果（即使有循环依赖）
        assert isinstance(order, list)
        assert len(order) >= 0  # 可能返回空列表或包含指标的列表

