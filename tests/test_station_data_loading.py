"""
测试泵站级数据加载功能 (load_station_data)

测试场景:
1. 正常流程测试 (5个场景)
2. 边界条件测试 (5个场景)
3. 异常情况测试 (3个场景)
4. 数据缺失测试 (2个场景)

总计: 15个测试场景
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from app.services.calculation.orchestrator import CalculationOrchestrator


class TestStationDataLoading:
    """泵站级数据加载测试类"""

    @pytest.fixture
    def orchestrator(self):
        """创建编排器实例"""
        # Mock所有依赖组件，避免数据库初始化
        with patch('app.services.calculation.dependency_analyzer.get_connection'):
            with patch('app.services.calculation.orchestrator.DependencyAnalyzer'):
                with patch('app.services.calculation.orchestrator.MethodSelector'):
                    with patch('app.services.calculation.orchestrator.PhysicsValidator'):
                        with patch('app.services.calculation.orchestrator.PerformanceMonitor'):
                            with patch('app.services.calculation.orchestrator.AdaptiveBatchManager'):
                                return CalculationOrchestrator()

    # =====================================================
    # 正常流程测试 (5个场景)
    # =====================================================

    def test_load_single_device_single_metric(self, orchestrator):
        """场景1: 加载单设备单指标数据"""
        with patch('app.services.calculation.orchestrator.get_connection') as mock_conn:
            # Mock数据库连接
            mock_cursor = MagicMock()
            mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
            
            # Mock查询结果
            # 查询1: 设备列表
            mock_cursor.fetchall.side_effect = [
                [(1,)],  # device_ids
                # 查询2: 时间戳
                [(datetime(2025, 1, 1, 0, 0, 0),), (datetime(2025, 1, 1, 0, 0, 1),)],
                # 查询3: 数据
                [
                    (datetime(2025, 1, 1, 0, 0, 0), 101, 10.5),
                    (datetime(2025, 1, 1, 0, 0, 1), 101, 11.2)
                ]
            ]
            
            # Mock metric_mapper
            with patch('app.services.calculation.orchestrator.metric_mapper') as mock_mapper:
                mock_mapper.keys_to_ids.return_value = [101]
                mock_mapper.key_to_id.return_value = 101
                
                # 执行测试
                station_data, timestamps = orchestrator.load_station_data(
                    station_id=1,
                    start_time='2025-01-01 00:00:00',
                    end_time='2025-01-01 00:01:00',
                    metric_keys=['pump_flow_rate']
                )
                
                # 验证结果
                assert len(station_data) == 1
                assert 1 in station_data
                assert 'pump_flow_rate' in station_data[1]
                assert len(station_data[1]['pump_flow_rate']) == 2
                assert station_data[1]['pump_flow_rate'][0] == 10.5
                assert station_data[1]['pump_flow_rate'][1] == 11.2
                assert len(timestamps) == 2

    def test_load_multiple_devices_multiple_metrics(self, orchestrator):
        """场景2: 加载多设备多指标数据"""
        with patch('app.services.calculation.orchestrator.get_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
            
            # Mock查询结果
            mock_cursor.fetchall.side_effect = [
                [(1,), (2,)],  # 2个设备
                [(datetime(2025, 1, 1, 0, 0, 0),)],  # 1个时间点
                # 设备1数据
                [
                    (datetime(2025, 1, 1, 0, 0, 0), 101, 10.5),
                    (datetime(2025, 1, 1, 0, 0, 0), 102, 50.0)
                ],
                # 设备2数据
                [
                    (datetime(2025, 1, 1, 0, 0, 0), 101, 12.3),
                    (datetime(2025, 1, 1, 0, 0, 0), 102, 55.0)
                ]
            ]
            
            with patch('app.services.calculation.orchestrator.metric_mapper') as mock_mapper:
                mock_mapper.keys_to_ids.return_value = [101, 102]
                mock_mapper.key_to_id.side_effect = lambda k: 101 if k == 'pump_flow_rate' else 102
                
                station_data, timestamps = orchestrator.load_station_data(
                    station_id=1,
                    start_time='2025-01-01 00:00:00',
                    end_time='2025-01-01 00:01:00',
                    metric_keys=['pump_flow_rate', 'pump_head']
                )
                
                # 验证结果
                assert len(station_data) == 2
                assert 1 in station_data and 2 in station_data
                assert 'pump_flow_rate' in station_data[1]
                assert 'pump_head' in station_data[1]
                assert station_data[1]['pump_flow_rate'][0] == 10.5
                assert station_data[1]['pump_head'][0] == 50.0

    def test_load_with_running_filter(self, orchestrator):
        """场景3: 加载数据并过滤停机状态"""
        with patch('app.services.calculation.orchestrator.get_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
            
            mock_cursor.fetchall.side_effect = [
                [(1,)],
                [(datetime(2025, 1, 1, 0, 0, 0),)],  # 只有运行时的时间点
                [(datetime(2025, 1, 1, 0, 0, 0), 101, 10.5)]
            ]
            
            with patch('app.services.calculation.orchestrator.metric_mapper') as mock_mapper:
                mock_mapper.keys_to_ids.return_value = [101]
                mock_mapper.key_to_id.return_value = 101
                
                station_data, timestamps = orchestrator.load_station_data(
                    station_id=1,
                    start_time='2025-01-01 00:00:00',
                    end_time='2025-01-01 00:01:00',
                    metric_keys=['pump_flow_rate'],
                    filter_running=True
                )
                
                # 验证SQL查询包含running过滤
                calls = mock_cursor.execute.call_args_list
                assert any('dr.running = 1' in str(call) for call in calls)
                assert len(timestamps) == 1

    def test_load_with_quality_filter(self, orchestrator):
        """场景4: 加载数据并过滤异常质量数据"""
        with patch('app.services.calculation.orchestrator.get_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
            
            mock_cursor.fetchall.side_effect = [
                [(1,)],
                [(datetime(2025, 1, 1, 0, 0, 0),)],
                [(datetime(2025, 1, 1, 0, 0, 0), 101, 10.5)]
            ]
            
            with patch('app.services.calculation.orchestrator.metric_mapper') as mock_mapper:
                mock_mapper.keys_to_ids.return_value = [101]
                mock_mapper.key_to_id.return_value = 101
                
                station_data, timestamps = orchestrator.load_station_data(
                    station_id=1,
                    start_time='2025-01-01 00:00:00',
                    end_time='2025-01-01 00:01:00',
                    metric_keys=['pump_flow_rate'],
                    filter_quality=True
                )
                
                # 验证SQL查询包含quality过滤
                calls = mock_cursor.execute.call_args_list
                assert any('quality_status = 0' in str(call) for call in calls)

    def test_load_with_time_alignment(self, orchestrator):
        """场景5: 数据时间对齐到基准时间序列"""
        with patch('app.services.calculation.orchestrator.get_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
            
            # 基准时间序列有3个点，但设备数据只有2个点
            base_times = [
                datetime(2025, 1, 1, 0, 0, 0),
                datetime(2025, 1, 1, 0, 0, 1),
                datetime(2025, 1, 1, 0, 0, 2)
            ]
            
            mock_cursor.fetchall.side_effect = [
                [(1,)],
                [(t,) for t in base_times],
                [
                    (datetime(2025, 1, 1, 0, 0, 0), 101, 10.5),
                    (datetime(2025, 1, 1, 0, 0, 2), 101, 12.5)  # 缺少中间时间点
                ]
            ]
            
            with patch('app.services.calculation.orchestrator.metric_mapper') as mock_mapper:
                mock_mapper.keys_to_ids.return_value = [101]
                mock_mapper.key_to_id.return_value = 101
                
                station_data, timestamps = orchestrator.load_station_data(
                    station_id=1,
                    start_time='2025-01-01 00:00:00',
                    end_time='2025-01-01 00:01:00',
                    metric_keys=['pump_flow_rate']
                )
                
                # 验证时间对齐
                assert len(station_data[1]['pump_flow_rate']) == 3
                assert station_data[1]['pump_flow_rate'][0] == 10.5
                assert np.isnan(station_data[1]['pump_flow_rate'][1])  # 缺失点为NaN
                assert station_data[1]['pump_flow_rate'][2] == 12.5

    # =====================================================
    # 边界条件测试 (5个场景)
    # =====================================================

    def test_load_empty_time_range(self, orchestrator):
        """场景6: 空时间范围（开始时间=结束时间）"""
        with patch('app.services.calculation.orchestrator.get_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
            
            mock_cursor.fetchall.side_effect = [
                [],  # 没有设备
            ]
            
            with patch('app.services.calculation.orchestrator.metric_mapper') as mock_mapper:
                mock_mapper.keys_to_ids.return_value = [101]
                
                station_data, timestamps = orchestrator.load_station_data(
                    station_id=1,
                    start_time='2025-01-01 00:00:00',
                    end_time='2025-01-01 00:00:00',
                    metric_keys=['pump_flow_rate']
                )
                
                assert len(station_data) == 0
                assert len(timestamps) == 0

    def test_load_single_timestamp(self, orchestrator):
        """场景7: 单个时间点数据"""
        with patch('app.services.calculation.orchestrator.get_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
            
            mock_cursor.fetchall.side_effect = [
                [(1,)],
                [(datetime(2025, 1, 1, 0, 0, 0),)],
                [(datetime(2025, 1, 1, 0, 0, 0), 101, 10.5)]
            ]
            
            with patch('app.services.calculation.orchestrator.metric_mapper') as mock_mapper:
                mock_mapper.keys_to_ids.return_value = [101]
                mock_mapper.key_to_id.return_value = 101
                
                station_data, timestamps = orchestrator.load_station_data(
                    station_id=1,
                    start_time='2025-01-01 00:00:00',
                    end_time='2025-01-01 00:00:01',
                    metric_keys=['pump_flow_rate']
                )
                
                assert len(timestamps) == 1
                assert len(station_data[1]['pump_flow_rate']) == 1

    def test_load_large_batch(self, orchestrator):
        """场景8: 大批量数据（1000个时间点）"""
        with patch('app.services.calculation.orchestrator.get_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
            
            # 生成1000个时间点
            base_time = datetime(2025, 1, 1, 0, 0, 0)
            timestamps_data = [(base_time + timedelta(seconds=i),) for i in range(1000)]
            values_data = [(base_time + timedelta(seconds=i), 101, float(i)) for i in range(1000)]
            
            mock_cursor.fetchall.side_effect = [
                [(1,)],
                timestamps_data,
                values_data
            ]
            
            with patch('app.services.calculation.orchestrator.metric_mapper') as mock_mapper:
                mock_mapper.keys_to_ids.return_value = [101]
                mock_mapper.key_to_id.return_value = 101
                
                station_data, timestamps = orchestrator.load_station_data(
                    station_id=1,
                    start_time='2025-01-01 00:00:00',
                    end_time='2025-01-01 00:20:00',
                    metric_keys=['pump_flow_rate']
                )
                
                assert len(timestamps) == 1000
                assert len(station_data[1]['pump_flow_rate']) == 1000

    def test_load_many_devices(self, orchestrator):
        """场景9: 多设备数据（10个设备）"""
        with patch('app.services.calculation.orchestrator.get_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
            
            # 10个设备
            device_ids = [(i,) for i in range(1, 11)]
            timestamps_data = [(datetime(2025, 1, 1, 0, 0, 0),)]
            
            # 为每个设备准备数据
            device_data_list = [
                [(datetime(2025, 1, 1, 0, 0, 0), 101, float(i))]
                for i in range(1, 11)
            ]
            
            mock_cursor.fetchall.side_effect = [device_ids, timestamps_data] + device_data_list
            
            with patch('app.services.calculation.orchestrator.metric_mapper') as mock_mapper:
                mock_mapper.keys_to_ids.return_value = [101]
                mock_mapper.key_to_id.return_value = 101
                
                station_data, timestamps = orchestrator.load_station_data(
                    station_id=1,
                    start_time='2025-01-01 00:00:00',
                    end_time='2025-01-01 00:01:00',
                    metric_keys=['pump_flow_rate']
                )
                
                assert len(station_data) == 10
                for i in range(1, 11):
                    assert i in station_data

    def test_load_sparse_data(self, orchestrator):
        """场景10: 稀疏数据（50%缺失率）"""
        with patch('app.services.calculation.orchestrator.get_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
            
            # 10个时间点，但只有5个有数据
            base_time = datetime(2025, 1, 1, 0, 0, 0)
            all_timestamps = [(base_time + timedelta(seconds=i),) for i in range(10)]
            sparse_data = [(base_time + timedelta(seconds=i*2), 101, float(i)) for i in range(5)]
            
            mock_cursor.fetchall.side_effect = [
                [(1,)],
                all_timestamps,
                sparse_data
            ]
            
            with patch('app.services.calculation.orchestrator.metric_mapper') as mock_mapper:
                mock_mapper.keys_to_ids.return_value = [101]
                mock_mapper.key_to_id.return_value = 101
                
                station_data, timestamps = orchestrator.load_station_data(
                    station_id=1,
                    start_time='2025-01-01 00:00:00',
                    end_time='2025-01-01 00:01:00',
                    metric_keys=['pump_flow_rate']
                )
                
                # 验证稀疏数据
                values = station_data[1]['pump_flow_rate']
                assert len(values) == 10
                nan_count = np.sum(np.isnan(values))
                assert nan_count == 5  # 50%缺失

    # =====================================================
    # 异常情况测试 (3个场景)
    # =====================================================

    def test_load_invalid_metric_keys(self, orchestrator):
        """场景11: 无效的指标键名"""
        with patch('app.services.calculation.orchestrator.metric_mapper') as mock_mapper:
            mock_mapper.keys_to_ids.return_value = []  # 没有有效的metric_id
            
            station_data, timestamps = orchestrator.load_station_data(
                station_id=1,
                start_time='2025-01-01 00:00:00',
                end_time='2025-01-01 00:01:00',
                metric_keys=['invalid_metric']
            )
            
            assert len(station_data) == 0
            assert len(timestamps) == 0

    def test_load_database_connection_error(self, orchestrator):
        """场景12: 数据库连接失败"""
        with patch('app.services.calculation.orchestrator.get_connection') as mock_conn:
            from app.core.exceptions import DatabaseError
            mock_conn.side_effect = DatabaseError("数据库连接失败")

            with pytest.raises(DatabaseError) as exc_info:
                orchestrator.load_station_data(
                    station_id=1,
                    start_time='2025-01-01 00:00:00',
                    end_time='2025-01-01 00:01:00',
                    metric_keys=['pump_flow_rate']
                )

            assert "数据库连接" in str(exc_info.value)

    def test_load_query_timeout(self, orchestrator):
        """场景13: 查询超时"""
        with patch('app.services.calculation.orchestrator.get_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
            mock_cursor.execute.side_effect = Exception("查询超时")
            
            with patch('app.services.calculation.orchestrator.metric_mapper') as mock_mapper:
                mock_mapper.keys_to_ids.return_value = [101]
                
                with pytest.raises(Exception) as exc_info:
                    orchestrator.load_station_data(
                        station_id=1,
                        start_time='2025-01-01 00:00:00',
                        end_time='2025-01-01 00:01:00',
                        metric_keys=['pump_flow_rate']
                    )
                
                assert "查询超时" in str(exc_info.value)

    # =====================================================
    # 数据缺失测试 (2个场景)
    # =====================================================

    def test_load_no_devices_found(self, orchestrator):
        """场景14: 没有找到任何设备"""
        with patch('app.services.calculation.orchestrator.get_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
            
            mock_cursor.fetchall.return_value = []  # 没有设备
            
            with patch('app.services.calculation.orchestrator.metric_mapper') as mock_mapper:
                mock_mapper.keys_to_ids.return_value = [101]
                
                station_data, timestamps = orchestrator.load_station_data(
                    station_id=999,  # 不存在的泵站
                    start_time='2025-01-01 00:00:00',
                    end_time='2025-01-01 00:01:00',
                    metric_keys=['pump_flow_rate']
                )
                
                assert len(station_data) == 0
                assert len(timestamps) == 0

    def test_load_no_timestamps_found(self, orchestrator):
        """场景15: 找到设备但没有时间戳数据"""
        with patch('app.services.calculation.orchestrator.get_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
            
            mock_cursor.fetchall.side_effect = [
                [(1,)],  # 有设备
                []  # 但没有时间戳
            ]
            
            with patch('app.services.calculation.orchestrator.metric_mapper') as mock_mapper:
                mock_mapper.keys_to_ids.return_value = [101]
                
                station_data, timestamps = orchestrator.load_station_data(
                    station_id=1,
                    start_time='2025-01-01 00:00:00',
                    end_time='2025-01-01 00:01:00',
                    metric_keys=['pump_flow_rate']
                )
                
                assert len(station_data) == 0
                assert len(timestamps) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

