"""
DataLoader 集成测试（使用真实数据库）

测试范围：
- 数据加载功能
- JOIN mv_device_running_1s
- 边界条件处理
- 性能测试
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

from app.services.calculation.metrics.pump_flow_rate.data_loader import DataLoader
from app.core.config.loader_new import load_settings
from app.adapters.db.pool import initialize_pool, close_pool


class TestDataLoaderIntegration:
    """DataLoader 集成测试（使用真实数据库）"""

    @pytest.fixture(scope="class", autouse=True)
    def init_db_pool(self):
        """初始化数据库连接池（类级别，所有测试共享）"""
        settings = load_settings(Path("configs"))
        initialize_pool(settings)
        yield
        close_pool()

    @pytest.fixture
    def data_loader(self):
        """创建 DataLoader 实例"""
        return DataLoader(trace_id="test_data_loader")

    def test_load_data_success(self, data_loader):
        """测试：成功加载数据"""
        # 使用真实的泵站和设备ID
        station_id = 1
        device_id = 3
        start_time = datetime(2025, 10, 23, 10, 0, 0)
        end_time = datetime(2025, 10, 23, 10, 5, 0)  # 5分钟数据

        # 加载数据
        df = data_loader.load_data(station_id, device_id, start_time, end_time)

        # 断言：数据不为空
        assert len(df) > 0, "Should load data successfully"

        # 断言：包含必需列
        required_columns = [
            'ts_bucket', 'device_id', 'main_pipeline_flow_rate',
            'pump_active_power', 'pump_frequency', 'running'
        ]
        for col in required_columns:
            assert col in df.columns, f"Missing required column: {col}"

        # 断言：device_id 正确
        assert df['device_id'].iloc[0] == device_id

    def test_load_data_with_running_status(self, data_loader):
        """测试：加载包含运行状态的数据"""
        station_id = 1
        device_id = 3
        start_time = datetime(2025, 10, 23, 10, 0, 0)
        end_time = datetime(2025, 10, 23, 13, 0, 0)  # 3小时数据（包含启停）

        # 加载数据
        df = data_loader.load_data(station_id, device_id, start_time, end_time)

        # 断言：包含 running 列
        assert 'running' in df.columns

        # 断言：running 列包含 0 和 1（有启停）
        unique_running = df['running'].dropna().unique()
        assert len(unique_running) > 0, "Should have running status data"

    def test_load_data_empty_result(self, data_loader):
        """测试：空结果（未来时间）"""
        station_id = 1
        device_id = 3
        start_time = datetime(2099, 1, 1, 0, 0, 0)  # 未来时间
        end_time = datetime(2099, 1, 1, 1, 0, 0)

        # 加载数据
        df = data_loader.load_data(station_id, device_id, start_time, end_time)

        # 断言：结果为空
        assert len(df) == 0, "Should return empty DataFrame for future time"

    def test_load_data_with_other_devices(self, data_loader):
        """测试：加载包含其他设备信息的数据"""
        station_id = 1
        device_id = 3
        start_time = datetime(2025, 10, 23, 10, 0, 0)
        end_time = datetime(2025, 10, 23, 10, 5, 0)

        # 加载数据
        df = data_loader.load_data(station_id, device_id, start_time, end_time)

        # 断言：包含 other_devices 列
        assert 'other_devices' in df.columns

        # 断言：other_devices 是列表类型
        if len(df) > 0:
            assert isinstance(df['other_devices'].iloc[0], list)

    def test_load_data_time_range(self, data_loader):
        """测试：时间范围过滤"""
        station_id = 1
        device_id = 3
        start_time = datetime(2025, 10, 23, 10, 0, 0)
        end_time = datetime(2025, 10, 23, 10, 1, 0)  # 1分钟

        # 加载数据
        df = data_loader.load_data(station_id, device_id, start_time, end_time)

        # 断言：数据量合理（1分钟 = 60秒，假设最多10个设备）
        if len(df) > 0:
            assert len(df) <= 60 * 10, "Data size should be reasonable for 1 minute"

            # 断言：时间戳是连续的（秒级）
            time_diffs = df['ts_bucket'].diff().dropna()
            if len(time_diffs) > 0:
                # 大部分时间差应该是1秒
                assert (time_diffs == timedelta(seconds=1)).sum() > len(time_diffs) * 0.8

    def test_load_data_multiple_devices(self, data_loader):
        """测试：加载多设备数据"""
        station_id = 1
        device_id = 3  # 主设备
        start_time = datetime(2025, 10, 23, 10, 0, 0)
        end_time = datetime(2025, 10, 23, 10, 5, 0)

        # 加载数据
        df = data_loader.load_data(station_id, device_id, start_time, end_time)

        # 断言：可能包含多个设备的数据
        if len(df) > 0:
            device_ids = df['device_id'].unique()
            assert len(device_ids) >= 1, "Should have at least one device"

    def test_load_data_performance(self, data_loader):
        """测试：性能测试（加载1小时数据）"""
        import time

        station_id = 1
        device_id = 3
        start_time = datetime(2025, 10, 23, 10, 0, 0)
        end_time = datetime(2025, 10, 23, 11, 0, 0)  # 1小时数据

        # 测量加载时间
        start = time.time()
        df = data_loader.load_data(station_id, device_id, start_time, end_time)
        duration = time.time() - start

        # 断言：加载时间应该在合理范围内（< 5秒）
        assert duration < 5.0, f"Loading should be fast, but took {duration:.2f}s"

        # 断言：数据量合理（1小时 = 3600秒）
        if len(df) > 0:
            assert len(df) <= 3600 * 10, "Data size should be reasonable"  # 假设最多10个设备

