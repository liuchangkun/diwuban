"""
测试 calculation/calculators.py - 计算器注册表

测试场景:
1. 注册表测试 (3个)
2. get_calculator测试 (4个)
3. get_calculator_unified测试 (3个)

总计: 10个测试场景
"""

import pytest
import numpy as np
from app.services.calculation.calculators import (
    CALCULATOR_REGISTRY,
    get_calculator,
    get_calculator_unified
)
from app.services.calculation.domain import CalculationContext, MethodDescriptor
from datetime import datetime, timezone


class TestCalculatorRegistry:
    """计算器注册表测试"""

    def test_registry_contains_all_methods(self):
        """场景1: 注册表包含所有计算方法"""
        # 验证注册表不为空
        assert len(CALCULATOR_REGISTRY) > 0
        
        # 验证包含关键方法
        expected_methods = [
            'pump_flow_rate_method_a',
            'pump_head_method_main',
            'pump_outlet_pressure_method_a',
            'EFF_SIMPLE_V1',
            'HEAD_COEF_V1',
        ]
        
        for method in expected_methods:
            assert method in CALCULATOR_REGISTRY, f"缺少方法: {method}"

    def test_registry_all_values_are_callable(self):
        """场景2: 注册表中所有值都是可调用的函数"""
        for method_id, calculator in CALCULATOR_REGISTRY.items():
            assert callable(calculator), f"方法 {method_id} 不是可调用对象"

    def test_registry_method_ids_are_unique(self):
        """场景3: 注册表中的方法ID是唯一的"""
        method_ids = list(CALCULATOR_REGISTRY.keys())
        unique_ids = set(method_ids)
        
        # 验证没有重复的ID
        assert len(method_ids) == len(unique_ids), "注册表中存在重复的方法ID"


class TestGetCalculator:
    """get_calculator函数测试"""

    def test_get_calculator_existing_method(self):
        """场景4: 获取存在的计算器"""
        calculator = get_calculator('pump_flow_rate_method_a')
        
        # 验证返回的是可调用对象
        assert callable(calculator)

    def test_get_calculator_nonexistent_method(self):
        """场景5: 获取不存在的计算器应该抛出KeyError"""
        with pytest.raises(KeyError) as exc_info:
            get_calculator('nonexistent_method')
        
        assert "未找到计算函数" in str(exc_info.value)

    def test_get_calculator_returns_correct_function(self):
        """场景6: 验证返回的是正确的函数"""
        calculator = get_calculator('pump_flow_rate_method_a')
        
        # 验证函数名称
        assert calculator.__name__ == 'calculate_pump_flow_rate_method_a'

    def test_get_calculator_all_registered_methods(self):
        """场景7: 验证所有注册的方法都可以获取"""
        for method_id in CALCULATOR_REGISTRY.keys():
            calculator = get_calculator(method_id)
            assert callable(calculator), f"方法 {method_id} 获取失败"


class TestGetCalculatorUnified:
    """get_calculator_unified函数测试"""

    def test_get_calculator_unified_returns_wrapper(self):
        """场景8: get_calculator_unified返回包装函数"""
        wrapper = get_calculator_unified('pump_flow_rate_method_a')
        
        # 验证返回的是可调用对象
        assert callable(wrapper)

    def test_get_calculator_unified_wrapper_signature(self):
        """场景9: 验证包装函数的签名"""
        wrapper = get_calculator_unified('pump_flow_rate_method_a')
        
        # 创建测试数据
        ctx = CalculationContext(
            station_id=1,
            device_id=10,
            start_ts=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            end_ts=datetime(2025, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
        )
        
        method = MethodDescriptor(
            method_id='pump_flow_rate_method_a',
            method_code='A',
            metric_key='pump_flow_rate',
            priority=10,
            params={}
        )
        
        data = {
            'main_pipeline_flow_rate': np.array([100.0, 105.0, 98.0]),
            '__pump_flow_rate_share': np.array([0.5, 0.5, 0.5])
        }
        
        # 调用包装函数
        values, meta = wrapper(ctx, method, data)
        
        # 验证返回值类型
        assert isinstance(values, np.ndarray)
        assert isinstance(meta, dict)
        assert 'method_id' in meta
        assert 'method_code' in meta

    def test_get_calculator_unified_nonexistent_method(self):
        """场景10: get_calculator_unified获取不存在的方法应该抛出KeyError"""
        with pytest.raises(KeyError):
            get_calculator_unified('nonexistent_method')

