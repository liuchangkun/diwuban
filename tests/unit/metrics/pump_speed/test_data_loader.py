"""
pump_speed DataLoader 单元测试

测试目标：
- 验证DataLoader能正确加载pump_frequency数据
- 验证空数据处理
- 验证设备类型过滤
- 验证时间范围过滤
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from app.services.calculation.metrics.pump_speed.data_loader import DataLoader


class TestDataLoader:
    """DataLoader 单元测试"""

    @pytest.fixture
    def loader(self):
        """创建DataLoader实例"""
        return DataLoader(trace_id='test_data_loader')

    @pytest.fixture
    def test_time_range(self):
        """测试时间范围"""
        return {
            'start_time': datetime(2025, 10, 22, 16, 0, 0),
            'end_time': datetime(2025, 10, 22, 17, 0, 0)
        }

    def test_load_data_success(self, loader, test_time_range):
        """
        测试用例1.1：正常数据加载
        
        验证DataLoader能正确加载pump_frequency数据
        """
        # 执行加载
        df = loader.load_data(
            station_id=1,
            device_id=1,
            start_time=test_time_range['start_time'],
            end_time=test_time_range['end_time']
        )

        # 断言：返回DataFrame
        assert isinstance(df, pd.DataFrame)
        
        # 断言：包含必需列
        assert set(df.columns) >= {'ts_bucket', 'device_id', 'pump_frequency', 'running'}
        
        # 断言：数据行数 > 0
        assert len(df) > 0
        
        # 断言：pump_frequency值在合理范围（0-60 Hz）
        assert df['pump_frequency'].between(0, 60).all()
        
        # 断言：无空值
        assert df['pump_frequency'].notna().all()

    def test_load_data_empty(self, loader):
        """
        测试用例1.2：空数据处理
        
        验证DataLoader能正确处理无数据情况
        """
        # 使用不存在的设备ID
        df = loader.load_data(
            station_id=1,
            device_id=999,
            start_time=datetime(2025, 10, 22, 8, 0, 0),
            end_time=datetime(2025, 10, 22, 9, 0, 0)
        )

        # 断言：返回空DataFrame
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_load_data_device_type_filter(self, loader, test_time_range):
        """
        测试用例1.3：设备类型过滤
        
        验证DataLoader只加载type='pump'的设备数据
        """
        # 设备1-6是pump类型
        df_pump = loader.load_data(
            station_id=1,
            device_id=1,
            start_time=test_time_range['start_time'],
            end_time=test_time_range['end_time']
        )

        # 断言：pump设备有数据
        assert len(df_pump) > 0

        # 设备7是main_pipeline类型（如果存在）
        df_pipeline = loader.load_data(
            station_id=1,
            device_id=7,
            start_time=test_time_range['start_time'],
            end_time=test_time_range['end_time']
        )

        # 断言：非pump设备返回空DataFrame
        assert len(df_pipeline) == 0

    def test_load_data_time_range(self, loader):
        """
        测试用例1.4：时间范围过滤

        验证DataLoader能正确过滤时间范围
        """
        # 加载1小时数据
        df_1h = loader.load_data(
            station_id=1,
            device_id=1,
            start_time=datetime(2025, 10, 22, 16, 0, 0),
            end_time=datetime(2025, 10, 22, 17, 0, 0)
        )

        # 加载2小时数据
        df_2h = loader.load_data(
            station_id=1,
            device_id=1,
            start_time=datetime(2025, 10, 22, 16, 0, 0),
            end_time=datetime(2025, 10, 22, 18, 0, 0)
        )

        # 断言：2小时数据量应该大于1小时
        assert len(df_2h) > len(df_1h)

    def test_load_data_running_status(self, loader, test_time_range):
        """
        测试用例1.5：运行状态加载
        
        验证DataLoader能正确加载运行状态
        """
        df = loader.load_data(
            station_id=1,
            device_id=1,
            start_time=test_time_range['start_time'],
            end_time=test_time_range['end_time']
        )

        # 断言：包含running列
        assert 'running' in df.columns
        
        # 断言：running值为0或1
        assert df['running'].isin([0, 1]).all()

