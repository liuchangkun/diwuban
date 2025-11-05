"""
测试缺失指标计算并发安全性

测试场景:
1. 正常流程测试 (2个场景)
2. 边界条件测试 (2个场景)
3. 异常情况测试 (1个场景)
4. 性能测试 (1个场景)

总计: 6个测试场景
"""

import pytest
import numpy as np
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch, MagicMock
from app.services.calculation.orchestrator import CalculationOrchestrator


class TestMissingMetricsConcurrent:
    """缺失指标计算并发测试类"""

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
    # 正常流程测试 (2个场景)
    # =====================================================

    def test_concurrent_multiple_devices(self, orchestrator):
        """场景1: 多设备并发计算"""
        # Mock数据
        mock_data = {
            'pump_active_power': np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        }
        mock_timestamps = np.array([0, 1, 2, 3, 4])

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

                            # 并发计算多个设备
                            devices = [(1, 101), (1, 102), (1, 103), (2, 201), (2, 202)]
                            results = []

                            with ThreadPoolExecutor(max_workers=3) as executor:
                                futures = []
                                for station_id, device_id in devices:
                                    future = executor.submit(
                                        orchestrator.calculate_missing_metrics,
                                        station_id=station_id,
                                        device_id=device_id,
                                        start_time='2025-01-01 00:00:00',
                                        end_time='2025-01-01 00:05:00',
                                        metrics=['pump_flow_rate'],
                                        write_to_db=False
                                    )
                                    futures.append(future)

                                for future in as_completed(futures):
                                    results.append(future.result())

        # 验证所有设备都计算成功
        assert len(results) == 5
        for result in results:
            assert result['success'] is True
            assert 'pump_flow_rate' in result['metrics_calculated']

    def test_concurrent_multiple_time_periods(self, orchestrator):
        """场景2: 多时间段并发计算"""
        # Mock数据
        mock_data = {
            'pump_active_power': np.array([10.0, 20.0, 30.0])
        }
        mock_timestamps = np.array([0, 1, 2])

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

                            # 并发计算多个时间段
                            time_periods = [
                                ('2025-01-01 00:00:00', '2025-01-01 06:00:00'),
                                ('2025-01-01 06:00:00', '2025-01-01 12:00:00'),
                                ('2025-01-01 12:00:00', '2025-01-01 18:00:00'),
                                ('2025-01-01 18:00:00', '2025-01-02 00:00:00')
                            ]
                            results = []

                            with ThreadPoolExecutor(max_workers=4) as executor:
                                futures = []
                                for start_time, end_time in time_periods:
                                    future = executor.submit(
                                        orchestrator.calculate_missing_metrics,
                                        station_id=1,
                                        device_id=101,
                                        start_time=start_time,
                                        end_time=end_time,
                                        metrics=['pump_flow_rate'],
                                        write_to_db=False
                                    )
                                    futures.append(future)
                        
                        for future in as_completed(futures):
                            results.append(future.result())
        
        # 验证所有时间段都计算成功
        assert len(results) == 4
        for result in results:
            assert result['success'] is True

    # =====================================================
    # 边界条件测试 (2个场景)
    # =====================================================

    def test_high_concurrency_stress(self, orchestrator):
        """场景3: 高并发压力测试"""
        # Mock数据
        mock_data = {
            'pump_active_power': np.array([10.0, 20.0, 30.0])
        }
        mock_timestamps = np.array([0, 1, 2])

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

                            # 高并发：20个并发任务
                            num_tasks = 20
                            results = []

                            with ThreadPoolExecutor(max_workers=10) as executor:
                                futures = []
                                for i in range(num_tasks):
                                    future = executor.submit(
                                        orchestrator.calculate_missing_metrics,
                                        station_id=1,
                                        device_id=100 + i,
                                        start_time='2025-01-01 00:00:00',
                                        end_time='2025-01-01 00:03:00',
                                        metrics=['pump_flow_rate'],
                                        write_to_db=False
                                    )
                                    futures.append(future)

                                for future in as_completed(futures):
                                    results.append(future.result())

        # 验证所有任务都完成
        assert len(results) == num_tasks
        # 验证成功率
        success_count = sum(1 for r in results if r['success'])
        assert success_count == num_tasks

    def test_resource_contention(self, orchestrator):
        """场景4: 资源竞争测试"""
        # Mock数据（模拟共享资源）
        shared_counter = {'count': 0}

        def mock_calculator_with_counter(ctx, method, data):
            # 模拟资源竞争
            shared_counter['count'] += 1
            time.sleep(0.01)  # 模拟计算延迟
            values = data['pump_active_power'] * 2
            meta = {'method_id': method.method_id, 'method_code': method.method_code}
            return values, meta

        mock_data = {
            'pump_active_power': np.array([10.0, 20.0, 30.0])
        }
        mock_timestamps = np.array([0, 1, 2])

        with patch.object(orchestrator, 'load_data', return_value=(mock_data, mock_timestamps)):
            with patch.object(orchestrator, 'load_parameters', return_value={}):
                with patch.object(orchestrator, '_get_running_device_count', return_value=2):
                    with patch.object(orchestrator, '_get_device_type', return_value='pump'):
                        with patch('app.services.calculation.orchestrator.get_calculator_unified') as mock_calc:
                            mock_calc.return_value = mock_calculator_with_counter

                            from app.services.calculation.domain import MethodDescriptor
                            mock_method = MethodDescriptor(
                                method_id='pump_flow_rate_method_a',
                                metric_key='pump_flow_rate',
                                method_code='A',
                                priority=100,
                                dependencies=['pump_active_power']
                            )
                            orchestrator.method_selector.select_method_ctx.return_value = mock_method

                            # 并发访问共享资源
                            num_tasks = 10
                            results = []

                            with ThreadPoolExecutor(max_workers=5) as executor:
                                futures = []
                                for i in range(num_tasks):
                                    future = executor.submit(
                                        orchestrator.calculate_missing_metrics,
                                        station_id=1,
                                        device_id=101,
                                        start_time='2025-01-01 00:00:00',
                                        end_time='2025-01-01 00:03:00',
                                        metrics=['pump_flow_rate'],
                                        write_to_db=False
                                    )
                                    futures.append(future)

                                for future in as_completed(futures):
                                    results.append(future.result())
        
        # 验证所有任务都完成
        assert len(results) == num_tasks
        # 验证共享资源被正确访问
        assert shared_counter['count'] == num_tasks

    # =====================================================
    # 异常情况测试 (1个场景)
    # =====================================================

    def test_concurrent_error_handling(self, orchestrator):
        """场景5: 并发错误处理"""
        # Mock数据
        mock_data = {
            'pump_active_power': np.array([10.0, 20.0, 30.0])
        }
        mock_timestamps = np.array([0, 1, 2])

        # Mock计算器：部分任务成功，部分失败
        call_count = {'count': 0}

        def mock_calculator_with_errors(ctx, method, data):
            call_count['count'] += 1
            if call_count['count'] % 3 == 0:
                raise ValueError("模拟计算错误")
            values = data['pump_active_power'] * 2
            meta = {'method_id': method.method_id, 'method_code': method.method_code}
            return values, meta

        with patch.object(orchestrator, 'load_data', return_value=(mock_data, mock_timestamps)):
            with patch.object(orchestrator, 'load_parameters', return_value={}):
                with patch.object(orchestrator, '_get_running_device_count', return_value=2):
                    with patch.object(orchestrator, '_get_device_type', return_value='pump'):
                        with patch('app.services.calculation.orchestrator.get_calculator_unified') as mock_calc:
                            mock_calc.return_value = mock_calculator_with_errors

                            from app.services.calculation.domain import MethodDescriptor
                            mock_method = MethodDescriptor(
                                method_id='pump_flow_rate_method_a',
                                metric_key='pump_flow_rate',
                                method_code='A',
                                priority=100,
                                dependencies=['pump_active_power']
                            )
                            orchestrator.method_selector.select_method_ctx.return_value = mock_method

                            # 并发执行（部分会失败）
                            num_tasks = 9
                            results = []

                            with ThreadPoolExecutor(max_workers=3) as executor:
                                futures = []
                                for i in range(num_tasks):
                                    future = executor.submit(
                                        orchestrator.calculate_missing_metrics,
                                        station_id=1,
                                        device_id=100 + i,
                                        start_time='2025-01-01 00:00:00',
                                        end_time='2025-01-01 00:03:00',
                                        metrics=['pump_flow_rate'],
                                        write_to_db=False
                                    )
                                    futures.append(future)

                                for future in as_completed(futures):
                                    results.append(future.result())

        # 验证所有任务都返回结果（成功或失败）
        assert len(results) == num_tasks
        # 验证有成功和失败的任务
        success_count = sum(1 for r in results if r['success'])
        failure_count = sum(1 for r in results if not r['success'])
        assert success_count > 0
        assert failure_count > 0

    # =====================================================
    # 性能测试 (1个场景)
    # =====================================================

    def test_concurrent_performance(self, orchestrator):
        """场景6: 并发性能测试"""
        # Mock数据
        mock_data = {
            'pump_active_power': np.random.uniform(10, 50, 100)
        }
        mock_timestamps = np.arange(100)

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

                            # 测试并发性能
                            num_tasks = 10

                            start_time = time.time()

                            with ThreadPoolExecutor(max_workers=5) as executor:
                                futures = []
                                for i in range(num_tasks):
                                    future = executor.submit(
                                        orchestrator.calculate_missing_metrics,
                                        station_id=1,
                                        device_id=100 + i,
                                        start_time='2025-01-01 00:00:00',
                                        end_time='2025-01-01 01:40:00',
                                        metrics=['pump_flow_rate'],
                                        write_to_db=False
                                    )
                                    futures.append(future)

                                results = [future.result() for future in as_completed(futures)]

                            end_time = time.time()
                    duration = end_time - start_time
        
        # 验证性能
        assert len(results) == num_tasks
        # 并发执行应该比串行快（假设串行需要10秒，并发应该在5秒内完成）
        assert duration < 5.0
        # 验证所有任务成功
        assert all(r['success'] for r in results)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

