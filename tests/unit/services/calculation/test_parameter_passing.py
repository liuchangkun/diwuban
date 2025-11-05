"""
测试参数传递机制 - 验证参数从 orchestrator 到计算函数的完整传递链

测试场景:
1. 计算函数参数接收测试 (4个)
2. 参数传递链测试 (3个)
3. 参数缺失错误处理测试 (2个)
4. MethodDescriptor 参数携带测试 (2个)

总计: 11个测试场景
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from app.services.calculation.calculators import (
    calculate_main_pipeline_inlet_pressure_method_b,
    calculate_pump_inlet_pressure_method_b,
    calculate_pump_outlet_pressure_method_c,
    calculate_main_pipeline_outlet_pressure_method_b
)


class TestCalculatorParameterReceiving:
    """计算函数参数接收测试"""

    def test_main_pipeline_inlet_pressure_method_b_receives_params(self):
        """场景1: main_pipeline_inlet_pressure_method_b 正确接收物理常数参数"""
        # 准备测试数据
        data = {
            'pool_liquid_level': np.array([1.0, 2.0, 3.0])
        }
        params = {
            'P_atm': 0.101325,
            'rho': 1000.0,
            'g': 9.80665
        }

        # 调用计算函数
        result = calculate_main_pipeline_inlet_pressure_method_b(data, params)

        # 验证结果
        assert isinstance(result, np.ndarray)
        assert len(result) == 3
        assert not np.isnan(result[0])  # 第一个值应该有效
        
        # 验证计算公式：P = P_atm + rho * g * L / 1e6
        expected_0 = 0.101325 + 1000.0 * 9.80665 * 1.0 / 1e6
        assert np.isclose(result[0], expected_0, rtol=1e-5)

    def test_pump_inlet_pressure_method_b_receives_params(self):
        """场景2: pump_inlet_pressure_method_b 正确接收物理常数参数"""
        # 准备测试数据
        data = {
            'pool_liquid_level': np.array([0.5, 1.5, 2.5])
        }
        params = {
            'P_atm': 0.101325,
            'rho': 1000.0,
            'g': 9.80665
        }

        # 调用计算函数
        result = calculate_pump_inlet_pressure_method_b(data, params)

        # 验证结果
        assert isinstance(result, np.ndarray)
        assert len(result) == 3
        assert not np.isnan(result[0])

    def test_pump_outlet_pressure_method_c_receives_params(self):
        """场景3: pump_outlet_pressure_method_c 正确接收物理常数参数"""
        # 准备测试数据
        data = {
            'pump_head': np.array([10.0, 20.0, 30.0]),
            'pump_inlet_pressure': np.array([0.1, 0.15, 0.2])
        }
        params = {
            'rho': 1000.0,
            'g': 9.80665
        }

        # 调用计算函数
        result = calculate_pump_outlet_pressure_method_c(data, params)

        # 验证结果
        assert isinstance(result, np.ndarray)
        assert len(result) == 3
        assert not np.isnan(result[0])
        
        # 验证计算公式：P_out = P_in + rho * g * H / 1e6
        expected_0 = 0.1 + 1000.0 * 9.80665 * 10.0 / 1e6
        assert np.isclose(result[0], expected_0, rtol=1e-5)

    def test_main_pipeline_outlet_pressure_method_b_receives_params(self):
        """场景4: main_pipeline_outlet_pressure_method_b 正确接收物理常数参数"""
        # 准备测试数据
        data = {
            'pump_head': np.array([15.0, 25.0, 35.0]),
            'pump_inlet_pressure': np.array([0.12, 0.18, 0.22])
        }
        params = {
            'rho': 1000.0,
            'g': 9.80665
        }

        # 调用计算函数
        result = calculate_main_pipeline_outlet_pressure_method_b(data, params)

        # 验证结果
        assert isinstance(result, np.ndarray)
        assert len(result) == 3
        assert not np.isnan(result[0])


class TestParameterMissingErrors:
    """参数缺失错误处理测试"""

    def test_main_pipeline_inlet_pressure_method_b_missing_P_atm(self):
        """场景5: 缺少 P_atm 参数时抛出明确错误"""
        data = {
            'pool_liquid_level': np.array([1.0, 2.0, 3.0])
        }
        params = {
            'rho': 1000.0,
            'g': 9.80665
            # 缺少 P_atm
        }

        # 验证抛出 ValueError 并包含参数名称
        with pytest.raises(ValueError) as exc_info:
            calculate_main_pipeline_inlet_pressure_method_b(data, params)
        
        assert 'P_atm' in str(exc_info.value)
        assert '缺少必需的物理常数参数' in str(exc_info.value)

    def test_pump_outlet_pressure_method_c_missing_rho(self):
        """场景6: 缺少 rho 参数时抛出明确错误"""
        data = {
            'pump_head': np.array([10.0, 20.0, 30.0]),
            'pump_inlet_pressure': np.array([0.1, 0.15, 0.2])
        }
        params = {
            'g': 9.80665
            # 缺少 rho
        }

        # 验证抛出 ValueError 并包含参数名称
        with pytest.raises(ValueError) as exc_info:
            calculate_pump_outlet_pressure_method_c(data, params)
        
        assert 'rho' in str(exc_info.value)
        assert '缺少必需的物理常数参数' in str(exc_info.value)


class TestMethodDescriptorParameterCarrying:
    """MethodDescriptor 参数携带测试"""

    def test_method_descriptor_carries_params(self):
        """场景7: MethodDescriptor 正确携带参数"""
        from app.services.calculation.domain import MethodDescriptor
        
        params = {
            'P_atm': 0.101325,
            'rho': 1000.0,
            'g': 9.80665
        }
        
        method_desc = MethodDescriptor(
            method_id='main_pipeline_inlet_pressure_method_b',
            method_code='B',
            metric_key='main_pipeline_inlet_pressure',
            priority=90,
            dependencies=['pool_liquid_level'],
            conditions={},
            params=params,
            validator_hint=None
        )

        # 验证参数正确携带
        assert method_desc.params == params
        assert method_desc.params['P_atm'] == 0.101325
        assert method_desc.params['rho'] == 1000.0
        assert method_desc.params['g'] == 9.80665

    def test_method_descriptor_empty_params(self):
        """场景8: MethodDescriptor 可以携带空参数字典"""
        from app.services.calculation.domain import MethodDescriptor
        
        method_desc = MethodDescriptor(
            method_id='pump_flow_rate_method_c',
            method_code='C',
            metric_key='pump_flow_rate',
            priority=80,
            dependencies=['main_pipeline_flow_rate'],
            conditions={},
            params={},  # 空参数字典
            validator_hint=None
        )

        # 验证空参数字典
        assert method_desc.params == {}


class TestGetCalculatorUnifiedWrapper:
    """get_calculator_unified 包装器测试"""

    @patch('app.services.calculation.calculators.get_calculator')
    def test_wrapper_extracts_params_from_method_descriptor(self, mock_get_calculator):
        """场景9: 包装器正确从 MethodDescriptor 提取参数"""
        from app.services.calculation.calculators import get_calculator_unified
        from app.services.calculation.domain import MethodDescriptor, CalculationContext
        
        # 模拟基础计算函数
        mock_base_fn = Mock(return_value=np.array([1.0, 2.0, 3.0]))
        mock_get_calculator.return_value = mock_base_fn
        
        # 创建带参数的 MethodDescriptor
        params = {'P_atm': 0.101325, 'rho': 1000.0, 'g': 9.80665}
        method_desc = MethodDescriptor(
            method_id='test_method',
            method_code='A',
            metric_key='test_metric',
            priority=100,
            dependencies=[],
            conditions={},
            params=params,
            validator_hint=None
        )
        
        # 创建 CalculationContext
        from datetime import datetime
        ctx = CalculationContext(
            station_id=1,
            device_id=7,
            start_ts=datetime(2025, 1, 1, 0, 0, 0),
            end_ts=datetime(2025, 1, 1, 1, 0, 0)
        )
        
        # 调用包装器
        calculator = get_calculator_unified('test_method')
        data = {'test_data': np.array([1.0, 2.0, 3.0])}
        result, meta = calculator(ctx, method_desc, data)
        
        # 验证基础函数被调用时传入了正确的参数
        mock_base_fn.assert_called_once()
        call_args = mock_base_fn.call_args
        assert call_args[0][0] == data  # 第一个参数是 data
        assert call_args[0][1] == params  # 第二个参数是 params

    @patch('app.services.calculation.calculators.get_calculator')
    def test_wrapper_handles_empty_params(self, mock_get_calculator):
        """场景10: 包装器正确处理空参数"""
        from app.services.calculation.calculators import get_calculator_unified
        from app.services.calculation.domain import MethodDescriptor, CalculationContext
        
        # 模拟基础计算函数
        mock_base_fn = Mock(return_value=np.array([1.0, 2.0, 3.0]))
        mock_get_calculator.return_value = mock_base_fn
        
        # 创建不带参数的 MethodDescriptor
        method_desc = MethodDescriptor(
            method_id='test_method',
            method_code='A',
            metric_key='test_metric',
            priority=100,
            dependencies=[],
            conditions={},
            params={},  # 空参数
            validator_hint=None
        )
        
        # 创建 CalculationContext
        from datetime import datetime
        ctx = CalculationContext(
            station_id=1,
            device_id=7,
            start_ts=datetime(2025, 1, 1, 0, 0, 0),
            end_ts=datetime(2025, 1, 1, 1, 0, 0)
        )

        # 调用包装器
        calculator = get_calculator_unified('test_method')
        data = {'test_data': np.array([1.0, 2.0, 3.0])}
        result, meta = calculator(ctx, method_desc, data)

        # 验证基础函数被调用时传入了空参数字典
        mock_base_fn.assert_called_once()
        call_args = mock_base_fn.call_args
        assert call_args[0][1] == {}  # 第二个参数是空字典

