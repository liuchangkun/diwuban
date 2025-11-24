"""
DataWriter 单元测试

测试范围：
- 批量写入逻辑
- ON CONFLICT 处理
- 自适应批量大小
- 性能统计
"""

import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import MagicMock, patch, call

from app.services.calculation.shared.data_writer import DataWriter, WriteRecord


class TestDataWriter:
    """DataWriter 单元测试"""

    @pytest.fixture
    def data_writer(self, mock_db_connection):
        """创建 DataWriter 实例"""
        with patch('app.services.calculation.shared.data_writer.get_connection', return_value=mock_db_connection):
            writer = DataWriter()
            writer._instance = None  # 重置单例
            return DataWriter()

    def test_write_single_batch(self, data_writer, mock_db_connection):
        """测试：单批次写入"""
        # 准备数据（小于批量大小）
        records = [
            WriteRecord(
                station_id=1,
                device_id=105,
                metric_key='pump_flow_rate',
                ts_bucket=datetime(2025, 1, 1, 0, 0, 0),
                value=50.0,
                quality_code=0
            )
            for _ in range(100)
        ]

        # 执行写入
        data_writer.write(records)

        # 断言：调用了一次 executemany
        cursor = mock_db_connection.cursor.return_value.__enter__.return_value
        assert cursor.executemany.called

    def test_write_multiple_batches(self, data_writer, mock_db_connection):
        """测试：多批次写入"""
        # 准备数据（大于批量大小）
        records = [
            WriteRecord(
                station_id=1,
                device_id=105,
                metric_key='pump_flow_rate',
                ts_bucket=datetime(2025, 1, 1, 0, 0, i),
                value=50.0 + i,
                quality_code=0
            )
            for i in range(2500)  # 超过默认批量大小 1000
        ]

        # 执行写入
        data_writer.write(records)

        # 断言：调用了多次 executemany（至少3次）
        cursor = mock_db_connection.cursor.return_value.__enter__.return_value
        assert cursor.executemany.call_count >= 3

    def test_get_stats(self, data_writer, mock_db_connection):
        """测试：获取写入统计"""
        # 准备数据
        records = [
            WriteRecord(
                station_id=1,
                device_id=105,
                metric_key='pump_flow_rate',
                ts_bucket=datetime(2025, 1, 1, 0, 0, 0),
                value=50.0,
                quality_code=0
            )
            for _ in range(100)
        ]

        # 执行写入
        data_writer.write(records)

        # 获取统计
        stats = data_writer.get_stats()

        # 断言
        assert stats['total_records'] == 100
        assert stats['total_batches'] >= 1
        assert 'total_duration' in stats
        assert 'avg_batch_size' in stats
        assert 'avg_duration' in stats

    def test_write_empty_records(self, data_writer, mock_db_connection):
        """测试：空记录列表"""
        # 准备空数据
        records = []

        # 执行写入
        data_writer.write(records)

        # 断言：不调用 executemany
        cursor = mock_db_connection.cursor.return_value.__enter__.return_value
        assert not cursor.executemany.called

    def test_adaptive_batch_size(self, data_writer):
        """测试：自适应批量大小调整"""
        # 测试：耗时过长，减小批量大小
        new_size = data_writer._adjust_batch_size(current_size=1000, duration_ms=1000)
        assert new_size < 1000

        # 测试：耗时过短，增大批量大小
        new_size = data_writer._adjust_batch_size(current_size=1000, duration_ms=200)
        assert new_size > 1000

        # 测试：耗时适中，保持批量大小
        new_size = data_writer._adjust_batch_size(current_size=1000, duration_ms=500)
        assert new_size == 1000

    def test_get_metric_ids(self, data_writer, mock_db_connection):
        """测试：批量查询 metric_id"""
        # Mock 数据库查询结果
        cursor = mock_db_connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [
            (1, 'pump_flow_rate'),
            (2, 'pump_head')
        ]

        # 执行查询
        metric_keys = ['pump_flow_rate', 'pump_head']
        metric_ids = data_writer._get_metric_ids(metric_keys)

        # 断言
        assert metric_ids == {'pump_flow_rate': 1, 'pump_head': 2}
        assert cursor.execute.called

    def test_write_with_on_conflict(self, data_writer, mock_db_connection):
        """测试：ON CONFLICT 处理"""
        # 准备数据（包含重复记录）
        records = [
            WriteRecord(
                station_id=1,
                device_id=105,
                metric_key='pump_flow_rate',
                ts_bucket=datetime(2025, 1, 1, 0, 0, 0),
                value=50.0,
                quality_code=0
            ),
            WriteRecord(
                station_id=1,
                device_id=105,
                metric_key='pump_flow_rate',
                ts_bucket=datetime(2025, 1, 1, 0, 0, 0),  # 重复时间戳
                value=60.0,  # 不同值
                quality_code=0
            )
        ]

        # 执行写入
        data_writer.write(records)

        # 断言：调用了 executemany，SQL 包含 ON CONFLICT
        cursor = mock_db_connection.cursor.return_value.__enter__.return_value
        assert cursor.executemany.called
        sql = cursor.executemany.call_args[0][0]
        assert 'ON CONFLICT' in sql
        assert 'DO UPDATE SET' in sql

    def test_singleton_pattern(self):
        """测试：单例模式"""
        # 创建两个实例
        writer1 = DataWriter()
        writer2 = DataWriter()

        # 断言：应该是同一个实例
        assert writer1 is writer2

