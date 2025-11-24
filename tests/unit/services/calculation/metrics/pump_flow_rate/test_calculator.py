"""
Calculator 单元测试

测试范围：
- 方法分发逻辑
- 参数加载
- 错误处理
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock

from app.services.calculation.metrics.pump_flow_rate.calculator import Calculator


class TestCalculator:
    """Calculator 单元测试"""

    @pytest.fixture
    def calculator(self, mock_parameter_manager):
        """创建 Calculator 实例"""
        return Calculator(param_manager=mock_parameter_manager)

    def test_calculate_method_a(self, calculator):
        """测试：调用 Method A"""
        # 准备数据
        data = pd.DataFrame({
            'main_pipeline_flow_rate': [100.0] * 10,
            'pump_active_power': [45.0] * 10,
            'pump_frequency': [48.0] * 10,
            'other_devices': [[] for _ in range(10)]
        })
        params = {'alpha': 1.0, 'beta': 1.0}

        # 执行计算
        result = calculator.calculate(data, 'method_a', params)

        # 断言
        assert result is not None
        assert len(result) == 10
        assert 'pump_flow_rate' in result.columns

    def test_calculate_method_b(self, calculator):
        """测试：调用 Method B"""
        # 准备数据
        data = pd.DataFrame({
            'pump_cumulative_flow': np.arange(0, 100, 1.0),
            'ts_bucket': pd.date_range('2025-01-01', periods=100, freq='1s')
        })
        params = {'derivative_window': 5}

        # 执行计算
        result = calculator.calculate(data, 'method_b', params)

        # 断言
        assert result is not None
        assert len(result) > 0
        assert 'pump_flow_rate' in result.columns

    def test_calculate_method_c(self, calculator):
        """测试：调用 Method C"""
        # 准备数据
        data = pd.DataFrame({
            'main_pipeline_flow_rate': [100.0, 120.0, 140.0]
        })
        params = {}

        # 执行计算
        result = calculator.calculate(data, 'method_c', params)

        # 断言
        assert result is not None
        assert len(result) == 3
        assert 'pump_flow_rate' in result.columns

    def test_calculate_method_d(self, calculator):
        """测试：调用 Method D"""
        # 准备数据
        data = pd.DataFrame({
            'main_pipeline_flow_rate': [100.0] * 10,
            'pump_active_power': [45.0] * 10,
            'other_devices': [[] for _ in range(10)]
        })
        params = {'alpha': 1.0}

        # 执行计算
        result = calculator.calculate(data, 'method_d', params)

        # 断言
        assert result is not None
        assert len(result) == 10
        assert 'pump_flow_rate' in result.columns

    def test_calculate_method_e(self, calculator):
        """测试：调用 Method E"""
        # 准备数据
        data = pd.DataFrame({
            'main_pipeline_flow_rate': [100.0] * 10,
            'pump_frequency': [48.0] * 10,
            'other_devices': [[] for _ in range(10)]
        })
        params = {'beta': 1.0}

        # 执行计算
        result = calculator.calculate(data, 'method_e', params)

        # 断言
        assert result is not None
        assert len(result) == 10
        assert 'pump_flow_rate' in result.columns

    def test_calculate_invalid_method(self, calculator):
        """测试：无效的方法ID"""
        # 准备数据
        data = pd.DataFrame({
            'main_pipeline_flow_rate': [100.0]
        })

        # 执行计算（应该抛出异常）
        with pytest.raises(ValueError):
            calculator.calculate(data, 'invalid_method', {})

    def test_calculate_with_parameter_manager(self, mock_parameter_manager):
        """测试：使用 ParameterManager 加载参数"""
        # 创建 Calculator（带 ParameterManager）
        calculator = Calculator(param_manager=mock_parameter_manager)

        # 准备数据
        data = pd.DataFrame({
            'main_pipeline_flow_rate': [100.0] * 10,
            'pump_active_power': [45.0] * 10,
            'pump_frequency': [48.0] * 10,
            'other_devices': [[] for _ in range(10)]
        })

        # 执行计算（不传递 params，应该从 ParameterManager 加载）
        result = calculator.calculate(data, 'method_a', params=None)

        # 断言
        assert result is not None
        assert len(result) == 10
        # 验证 ParameterManager 被调用
        mock_parameter_manager.get_parameters.assert_called_once_with(
            metric_key='pump_flow_rate',
            method_id='method_a'
        )

    def test_calculate_empty_data(self, calculator):
        """测试：空数据"""
        # 准备空数据
        data = pd.DataFrame(columns=['main_pipeline_flow_rate'])

        # 执行计算
        result = calculator.calculate(data, 'method_c', {})

        # 断言：返回空 DataFrame
        assert result is not None
        assert len(result) == 0
        assert 'pump_flow_rate' in result.columns

