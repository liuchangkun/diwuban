"""
MethodSelector 单元测试

测试范围：
- 方法选择逻辑
- 依赖检查
- 条件检查
- 运行泵数统计
"""

import pytest
import pandas as pd
import numpy as np

from app.services.calculation.metrics.pump_flow_rate.method_selector import MethodSelector


class TestMethodSelector:
    """MethodSelector 单元测试"""

    @pytest.fixture
    def method_selector(self):
        """创建 MethodSelector 实例"""
        return MethodSelector()

    def test_select_method_a(self, method_selector):
        """测试：选择 Method A（功率×频率分摊）"""
        # 准备数据（多泵，有功率和频率）
        data = pd.DataFrame({
            'main_pipeline_flow_rate': [300.0] * 10,
            'pump_active_power': [45.0] * 10,
            'pump_frequency': [48.0] * 10,
            'other_devices': [[
                {'device_id': 106, 'pump_active_power': 45.0, 'pump_frequency': 48.0, 'running': 1}
            ] for _ in range(10)]
        })

        # 执行选择
        method_id = method_selector.select_method(data)

        # 断言：应该选择 Method A
        assert method_id == 'method_a'

    def test_select_method_b(self, method_selector):
        """测试：选择 Method B（累计流量导数）"""
        # 准备数据（有累计流量）
        data = pd.DataFrame({
            'main_pipeline_flow_rate': [100.0] * 10,
            'pump_cumulative_flow': np.arange(0, 100, 10.0),
            'ts_bucket': pd.date_range('2025-01-01', periods=10, freq='1s')
        })

        # 执行选择
        method_id = method_selector.select_method(data)

        # 断言：应该选择 Method B
        assert method_id == 'method_b'

    def test_select_method_c(self, method_selector):
        """测试：选择 Method C（单泵直读）"""
        # 准备数据（单泵）
        data = pd.DataFrame({
            'main_pipeline_flow_rate': [100.0] * 10,
            'other_devices': [[] for _ in range(10)]
        })

        # 执行选择
        method_id = method_selector.select_method(data)

        # 断言：应该选择 Method C
        assert method_id == 'method_c'

    def test_select_method_d(self, method_selector):
        """测试：选择 Method D（功率分摊）"""
        # 准备数据（多泵，只有功率）
        data = pd.DataFrame({
            'main_pipeline_flow_rate': [300.0] * 10,
            'pump_active_power': [45.0] * 10,
            'other_devices': [[
                {'device_id': 106, 'pump_active_power': 45.0, 'running': 1}
            ] for _ in range(10)]
        })

        # 执行选择
        method_id = method_selector.select_method(data)

        # 断言：应该选择 Method D
        assert method_id == 'method_d'

    def test_select_method_e(self, method_selector):
        """测试：选择 Method E（频率分摊）"""
        # 准备数据（多泵，只有频率）
        data = pd.DataFrame({
            'main_pipeline_flow_rate': [300.0] * 10,
            'pump_frequency': [48.0] * 10,
            'other_devices': [[
                {'device_id': 106, 'pump_frequency': 48.0, 'running': 1}
            ] for _ in range(10)]
        })

        # 执行选择
        method_id = method_selector.select_method(data)

        # 断言：应该选择 Method E
        assert method_id == 'method_e'

    def test_count_running_pumps_single(self, method_selector):
        """测试：统计运行泵数（单泵）"""
        # 准备数据（单泵）
        data = pd.DataFrame({
            'other_devices': [[] for _ in range(10)]
        })

        # 执行统计
        count = method_selector._count_running_pumps(data)

        # 断言：1台泵
        assert count == 1

    def test_count_running_pumps_multi(self, method_selector):
        """测试：统计运行泵数（多泵）"""
        # 准备数据（3泵）
        data = pd.DataFrame({
            'other_devices': [[
                {'device_id': 106, 'running': 1},
                {'device_id': 107, 'running': 1}
            ] for _ in range(10)]
        })

        # 执行统计
        count = method_selector._count_running_pumps(data)

        # 断言：3台泵
        assert count == 3

    def test_count_running_pumps_with_stopped(self, method_selector):
        """测试：统计运行泵数（包含停机泵）"""
        # 准备数据（2台运行，1台停机）
        data = pd.DataFrame({
            'other_devices': [[
                {'device_id': 106, 'running': 1},
                {'device_id': 107, 'running': 0}  # 停机
            ] for _ in range(10)]
        })

        # 执行统计
        count = method_selector._count_running_pumps(data)

        # 断言：2台泵（不包括停机泵）
        assert count == 2

    def test_check_dependencies_satisfied(self, method_selector):
        """测试：依赖检查 - 满足"""
        # 准备数据（包含所有依赖）
        data = pd.DataFrame({
            'main_pipeline_flow_rate': [100.0],
            'pump_active_power': [45.0],
            'pump_frequency': [48.0]
        })
        dependencies = ['main_pipeline_flow_rate', 'pump_active_power', 'pump_frequency']

        # 执行检查
        satisfied = method_selector._check_dependencies(data, dependencies)

        # 断言：满足
        assert satisfied is True

    def test_check_dependencies_not_satisfied(self, method_selector):
        """测试：依赖检查 - 不满足"""
        # 准备数据（缺少 pump_frequency）
        data = pd.DataFrame({
            'main_pipeline_flow_rate': [100.0],
            'pump_active_power': [45.0]
        })
        dependencies = ['main_pipeline_flow_rate', 'pump_active_power', 'pump_frequency']

        # 执行检查
        satisfied = method_selector._check_dependencies(data, dependencies)

        # 断言：不满足
        assert satisfied is False

    def test_no_method_available(self, method_selector):
        """测试：无可用方法"""
        # 准备数据（缺少所有依赖）
        data = pd.DataFrame({
            'unknown_column': [100.0]
        })

        # 执行选择（应该抛出 ValueError）
        with pytest.raises(ValueError, match="没有找到合适的计算方法"):
            method_selector.select_method(data)

