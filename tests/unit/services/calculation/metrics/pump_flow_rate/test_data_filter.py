"""
DataFilter 单元测试

测试范围：
- 停机状态过滤（running=1）
- NaN/Inf 过滤
- 负值过滤
- 异常值过滤
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from app.services.calculation.metrics.pump_flow_rate.data_filter import DataFilter


class TestDataFilter:
    """DataFilter 单元测试"""

    @pytest.fixture
    def data_filter(self, test_config):
        """创建 DataFilter 实例"""
        return DataFilter(
            max_flow=test_config.get('max_flow', 500.0),
            max_power=test_config.get('max_power', 200.0),
            max_freq=test_config.get('max_freq', 50.0)
        )

    def test_filter_running_status(self, data_filter):
        """测试：过滤停机状态（running=0）"""
        # 准备数据（50条运行，50条停机）
        data = pd.DataFrame({
            'ts_bucket': pd.date_range('2025-01-01', periods=100, freq='1s'),
            'running': [1] * 50 + [0] * 50,
            'main_pipeline_flow_rate': [100.0] * 100,
            'pump_active_power': [45.0] * 100,
            'pump_frequency': [48.0] * 100
        })

        # 执行过滤
        filtered = data_filter.filter_data(data)

        # 断言：只保留 running=1 的数据
        assert len(filtered) == 50
        assert all(filtered['running'] == 1)

    def test_filter_nan_values(self, data_filter):
        """测试：过滤 NaN 值"""
        # 准备数据（包含 NaN）
        data = pd.DataFrame({
            'ts_bucket': pd.date_range('2025-01-01', periods=100, freq='1s'),
            'running': [1] * 100,
            'main_pipeline_flow_rate': [100.0] * 50 + [np.nan] * 50,
            'pump_active_power': [45.0] * 100,
            'pump_frequency': [48.0] * 100
        })

        # 执行过滤
        filtered = data_filter.filter_data(data)

        # 断言：移除 NaN 值
        assert len(filtered) == 50
        assert not filtered['main_pipeline_flow_rate'].isna().any()

    def test_filter_inf_values(self, data_filter):
        """测试：过滤 Inf 值"""
        # 准备数据（包含 Inf）
        data = pd.DataFrame({
            'ts_bucket': pd.date_range('2025-01-01', periods=100, freq='1s'),
            'running': [1] * 100,
            'main_pipeline_flow_rate': [100.0] * 50 + [np.inf] * 50,
            'pump_active_power': [45.0] * 100,
            'pump_frequency': [48.0] * 100
        })

        # 执行过滤
        filtered = data_filter.filter_data(data)

        # 断言：移除 Inf 值
        assert len(filtered) == 50
        assert not np.isinf(filtered['main_pipeline_flow_rate']).any()

    def test_filter_negative_values(self, data_filter):
        """测试：过滤负值"""
        # 准备数据（包含负值）
        data = pd.DataFrame({
            'ts_bucket': pd.date_range('2025-01-01', periods=100, freq='1s'),
            'running': [1] * 100,
            'main_pipeline_flow_rate': [100.0] * 50 + [-10.0] * 50,
            'pump_active_power': [45.0] * 100,
            'pump_frequency': [48.0] * 100
        })

        # 执行过滤
        filtered = data_filter.filter_data(data)

        # 断言：移除负值
        assert len(filtered) == 50
        assert all(filtered['main_pipeline_flow_rate'] >= 0)

    def test_filter_outliers(self, data_filter):
        """测试：过滤异常值（超过 max_flow）"""
        # 准备数据（包含异常值）
        data = pd.DataFrame({
            'ts_bucket': pd.date_range('2025-01-01', periods=100, freq='1s'),
            'running': [1] * 100,
            'main_pipeline_flow_rate': [100.0] * 50 + [600.0] * 50,  # 600 > max_flow(500)
            'pump_active_power': [45.0] * 100,
            'pump_frequency': [48.0] * 100
        })

        # 执行过滤
        filtered = data_filter.filter_data(data)

        # 断言：移除异常值
        assert len(filtered) == 50
        assert all(filtered['main_pipeline_flow_rate'] <= data_filter.max_flow)

    def test_filter_combined(self, data_filter):
        """测试：组合过滤（多种无效值）"""
        # 准备数据（包含多种无效值）
        data = pd.DataFrame({
            'ts_bucket': pd.date_range('2025-01-01', periods=100, freq='1s'),
            'running': [1] * 20 + [0] * 20 + [1] * 60,  # 20条停机
            'main_pipeline_flow_rate': (
                [100.0] * 20 +  # 有效
                [100.0] * 20 +  # 停机（会被过滤）
                [np.nan] * 20 +  # NaN
                [-10.0] * 20 +  # 负值
                [600.0] * 20    # 异常值
            ),
            'pump_active_power': [45.0] * 100,
            'pump_frequency': [48.0] * 100
        })

        # 执行过滤
        filtered = data_filter.filter_data(data)

        # 断言：只保留有效数据
        assert len(filtered) == 20
        assert all(filtered['running'] == 1)
        assert not filtered['main_pipeline_flow_rate'].isna().any()
        assert all(filtered['main_pipeline_flow_rate'] >= 0)
        assert all(filtered['main_pipeline_flow_rate'] <= data_filter.max_flow)

    def test_empty_data(self, data_filter):
        """测试：空数据"""
        # 准备空数据
        data = pd.DataFrame(columns=['ts_bucket', 'running', 'main_pipeline_flow_rate', 'pump_active_power', 'pump_frequency'])

        # 执行过滤
        filtered = data_filter.filter_data(data)

        # 断言：返回空 DataFrame
        assert len(filtered) == 0

