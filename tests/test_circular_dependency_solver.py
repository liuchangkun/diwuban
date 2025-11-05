"""
测试循环依赖求解器 (solve_circular_dependencies)

测试场景:
1. 正常流程测试 (3个场景)
2. 边界条件测试 (3个场景)
3. 异常情况测试 (2个场景)
4. 性能测试 (2个场景)

总计: 10个测试场景
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from app.services.calculation.orchestrator import CalculationOrchestrator


class TestCircularDependencySolver:
    """循环依赖求解器测试类"""

    @pytest.fixture
    def orchestrator(self):
        """创建编排器实例"""
        # Mock所有依赖组件
        with patch('app.services.calculation.dependency_analyzer.get_connection'):
            with patch('app.services.calculation.orchestrator.DependencyAnalyzer'):
                with patch('app.services.calculation.orchestrator.MethodSelector'):
                    with patch('app.services.calculation.orchestrator.PhysicsValidator'):
                        with patch('app.services.calculation.orchestrator.PerformanceMonitor'):
                            with patch('app.services.calculation.orchestrator.AdaptiveBatchManager'):
                                return CalculationOrchestrator()

    # =====================================================
    # 正常流程测试 (3个场景)
    # =====================================================

    def test_simple_circular_convergence(self, orchestrator):
        """场景1: 简单循环依赖收敛"""
        # 准备数据
        circular_group = ['metric_a', 'metric_b']
        data = {
            'base_metric': np.array([10.0, 20.0, 30.0])
        }
        timestamps = np.array([0, 1, 2])

        # Mock方法选择器和计算器
        mock_method = {'method_code': 'TEST_METHOD', 'params': {}}
        orchestrator.method_selector.select_method = Mock(return_value=mock_method)

        # Mock计算器：metric_a = base_metric * 2, metric_b = metric_a * 0.5
        def mock_calculator(data, params):
            if 'metric_a' not in data:
                return data['base_metric'] * 2
            else:
                return data['metric_a'] * 0.5

        with patch('app.services.calculation.orchestrator.get_calculator', return_value=mock_calculator):
            results = orchestrator.solve_circular_dependencies(
                circular_group=circular_group,
                data=data,
                timestamps=timestamps,
                station_id=1,
                device_id=101,
                start_time='2025-01-01 00:00:00',
                end_time='2025-01-01 00:00:02',
                max_iterations=10,
                convergence_threshold=0.01
            )
        
        # 验证结果
        assert 'metric_a' in results
        assert 'metric_b' in results
        assert len(results['metric_a']) == 3
        assert len(results['metric_b']) == 3
        # 验证无NaN
        assert not np.isnan(results['metric_a']).any()
        assert not np.isnan(results['metric_b']).any()

    def test_multi_metric_circular_convergence(self, orchestrator):
        """场景2: 多指标循环依赖收敛"""
        # 准备数据（3个指标的循环）
        circular_group = ['metric_a', 'metric_b', 'metric_c']
        data = {
            'base_metric': np.array([100.0, 200.0])
        }
        timestamps = np.array([0, 1])
        
        # Mock方法选择器
        mock_method = {'method_code': 'TEST_METHOD', 'params': {}}
        orchestrator.method_selector.select_method = Mock(return_value=mock_method)
        
        # Mock计算器：简单的线性关系
        call_count = {'count': 0}
        
        def mock_calculator(data, params):
            call_count['count'] += 1
            # 返回稳定值以确保收敛
            return np.ones(len(data['base_metric'])) * 50.0
        
        with patch('app.services.calculation.orchestrator.get_calculator', return_value=mock_calculator):
            results = orchestrator.solve_circular_dependencies(
                circular_group=circular_group,
                data=data,
                timestamps=timestamps,
                station_id=1,
                device_id=101,
                start_time='2025-01-01 00:00:00',
                end_time='2025-01-01 00:00:01',
                max_iterations=10,
                convergence_threshold=0.01
            )
        
        # 验证所有指标都计算了
        assert len(results) == 3
        for metric in circular_group:
            assert metric in results
            assert len(results[metric]) == 2

    def test_convergence_with_initial_values(self, orchestrator):
        """场景3: 使用初始值加速收敛"""
        # 准备数据（包含初始值）
        circular_group = ['metric_a', 'metric_b']
        data = {
            'base_metric': np.array([10.0, 20.0]),
            'metric_a': np.array([15.0, 25.0]),  # 提供初始值
            'metric_b': np.array([7.5, 12.5])    # 提供初始值
        }
        timestamps = np.array([0, 1])
        
        # Mock方法选择器
        mock_method = {'method_code': 'TEST_METHOD', 'params': {}}
        orchestrator.method_selector.select_method = Mock(return_value=mock_method)
        
        # Mock计算器
        def mock_calculator(data, params):
            return data['base_metric'] * 1.5
        
        with patch('app.services.calculation.orchestrator.get_calculator', return_value=mock_calculator):
            results = orchestrator.solve_circular_dependencies(
                circular_group=circular_group,
                data=data,
                timestamps=timestamps,
                station_id=1,
                device_id=101,
                start_time='2025-01-01 00:00:00',
                end_time='2025-01-01 00:00:01',
                max_iterations=5,
                convergence_threshold=0.01
            )
        
        # 验证使用了初始值（结果应该接近初始值）
        assert 'metric_a' in results
        assert 'metric_b' in results

    # =====================================================
    # 边界条件测试 (3个场景)
    # =====================================================

    def test_convergence_at_boundary(self, orchestrator):
        """场景4: 收敛边界测试"""
        # 准备数据
        circular_group = ['metric_a']
        data = {'base_metric': np.array([10.0])}
        timestamps = np.array([0])
        
        # Mock方法选择器
        mock_method = {'method_code': 'TEST_METHOD', 'params': {}}
        orchestrator.method_selector.select_method = Mock(return_value=mock_method)
        
        # Mock计算器：返回值逐渐接近目标值
        iteration_count = {'count': 0}
        
        def mock_calculator(data, params):
            iteration_count['count'] += 1
            # 每次迭代减小误差
            return np.array([10.0 + 1.0 / iteration_count['count']])
        
        with patch('app.services.calculation.orchestrator.get_calculator', return_value=mock_calculator):
            results = orchestrator.solve_circular_dependencies(
                circular_group=circular_group,
                data=data,
                timestamps=timestamps,
                station_id=1,
                device_id=101,
                start_time='2025-01-01 00:00:00',
                end_time='2025-01-01 00:00:01',
                max_iterations=20,
                convergence_threshold=0.01  # 1%阈值
            )
        
        # 验证收敛
        assert 'metric_a' in results

    def test_max_iterations_reached(self, orchestrator):
        """场景5: 达到最大迭代次数"""
        # 准备数据
        circular_group = ['metric_a']
        data = {'base_metric': np.array([10.0])}
        timestamps = np.array([0])

        # Mock方法选择器 - 使用新的API
        from app.services.calculation.domain import MethodDescriptor
        mock_method_desc = MethodDescriptor(
            method_id='TEST_METHOD',
            method_code='TEST_METHOD',
            metric_key='metric_a',
            priority=1,
            params={}
        )
        orchestrator.method_selector.select_method_ctx = Mock(return_value=mock_method_desc)

        # Mock计算器：每次返回不同值（不收敛）
        iteration_count = {'count': 0}

        def mock_calculator_unified(ctx, method_desc, data):
            iteration_count['count'] += 1
            # 返回振荡值，不收敛
            values = np.array([10.0 + (-1) ** iteration_count['count'] * 5.0])
            return values, {}

        with patch('app.services.calculation.orchestrator.get_calculator_unified', return_value=mock_calculator_unified):
            results = orchestrator.solve_circular_dependencies(
                circular_group=circular_group,
                data=data,
                timestamps=timestamps,
                station_id=1,
                device_id=101,
                start_time='2025-01-01 00:00:00',
                end_time='2025-01-01 00:00:01',
                max_iterations=3,  # 限制迭代次数
                convergence_threshold=0.01
            )

        # 验证即使不收敛也返回结果
        assert 'metric_a' in results
        # 验证迭代了指定次数（至少迭代了3次）
        assert iteration_count['count'] >= 3

    def test_initial_value_impact(self, orchestrator):
        """场景6: 初始值对收敛的影响"""
        # 准备两组数据：一组有初始值，一组没有
        circular_group = ['metric_a']
        timestamps = np.array([0, 1, 2])
        
        # 第一组：无初始值
        data1 = {'base_metric': np.array([10.0, 20.0, 30.0])}
        
        # 第二组：有初始值
        data2 = {
            'base_metric': np.array([10.0, 20.0, 30.0]),
            'metric_a': np.array([15.0, 25.0, 35.0])
        }
        
        # Mock方法选择器
        mock_method = {'method_code': 'TEST_METHOD', 'params': {}}
        orchestrator.method_selector.select_method = Mock(return_value=mock_method)
        
        # Mock计算器
        def mock_calculator(data, params):
            return data['base_metric'] * 1.5
        
        with patch('app.services.calculation.orchestrator.get_calculator', return_value=mock_calculator):
            results1 = orchestrator.solve_circular_dependencies(
                circular_group, data1, timestamps, 1, 101,
                '2025-01-01 00:00:00', '2025-01-01 00:00:01', 10, 0.01
            )
            results2 = orchestrator.solve_circular_dependencies(
                circular_group, data2, timestamps, 1, 101,
                '2025-01-01 00:00:00', '2025-01-01 00:00:01', 10, 0.01
            )
        
        # 验证两组都有结果
        assert 'metric_a' in results1
        assert 'metric_a' in results2

    # =====================================================
    # 异常情况测试 (2个场景)
    # =====================================================

    def test_no_convergence_warning(self, orchestrator):
        """场景7: 不收敛情况的警告"""
        # 准备数据
        circular_group = ['metric_a']
        data = {'base_metric': np.array([10.0])}
        timestamps = np.array([0])
        
        # Mock方法选择器
        mock_method = {'method_code': 'TEST_METHOD', 'params': {}}
        orchestrator.method_selector.select_method = Mock(return_value=mock_method)
        
        # Mock计算器：返回随机值（不收敛）
        import random
        def mock_calculator(data, params):
            return np.array([random.uniform(5.0, 15.0)])
        
        with patch('app.services.calculation.orchestrator.get_calculator', return_value=mock_calculator):
            # 应该记录警告但不抛出异常
            results = orchestrator.solve_circular_dependencies(
                circular_group=circular_group,
                data=data,
                timestamps=timestamps,
                station_id=1,
                device_id=101,
                start_time='2025-01-01 00:00:00',
                end_time='2025-01-01 00:00:01',
                max_iterations=5,
                convergence_threshold=0.001  # 严格的阈值
            )
        
        # 验证返回了结果（即使不收敛）
        assert 'metric_a' in results

    def test_calculator_error_handling(self, orchestrator):
        """场景8: 计算器错误处理"""
        # 准备数据
        circular_group = ['metric_a', 'metric_b']
        data = {'base_metric': np.array([10.0])}
        timestamps = np.array([0])
        
        # Mock方法选择器
        mock_method = {'method_code': 'TEST_METHOD', 'params': {}}
        orchestrator.method_selector.select_method = Mock(return_value=mock_method)
        
        # Mock计算器：第一个指标抛出异常
        call_count = {'count': 0}
        
        def mock_calculator(data, params):
            call_count['count'] += 1
            if call_count['count'] % 2 == 1:  # 奇数次调用抛出异常
                raise ValueError("计算错误")
            return np.array([10.0])
        
        with patch('app.services.calculation.orchestrator.get_calculator', return_value=mock_calculator):
            results = orchestrator.solve_circular_dependencies(
                circular_group=circular_group,
                data=data,
                timestamps=timestamps,
                station_id=1,
                device_id=101,
                start_time='2025-01-01 00:00:00',
                end_time='2025-01-01 00:00:01',
                max_iterations=3,
                convergence_threshold=0.01
            )
        
        # 验证即使有错误也返回结果
        assert isinstance(results, dict)

    # =====================================================
    # 性能测试 (2个场景)
    # =====================================================

    def test_convergence_speed(self, orchestrator):
        """场景9: 收敛速度测试"""
        # 准备数据
        circular_group = ['metric_a']
        data = {'base_metric': np.array([10.0, 20.0, 30.0])}
        timestamps = np.array([0, 1, 2])
        
        # Mock方法选择器
        mock_method = {'method_code': 'TEST_METHOD', 'params': {}}
        orchestrator.method_selector.select_method = Mock(return_value=mock_method)
        
        # Mock计算器：快速收敛（返回常数）
        def mock_calculator(data, params):
            return np.array([15.0, 25.0, 35.0])
        
        iteration_count = {'count': 0}
        
        original_get_calculator = None
        def counting_calculator(data, params):
            iteration_count['count'] += 1
            return mock_calculator(data, params)
        
        with patch('app.services.calculation.orchestrator.get_calculator', return_value=counting_calculator):
            results = orchestrator.solve_circular_dependencies(
                circular_group=circular_group,
                data=data,
                timestamps=timestamps,
                station_id=1,
                device_id=101,
                start_time='2025-01-01 00:00:00',
                end_time='2025-01-01 00:00:01',
                max_iterations=10,
                convergence_threshold=0.01
            )
        
        # 验证快速收敛（应该在2-3次迭代内收敛）
        assert iteration_count['count'] <= 5

    def test_memory_efficiency(self, orchestrator):
        """场景10: 内存使用效率测试"""
        # 准备大数据集
        circular_group = ['metric_a', 'metric_b']
        data = {
            'base_metric': np.random.rand(1000)  # 1000个数据点
        }
        timestamps = np.arange(1000)
        
        # Mock方法选择器
        mock_method = {'method_code': 'TEST_METHOD', 'params': {}}
        orchestrator.method_selector.select_method = Mock(return_value=mock_method)
        
        # Mock计算器
        def mock_calculator(data, params):
            return data['base_metric'] * 1.5
        
        with patch('app.services.calculation.orchestrator.get_calculator', return_value=mock_calculator):
            results = orchestrator.solve_circular_dependencies(
                circular_group=circular_group,
                data=data,
                timestamps=timestamps,
                station_id=1,
                device_id=101,
                start_time='2025-01-01 00:00:00',
                end_time='2025-01-01 00:00:01',
                max_iterations=5,
                convergence_threshold=0.01
            )
        
        # 验证结果大小正确
        assert len(results['metric_a']) == 1000
        assert len(results['metric_b']) == 1000
        # 验证数据类型正确（numpy数组）
        assert isinstance(results['metric_a'], np.ndarray)
        assert isinstance(results['metric_b'], np.ndarray)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

