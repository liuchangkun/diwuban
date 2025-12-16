"""
Pipeline 集成测试

测试范围：
- 完整的6阶段流水线
- 端到端流程
- 多设备并行处理
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.services.calculation.metrics.pump_flow_rate.data_loader import DataLoader
from app.services.calculation.metrics.pump_flow_rate.data_filter import DataFilter
from app.services.calculation.metrics.pump_flow_rate.method_selector import MethodSelector
from app.services.calculation.metrics.pump_flow_rate.calculator import Calculator
from app.services.calculation.metrics.pump_flow_rate.validator import Validator


class TestPipelineIntegration:
    """Pipeline 集成测试"""

    @pytest.fixture
    def pipeline_components(self, test_config, mock_parameter_manager):
        """创建流水线组件"""
        return {
            'data_loader': DataLoader(),
            'data_filter': DataFilter(
                max_flow=test_config.get('max_flow', 500.0),
                max_power=200.0,
                max_freq=50.0
            ),
            'method_selector': MethodSelector(),
            'calculator': Calculator(param_manager=mock_parameter_manager),
            'validator': Validator(params=test_config)
        }

    def test_end_to_end_single_device(self, pipeline_components, sample_data):
        """测试：单设备端到端流程"""
        # 1. 数据过滤
        filtered_data = pipeline_components['data_filter'].filter_data(sample_data)
        assert len(filtered_data) > 0

        # 2. 方法选择
        method_id = pipeline_components['method_selector'].select_method(filtered_data)
        assert method_id is not None

        # 3. 计算执行
        params = {'alpha': 1.0, 'beta': 1.0}
        results = pipeline_components['calculator'].calculate(filtered_data, method_id, params)
        assert len(results) > 0
        assert 'pump_flow_rate' in results.columns

        # 4. 结果验证
        validation_result = pipeline_components['validator'].validate(results, filtered_data)
        assert validation_result['valid_count'] > 0
        assert validation_result['quality_code'] in [0, 1, 2, 3]

    def test_end_to_end_multi_device(self, pipeline_components, sample_multi_device_data):
        """测试：多设备端到端流程"""
        # 1. 数据过滤
        filtered_data = pipeline_components['data_filter'].filter_data(sample_multi_device_data)
        assert len(filtered_data) > 0

        # 2. 方法选择
        method_id = pipeline_components['method_selector'].select_method(filtered_data)
        assert method_id is not None

        # 3. 计算执行
        params = {'alpha': 1.0, 'beta': 1.0}
        results = pipeline_components['calculator'].calculate(filtered_data, method_id, params)
        assert len(results) > 0
        assert 'pump_flow_rate' in results.columns

        # 4. 结果验证
        validation_result = pipeline_components['validator'].validate(results, filtered_data)
        assert validation_result['valid_count'] > 0

    def test_end_to_end_with_stopped_pump(self, pipeline_components, sample_data_with_stopped_pump):
        """测试：包含停机泵的端到端流程"""
        # 1. 数据过滤（应该过滤掉停机数据）
        filtered_data = pipeline_components['data_filter'].filter_data(sample_data_with_stopped_pump)
        assert len(filtered_data) == 50  # 只保留运行的50条

        # 2. 方法选择
        method_id = pipeline_components['method_selector'].select_method(filtered_data)
        assert method_id is not None

        # 3. 计算执行
        params = {'alpha': 1.0, 'beta': 1.0}
        results = pipeline_components['calculator'].calculate(filtered_data, method_id, params)
        assert len(results) == 50

        # 4. 结果验证
        validation_result = pipeline_components['validator'].validate(results, filtered_data)
        assert validation_result['valid_count'] > 0

    def test_pipeline_with_all_methods(self, pipeline_components):
        """测试：所有计算方法的流水线"""
        methods_to_test = ['method_a', 'method_b', 'method_c', 'method_d', 'method_e']

        for method_id in methods_to_test:
            # 准备适合该方法的数据
            if method_id == 'method_a':
                # Method A: 功率分摊法（需要 main_pipeline_flow_rate, pump_active_power, pump_frequency, other_devices）
                data = pd.DataFrame({
                    'ts_bucket': pd.date_range('2025-01-01', periods=10, freq='1s'),
                    'device_id': [105] * 10,
                    'main_pipeline_flow_rate': [300.0] * 10,
                    'pump_active_power': [45.0] * 10,
                    'pump_frequency': [48.0] * 10,
                    'running': [1] * 10,
                    'other_devices': [[{'device_id': 106, 'pump_active_power': 45.0, 'pump_frequency': 48.0, 'running': 1}] for _ in range(10)]
                })
                params = {'alpha': 1.0, 'beta': 1.0}
            elif method_id == 'method_b':
                # Method B: 累计流量差分法（需要 pump_cumulative_flow, ts_bucket）
                # 累计流量每秒增加10 m³，即流量为 10 m³/s = 36000 m³/h
                # 但这太大了，调整为每秒增加0.1 m³，即流量为 0.1 m³/s = 360 m³/h
                data = pd.DataFrame({
                    'ts_bucket': pd.date_range('2025-01-01', periods=10, freq='1s'),
                    'device_id': [105] * 10,
                    'pump_cumulative_flow': np.arange(0, 1.0, 0.1),  # 每秒增加0.1 m³
                    'main_pipeline_flow_rate': [400.0] * 10,  # 总管流量400 m³/h（大于单泵流量360 m³/h）
                    'pump_active_power': [45.0] * 10,  # 添加必需列（用于过滤）
                    'pump_frequency': [48.0] * 10,  # 添加必需列（用于过滤）
                    'running': [1] * 10
                })
                params = {'derivative_window': 5}
            elif method_id == 'method_c':
                # Method C: 单泵法（需要 main_pipeline_flow_rate, other_devices 为空）
                data = pd.DataFrame({
                    'ts_bucket': pd.date_range('2025-01-01', periods=10, freq='1s'),
                    'device_id': [105] * 10,
                    'main_pipeline_flow_rate': [100.0] * 10,
                    'pump_active_power': [45.0] * 10,  # 添加必需列（用于过滤）
                    'pump_frequency': [48.0] * 10,  # 添加必需列（用于过滤）
                    'running': [1] * 10,
                    'other_devices': [[] for _ in range(10)]
                })
                params = {}
            elif method_id == 'method_d':
                # Method D: 功率分摊法简化版（需要 main_pipeline_flow_rate, pump_active_power, other_devices）
                data = pd.DataFrame({
                    'ts_bucket': pd.date_range('2025-01-01', periods=10, freq='1s'),
                    'device_id': [105] * 10,
                    'main_pipeline_flow_rate': [300.0] * 10,
                    'pump_active_power': [45.0] * 10,
                    'pump_frequency': [48.0] * 10,  # 添加必需列（用于过滤）
                    'running': [1] * 10,
                    'other_devices': [[{'device_id': 106, 'pump_active_power': 45.0, 'running': 1}] for _ in range(10)]
                })
                params = {'alpha': 1.0}
            else:  # method_e
                # Method E: 频率分摊法（需要 main_pipeline_flow_rate, pump_frequency, other_devices）
                data = pd.DataFrame({
                    'ts_bucket': pd.date_range('2025-01-01', periods=10, freq='1s'),
                    'device_id': [105] * 10,
                    'main_pipeline_flow_rate': [300.0] * 10,
                    'pump_active_power': [45.0] * 10,  # 添加必需列（用于过滤）
                    'pump_frequency': [48.0] * 10,
                    'running': [1] * 10,
                    'other_devices': [[{'device_id': 106, 'pump_frequency': 48.0, 'running': 1}] for _ in range(10)]
                })
                params = {'beta': 1.0}

            # 执行流水线
            filtered_data = pipeline_components['data_filter'].filter_data(data)
            assert len(filtered_data) > 0, f"Method {method_id} failed: data filtered out completely"

            results = pipeline_components['calculator'].calculate(filtered_data, method_id, params)
            assert len(results) > 0, f"Method {method_id} failed: no results"

            validation_result = pipeline_components['validator'].validate(results, filtered_data)
            assert validation_result['valid_count'] > 0, f"Method {method_id} failed: no valid results"

    def test_pipeline_error_handling(self, pipeline_components):
        """测试：流水线错误处理"""
        # 测试1: 缺少必需列的数据（应该抛出 ValueError）
        invalid_data = pd.DataFrame({
            'unknown_column': [100.0]
        })

        # 执行方法选择（应该抛出 ValueError）
        with pytest.raises(ValueError, match="没有找到合适的计算方法"):
            method_id = pipeline_components['method_selector'].select_method(invalid_data)

        # 测试2: 数据过滤后为空
        empty_data = pd.DataFrame({
            'main_pipeline_flow_rate': [1000.0] * 10,  # 超过 max_flow (500.0)
            'pump_active_power': [45.0] * 10,
            'pump_frequency': [48.0] * 10,
            'running': [1] * 10
        })

        filtered_data = pipeline_components['data_filter'].filter_data(empty_data)
        assert len(filtered_data) == 0, "Data should be filtered out due to outliers"

        # 测试3: 无效的方法ID（应该抛出 ValueError）
        valid_data = pd.DataFrame({
            'main_pipeline_flow_rate': [100.0] * 10,
            'pump_active_power': [45.0] * 10,
            'pump_frequency': [48.0] * 10,
            'running': [1] * 10
        })

        with pytest.raises(ValueError, match="未知的方法ID"):
            # 无效的方法ID应该抛出异常
            results = pipeline_components['calculator'].calculate(
                valid_data,
                'invalid_method',
                {}
            )

