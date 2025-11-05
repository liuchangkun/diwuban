"""
测试缺失指标计算端到端流程 (E2E)

测试场景:
1. 正常流程测试 (3个场景)
2. 边界条件测试 (2个场景)
3. 异常情况测试 (2个场景)
4. 性能测试 (1个场景)

总计: 8个测试场景
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from app.services.calculation.orchestrator import CalculationOrchestrator


class TestMissingMetricsE2E:
    """缺失指标计算端到端测试类"""

    @pytest.fixture
    def orchestrator(self):
        """创建编排器实例"""
        # Mock所有依赖组件
        with patch('app.services.calculation.dependency_analyzer.get_connection'):
            with patch('app.services.calculation.orchestrator.DependencyAnalyzer') as mock_dep:
                with patch('app.services.calculation.orchestrator.MethodSelector') as mock_sel:
                    with patch('app.services.calculation.orchestrator.PhysicsValidator') as mock_val:
                        with patch('app.services.calculation.orchestrator.PerformanceMonitor'):
                            with patch('app.services.calculation.orchestrator.AdaptiveBatchManager'):
                                # 配置Mock
                                orch = CalculationOrchestrator()
                                
                                # Mock依赖分析器
                                mock_dep_instance = mock_dep.return_value
                                mock_dep_instance.get_calculation_order.return_value = ['pump_flow_rate']
                                mock_dep_instance.get_circular_group_info.return_value = {}
                                mock_dep_instance.get_dependencies.return_value = ['pump_active_power']
                                orch.dependency_analyzer = mock_dep_instance
                                
                                # Mock方法选择器
                                mock_sel_instance = mock_sel.return_value
                                mock_sel_instance.select_method.return_value = {
                                    'method_id': 'pump_flow_rate_method_a',
                                    'method_code': 'A',
                                    'method_name': '方法A',
                                    'dependencies': ['pump_active_power']
                                }
                                orch.method_selector = mock_sel_instance
                                
                                # Mock验证器
                                mock_val_instance = mock_val.return_value
                                mock_val_instance.validate.return_value = (
                                    True,
                                    np.ones(10, dtype=bool),
                                    [],
                                    []
                                )
                                mock_val_instance.validate_ctx.return_value = (
                                    True,
                                    np.ones(10, dtype=bool),
                                    [],
                                    []
                                )
                                orch.validator = mock_val_instance

                                return orch

    # =====================================================
    # 正常流程测试 (3个场景)
    # =====================================================

    def test_e2e_single_metric_calculation(self, orchestrator):
        """场景1: 单指标端到端计算"""
        # Mock load_data
        mock_data = {
            'pump_active_power': np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        }
        mock_timestamps = np.array([0, 1, 2, 3, 4])

        with patch.object(orchestrator, 'load_data', return_value=(mock_data, mock_timestamps)):
            with patch.object(orchestrator, 'load_parameters', return_value={}):
                with patch.object(orchestrator, '_get_running_device_count', return_value=2):
                    with patch.object(orchestrator, '_get_device_type', return_value='pump'):
                        with patch('app.services.calculation.orchestrator.get_calculator_unified') as mock_calc:
                            # Mock计算器 - 返回统一签名的函数
                            def mock_calculator(ctx, method, data):
                                values = data['pump_active_power'] * 2
                                meta = {'method_id': method.method_id, 'method_code': method.method_code}
                                return values, meta
                            mock_calc.return_value = mock_calculator

                            # Mock方法选择器返回MethodDescriptor
                            from app.services.calculation.domain import MethodDescriptor
                            mock_method = MethodDescriptor(
                                method_id='pump_flow_rate_method_a',
                                metric_key='pump_flow_rate',
                                method_code='A',
                                priority=100,
                                dependencies=['pump_active_power'],
                                conditions={},
                                params={}
                            )
                            orchestrator.method_selector.select_method_ctx.return_value = mock_method

                            # 执行计算
                            result = orchestrator.calculate_missing_metrics(
                                station_id=1,
                                device_id=101,
                                start_time='2025-01-01 00:00:00',
                                end_time='2025-01-01 00:05:00',
                                metrics=['pump_flow_rate'],
                                write_to_db=False
                            )

        # 验证结果
        assert result['success'] is True
        assert 'pump_flow_rate' in result['metrics_calculated']
        assert len(result['metrics_failed']) == 0
        assert result['total_points'] > 0
        assert result['valid_points'] > 0
        assert 'performance_stats' in result

    def test_e2e_multiple_metrics_calculation(self, orchestrator):
        """场景2: 多指标端到端计算"""
        # Mock依赖分析器返回多个指标的顺序
        orchestrator.dependency_analyzer.get_calculation_order.return_value = [
            'pump_flow_rate', 'pump_head'
        ]
        orchestrator.dependency_analyzer.get_dependencies.side_effect = [
            ['pump_active_power'],
            ['pump_flow_rate', 'pump_outlet_pressure']
        ]

        # Mock load_data
        mock_data = {
            'pump_active_power': np.array([10.0, 20.0, 30.0]),
            'pump_outlet_pressure': np.array([5.0, 6.0, 7.0])
        }
        mock_timestamps = np.array([0, 1, 2])

        with patch.object(orchestrator, 'load_data', return_value=(mock_data, mock_timestamps)):
            with patch.object(orchestrator, 'load_parameters', return_value={}):
                with patch.object(orchestrator, '_get_running_device_count', return_value=2):
                    with patch.object(orchestrator, '_get_device_type', return_value='pump'):
                        with patch('app.services.calculation.orchestrator.get_calculator_unified') as mock_calc:
                            # Mock计算器（根据method_id返回不同计算）
                            def calculator_factory(method_id):
                                def calc(ctx, method, data):
                                    if 'flow_rate' in method_id:
                                        values = data['pump_active_power'] * 2
                                    else:  # head
                                        values = data['pump_outlet_pressure'] * 10
                                    meta = {'method_id': method.method_id, 'method_code': method.method_code}
                                    return values, meta
                                return calc

                            mock_calc.side_effect = calculator_factory

                            # Mock方法选择器返回MethodDescriptor
                            from app.services.calculation.domain import MethodDescriptor
                            def method_selector_side_effect(ctx, metric_key, available_metrics, data):
                                if metric_key == 'pump_flow_rate':
                                    return MethodDescriptor(
                                        method_id='pump_flow_rate_method_a',
                                        metric_key='pump_flow_rate',
                                        method_code='A',
                                        priority=100,
                                        dependencies=['pump_active_power']
                                    )
                                elif metric_key == 'pump_head':
                                    return MethodDescriptor(
                                        method_id='pump_head_method_a',
                                        metric_key='pump_head',
                                        method_code='A',
                                        priority=100,
                                        dependencies=['pump_outlet_pressure']
                                    )
                                return None

                            orchestrator.method_selector.select_method_ctx.side_effect = method_selector_side_effect

                            # 执行计算
                            result = orchestrator.calculate_missing_metrics(
                                station_id=1,
                                device_id=101,
                                start_time='2025-01-01 00:00:00',
                                end_time='2025-01-01 00:03:00',
                                metrics=['pump_flow_rate', 'pump_head'],
                                write_to_db=False
                            )

        # 验证结果
        assert result['success'] is True
        assert len(result['metrics_calculated']) == 2
        assert 'pump_flow_rate' in result['metrics_calculated']
        assert 'pump_head' in result['metrics_calculated']

    def test_e2e_circular_dependency_calculation(self, orchestrator):
        """场景3: 循环依赖端到端计算"""
        # Mock循环依赖组
        orchestrator.dependency_analyzer.get_calculation_order.return_value = [
            'pump_efficiency', 'pump_power'
        ]
        orchestrator.dependency_analyzer.get_circular_group_info.return_value = {
            'circular_0': ['pump_efficiency', 'pump_power']
        }

        # Mock load_data
        mock_data = {
            'pump_flow_rate': np.array([100.0, 150.0, 200.0]),
            'pump_head': np.array([50.0, 45.0, 40.0])
        }
        mock_timestamps = np.array([0, 1, 2])

        # Mock validator返回正确大小的mask（3个元素）
        orchestrator.validator.validate.return_value = (
            True,
            np.ones(3, dtype=bool),  # 修改为3个元素
            [],
            []
        )

        with patch.object(orchestrator, 'load_data', return_value=(mock_data, mock_timestamps)):
            with patch.object(orchestrator, 'load_parameters', return_value={}):
                with patch.object(orchestrator, 'solve_circular_dependencies') as mock_solve:
                    # Mock循环依赖求解结果
                    mock_solve.return_value = {
                        'pump_efficiency': np.array([80.0, 82.0, 85.0]),
                        'pump_power': np.array([15.0, 18.0, 22.0])
                    }

                    # 执行计算
                    result = orchestrator.calculate_missing_metrics(
                        station_id=1,
                        device_id=101,
                        start_time='2025-01-01 00:00:00',
                        end_time='2025-01-01 00:03:00',
                        metrics=['pump_efficiency', 'pump_power'],
                        write_to_db=False
                    )

        # 验证结果
        assert result['success'] is True
        assert 'pump_efficiency' in result['metrics_calculated']
        assert 'pump_power' in result['metrics_calculated']
        # 验证调用了循环依赖求解
        mock_solve.assert_called_once()

    # =====================================================
    # 边界条件测试 (2个场景)
    # =====================================================

    def test_e2e_large_batch_data(self, orchestrator):
        """场景4: 大批量数据处理"""
        # Mock大批量数据（10000个数据点）
        mock_data = {
            'pump_active_power': np.random.uniform(10, 50, 10000)
        }
        mock_timestamps = np.arange(10000)

        with patch.object(orchestrator, 'load_data', return_value=(mock_data, mock_timestamps)):
            with patch.object(orchestrator, 'load_parameters', return_value={}):
                with patch.object(orchestrator, '_get_running_device_count', return_value=2):
                    with patch.object(orchestrator, '_get_device_type', return_value='pump'):
                        with patch('app.services.calculation.orchestrator.get_calculator_unified') as mock_calc:
                            def mock_calculator(ctx, method, data):
                                values = data['pump_active_power'] * 2
                                meta = {'method_id': method.method_id, 'method_code': method.method_code}
                                return values, meta
                            mock_calc.return_value = mock_calculator

                            from app.services.calculation.domain import MethodDescriptor
                            mock_method = MethodDescriptor(
                                method_id='pump_flow_rate_method_a',
                                metric_key='pump_flow_rate',
                                method_code='A',
                                priority=100,
                                dependencies=['pump_active_power']
                            )
                            orchestrator.method_selector.select_method_ctx.return_value = mock_method

                            # 执行计算
                            result = orchestrator.calculate_missing_metrics(
                                station_id=1,
                                device_id=101,
                                start_time='2025-01-01 00:00:00',
                                end_time='2025-01-08 00:00:00',  # 7天数据
                                metrics=['pump_flow_rate'],
                                write_to_db=False
                            )

        # 验证结果
        assert result['success'] is True
        assert result['total_points'] == 10000
        # 验证性能（大批量数据应该有合理的吞吐量）
        assert result['performance_stats']['throughput'] > 0

    def test_e2e_long_time_window(self, orchestrator):
        """场景5: 长时间窗口处理"""
        # Mock长时间窗口数据（30天，每分钟1个点 = 43200个点）
        num_points = 43200
        mock_data = {
            'pump_active_power': np.random.uniform(10, 50, num_points)
        }
        mock_timestamps = np.arange(num_points)

        with patch.object(orchestrator, 'load_data', return_value=(mock_data, mock_timestamps)):
            with patch.object(orchestrator, 'load_parameters', return_value={}):
                with patch.object(orchestrator, '_get_running_device_count', return_value=2):
                    with patch.object(orchestrator, '_get_device_type', return_value='pump'):
                        with patch('app.services.calculation.orchestrator.get_calculator_unified') as mock_calc:
                            def mock_calculator(ctx, method, data):
                                values = data['pump_active_power'] * 2
                                meta = {'method_id': method.method_id, 'method_code': method.method_code}
                                return values, meta
                            mock_calc.return_value = mock_calculator

                            from app.services.calculation.domain import MethodDescriptor
                            mock_method = MethodDescriptor(
                                method_id='pump_flow_rate_method_a',
                                metric_key='pump_flow_rate',
                                method_code='A',
                                priority=100,
                                dependencies=['pump_active_power']
                            )
                            orchestrator.method_selector.select_method_ctx.return_value = mock_method

                            # 执行计算
                            result = orchestrator.calculate_missing_metrics(
                                station_id=1,
                                device_id=101,
                                start_time='2025-01-01 00:00:00',
                                end_time='2025-01-31 00:00:00',  # 30天
                                metrics=['pump_flow_rate'],
                                write_to_db=False
                            )

        # 验证结果
        assert result['success'] is True
        assert result['total_points'] == num_points

    # =====================================================
    # 异常情况测试 (2个场景)
    # =====================================================

    def test_e2e_missing_dependency_data(self, orchestrator):
        """场景6: 依赖数据缺失"""
        # Mock空数据（缺少依赖）
        mock_data = {}  # 缺少pump_active_power
        mock_timestamps = np.array([0, 1, 2])

        with patch.object(orchestrator, 'load_data', return_value=(mock_data, mock_timestamps)):
            with patch.object(orchestrator, 'load_parameters', return_value={}):
                # 执行计算
                result = orchestrator.calculate_missing_metrics(
                    station_id=1,
                    device_id=101,
                    start_time='2025-01-01 00:00:00',
                    end_time='2025-01-01 00:03:00',
                    metrics=['pump_flow_rate'],
                    write_to_db=False
                )

        # 验证结果
        assert result['success'] is False
        assert 'pump_flow_rate' in result['metrics_failed']
        assert len(result['errors']) > 0

    def test_e2e_calculation_failure(self, orchestrator):
        """场景7: 计算失败处理"""
        # Mock load_data
        mock_data = {
            'pump_active_power': np.array([10.0, 20.0, 30.0])
        }
        mock_timestamps = np.array([0, 1, 2])

        with patch.object(orchestrator, 'load_data', return_value=(mock_data, mock_timestamps)):
            with patch.object(orchestrator, 'load_parameters', return_value={}):
                with patch.object(orchestrator, '_get_running_device_count', return_value=2):
                    with patch.object(orchestrator, '_get_device_type', return_value='pump'):
                        with patch('app.services.calculation.orchestrator.get_calculator_unified') as mock_calc:
                            # Mock计算器抛出异常
                            def mock_calculator_error(ctx, method, data):
                                raise ValueError("计算错误")
                            mock_calc.return_value = mock_calculator_error

                            from app.services.calculation.domain import MethodDescriptor
                            mock_method = MethodDescriptor(
                                method_id='pump_flow_rate_method_a',
                                metric_key='pump_flow_rate',
                                method_code='A',
                                priority=100,
                                dependencies=['pump_active_power']
                            )
                            orchestrator.method_selector.select_method_ctx.return_value = mock_method

                            # 执行计算
                            result = orchestrator.calculate_missing_metrics(
                                station_id=1,
                                device_id=101,
                                start_time='2025-01-01 00:00:00',
                                end_time='2025-01-01 00:03:00',
                                metrics=['pump_flow_rate'],
                                write_to_db=False
                            )

        # 验证结果
        assert result['success'] is False
        assert 'pump_flow_rate' in result['metrics_failed']
        assert any('计算错误' in str(e) for e in result['errors'])

    # =====================================================
    # 性能测试 (1个场景)
    # =====================================================

    def test_e2e_performance_metrics(self, orchestrator):
        """场景8: 端到端性能指标"""
        # Mock数据
        mock_data = {
            'pump_active_power': np.random.uniform(10, 50, 1000)
        }
        mock_timestamps = np.arange(1000)

        with patch.object(orchestrator, 'load_data', return_value=(mock_data, mock_timestamps)):
            with patch.object(orchestrator, 'load_parameters', return_value={}):
                with patch.object(orchestrator, '_get_running_device_count', return_value=2):
                    with patch.object(orchestrator, '_get_device_type', return_value='pump'):
                        with patch('app.services.calculation.orchestrator.get_calculator_unified') as mock_calc:
                            def mock_calculator(ctx, method, data):
                                values = data['pump_active_power'] * 2
                                meta = {'method_id': method.method_id, 'method_code': method.method_code}
                                return values, meta
                            mock_calc.return_value = mock_calculator

                            from app.services.calculation.domain import MethodDescriptor
                            mock_method = MethodDescriptor(
                                method_id='pump_flow_rate_method_a',
                                metric_key='pump_flow_rate',
                                method_code='A',
                                priority=100,
                                dependencies=['pump_active_power']
                            )
                            orchestrator.method_selector.select_method_ctx.return_value = mock_method

                            # 执行计算
                            result = orchestrator.calculate_missing_metrics(
                                station_id=1,
                                device_id=101,
                                start_time='2025-01-01 00:00:00',
                                end_time='2025-01-01 16:40:00',
                                metrics=['pump_flow_rate'],
                                write_to_db=False
                            )
        
        # 验证性能指标
        assert 'performance_stats' in result
        stats = result['performance_stats']
        assert 'total_time' in stats
        assert 'load_data_time' in stats
        assert 'calculation_time' in stats
        assert 'throughput' in stats
        assert stats['total_time'] > 0
        assert stats['throughput'] > 0
        # 验证吞吐量合理（应该能处理至少100个数据点/秒）
        assert stats['throughput'] >= 100


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

