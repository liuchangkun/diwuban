"""
Methods 单元测试

测试范围：
- Method A: 功率×频率分摊
- Method B: 累计流量导数
- Method C: 单泵直读
- Method D: 功率分摊
- Method E: 频率分摊
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from app.services.calculation.metrics.pump_flow_rate.methods import (
    method_a, method_b, method_c, method_d, method_e
)


class TestMethodA:
    """Method A 单元测试：功率×频率分摊"""

    def test_method_a_single_pump(self):
        """测试：单泵场景"""
        # 准备数据（单泵）
        data = pd.DataFrame({
            'main_pipeline_flow_rate': [100.0] * 10,
            'pump_active_power': [45.0] * 10,
            'pump_frequency': [48.0] * 10,
            'other_devices': [[] for _ in range(10)]
        })
        params = {'alpha': 1.0, 'beta': 1.0}

        # 执行计算
        result = method_a.calculate_method_a(data, params)

        # 断言：单泵时，流量 = 总管流量
        assert len(result) == 10
        assert all(np.isclose(result['pump_flow_rate'], 100.0))

    def test_method_a_multi_pump(self):
        """测试：多泵场景"""
        # 准备数据（3泵，功率和频率相同）
        other_devices = []
        for _ in range(10):
            other_devices.append([
                {'device_id': 106, 'pump_active_power': 45.0, 'pump_frequency': 48.0, 'running': 1},
                {'device_id': 107, 'pump_active_power': 45.0, 'pump_frequency': 48.0, 'running': 1}
            ])
        
        data = pd.DataFrame({
            'main_pipeline_flow_rate': [300.0] * 10,
            'pump_active_power': [45.0] * 10,
            'pump_frequency': [48.0] * 10,
            'other_devices': other_devices
        })
        params = {'alpha': 1.0, 'beta': 1.0}

        # 执行计算
        result = method_a.calculate_method_a(data, params)

        # 断言：3泵均分，每泵 100.0
        assert len(result) == 10
        assert all(np.isclose(result['pump_flow_rate'], 100.0, atol=0.1))


class TestMethodB:
    """Method B 单元测试：累计流量导数"""

    def test_method_b_constant_rate(self):
        """测试：恒定流量"""
        # 准备数据（累计流量线性增长）
        data = pd.DataFrame({
            'pump_cumulative_flow': np.arange(0, 100, 1.0),  # 每秒增加1 m³
            'ts_bucket': pd.date_range('2025-01-01', periods=100, freq='1s')
        })
        params = {'derivative_window': 5}

        # 执行计算
        result = method_b.calculate_method_b(data, params)

        # 断言：流量 = 1 m³/s = 3600 m³/h
        assert len(result) > 0
        assert all(np.isclose(result['pump_flow_rate'], 3600.0, atol=100.0))

    def test_method_b_zero_flow(self):
        """测试：零流量"""
        # 准备数据（累计流量不变）
        data = pd.DataFrame({
            'pump_cumulative_flow': [100.0] * 100,
            'ts_bucket': pd.date_range('2025-01-01', periods=100, freq='1s')
        })
        params = {'derivative_window': 5}

        # 执行计算
        result = method_b.calculate_method_b(data, params)

        # 断言：流量 = 0
        assert len(result) > 0
        assert all(np.isclose(result['pump_flow_rate'], 0.0, atol=10.0))


class TestMethodC:
    """Method C 单元测试：单泵直读"""

    def test_method_c_single_pump(self):
        """测试：单泵场景"""
        # 准备数据（单泵）
        data = pd.DataFrame({
            'main_pipeline_flow_rate': [100.0, 120.0, 140.0, 160.0, 180.0]
        })
        params = {}

        # 执行计算
        result = method_c.calculate_method_c(data, params)

        # 断言：流量 = 总管流量
        assert len(result) == 5
        assert all(result['pump_flow_rate'] == data['main_pipeline_flow_rate'])


class TestMethodD:
    """Method D 单元测试：功率分摊"""

    def test_method_d_single_pump(self):
        """测试：单泵场景"""
        # 准备数据（单泵）
        data = pd.DataFrame({
            'main_pipeline_flow_rate': [100.0] * 10,
            'pump_active_power': [45.0] * 10,
            'other_devices': [[] for _ in range(10)]
        })
        params = {'alpha': 1.0}

        # 执行计算
        result = method_d.calculate_method_d(data, params)

        # 断言：单泵时，流量 = 总管流量
        assert len(result) == 10
        assert all(np.isclose(result['pump_flow_rate'], 100.0))

    def test_method_d_multi_pump(self):
        """测试：多泵场景（功率相同）"""
        # 准备数据（3泵，功率相同）
        other_devices = []
        for _ in range(10):
            other_devices.append([
                {'device_id': 106, 'pump_active_power': 45.0, 'running': 1},
                {'device_id': 107, 'pump_active_power': 45.0, 'running': 1}
            ])
        
        data = pd.DataFrame({
            'main_pipeline_flow_rate': [300.0] * 10,
            'pump_active_power': [45.0] * 10,
            'other_devices': other_devices
        })
        params = {'alpha': 1.0}

        # 执行计算
        result = method_d.calculate_method_d(data, params)

        # 断言：3泵均分，每泵 100.0
        assert len(result) == 10
        assert all(np.isclose(result['pump_flow_rate'], 100.0, atol=0.1))


class TestMethodE:
    """Method E 单元测试：频率分摊"""

    def test_method_e_single_pump(self):
        """测试：单泵场景"""
        # 准备数据（单泵）
        data = pd.DataFrame({
            'main_pipeline_flow_rate': [100.0] * 10,
            'pump_frequency': [48.0] * 10,
            'other_devices': [[] for _ in range(10)]
        })
        params = {'beta': 1.0}

        # 执行计算
        result = method_e.calculate_method_e(data, params)

        # 断言：单泵时，流量 = 总管流量
        assert len(result) == 10
        assert all(np.isclose(result['pump_flow_rate'], 100.0))

    def test_method_e_multi_pump(self):
        """测试：多泵场景（频率相同）"""
        # 准备数据（3泵，频率相同）
        other_devices = []
        for _ in range(10):
            other_devices.append([
                {'device_id': 106, 'pump_frequency': 48.0, 'running': 1},
                {'device_id': 107, 'pump_frequency': 48.0, 'running': 1}
            ])
        
        data = pd.DataFrame({
            'main_pipeline_flow_rate': [300.0] * 10,
            'pump_frequency': [48.0] * 10,
            'other_devices': other_devices
        })
        params = {'beta': 1.0}

        # 执行计算
        result = method_e.calculate_method_e(data, params)

        # 断言：3泵均分，每泵 100.0
        assert len(result) == 10
        assert all(np.isclose(result['pump_flow_rate'], 100.0, atol=0.1))

