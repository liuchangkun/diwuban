"""
pump_speed MethodSelector 单元测试

测试目标：
- 验证方法选择逻辑
- 验证依赖检查
- 验证条件检查
- 验证优先级排序
"""

import pytest
import pandas as pd
from datetime import datetime
from app.services.calculation.metrics.pump_speed.method_selector import MethodSelector


class TestMethodSelector:
    """MethodSelector 单元测试"""

    @pytest.fixture
    def selector(self):
        """创建MethodSelector实例"""
        params = {
            'f_ref': 50.0,
            'n_ref': 1500.0
        }
        return MethodSelector(params=params, trace_id='test_method_selector')

    @pytest.fixture
    def data_with_frequency(self):
        """包含pump_frequency的数据"""
        return pd.DataFrame({
            'ts_bucket': [datetime(2025, 10, 22, 8, 0, 0)],
            'device_id': [1],
            'pump_frequency': [45.0],
            'running': [1]
        })

    @pytest.fixture
    def data_with_pole_pairs(self):
        """包含pole_pairs和slip的数据"""
        return pd.DataFrame({
            'ts_bucket': [datetime(2025, 10, 22, 8, 0, 0)],
            'device_id': [1],
            'pump_frequency': [45.0],
            'pole_pairs': [2],
            'slip': [0.02],
            'running': [1]
        })

    @pytest.fixture
    def data_with_calibration(self):
        """包含校准系数的数据"""
        return pd.DataFrame({
            'ts_bucket': [datetime(2025, 10, 22, 8, 0, 0)],
            'device_id': [1],
            'pump_frequency': [45.0],
            'speed_calibration_k': [1.05],
            'speed_calibration_b': [10.0],
            'calibration_quality': ['high'],
            'running': [1]
        })

    def test_select_method_a(self, selector, data_with_frequency):
        """
        测试用例3.1：选择method_a（频率比例法）
        
        验证当只有pump_frequency时，选择method_a
        """
        method_id = selector.select_method(data_with_frequency)
        
        # 断言：选择method_a
        assert method_id == 'method_a'

    def test_select_method_b(self, selector, data_with_pole_pairs):
        """
        测试用例3.2：选择method_b（极对数法）
        
        验证当有pole_pairs和slip时，选择method_b（优先级更高）
        """
        method_id = selector.select_method(data_with_pole_pairs)
        
        # 断言：选择method_b
        assert method_id == 'method_b'

    def test_select_method_c(self, selector, data_with_calibration):
        """
        测试用例3.3：选择method_c（校准系数法）
        
        验证当有校准系数时，选择method_c（优先级最高）
        """
        method_id = selector.select_method(data_with_calibration)
        
        # 断言：选择method_c
        assert method_id == 'method_c'

    def test_select_method_priority(self, selector):
        """
        测试用例3.4：优先级排序

        验证当多个方法都可用时，选择优先级最高的方法
        """
        # 包含所有依赖的数据
        data_all = pd.DataFrame({
            'ts_bucket': [datetime(2025, 10, 22, 8, 0, 0)],
            'device_id': [1],
            'pump_frequency': [45.0],
            'pole_pairs': [2],
            'slip': [0.02],
            'speed_calibration_k': [1.05],
            'speed_calibration_b': [10.0],
            'calibration_quality': ['high'],
            'running': [1]
        })

        method_id = selector.select_method(data_all)

        # 断言：选择优先级最高的method_c
        assert method_id == 'method_c'

    def test_select_method_no_data(self, selector):
        """
        测试用例3.5：无可用方法
        
        验证当没有任何依赖数据时，抛出异常
        """
        # 空数据
        data_empty = pd.DataFrame({
            'ts_bucket': [datetime(2025, 10, 22, 8, 0, 0)],
            'device_id': [1],
            'running': [1]
        })

        # 断言：抛出ValueError
        with pytest.raises(ValueError, match="没有合适的计算方法"):
            selector.select_method(data_empty)

    def test_check_dependencies(self, selector, data_with_frequency):
        """
        测试用例3.6：依赖检查
        
        验证依赖检查逻辑
        """
        # method_a依赖pump_frequency
        dependencies_met = selector._check_dependencies(
            data_with_frequency,
            ['pump_frequency']
        )
        
        # 断言：依赖满足
        assert dependencies_met is True

        # method_b依赖pole_pairs和slip
        dependencies_met = selector._check_dependencies(
            data_with_frequency,
            ['pole_pairs', 'slip']
        )
        
        # 断言：依赖不满足
        assert dependencies_met is False

    def test_check_conditions(self, selector, data_with_frequency):
        """
        测试用例3.7：条件检查
        
        验证条件检查逻辑
        """
        # 无条件限制
        conditions_met = selector._check_conditions(
            data_with_frequency,
            {}
        )
        
        # 断言：条件满足
        assert conditions_met is True

