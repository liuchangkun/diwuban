"""
测试性能监控器 (PerformanceMonitor)

测试场景:
1. 正常流程测试 (4个场景)
2. 边界条件测试 (4个场景)
3. 异常情况测试 (3个场景)
4. 性能测试 (2个场景)

总计: 13个测试场景
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from app.services.calculation.performance_monitor import PerformanceMonitor


class TestPerformanceMonitor:
    """性能监控器测试类"""

    # =====================================================
    # 正常流程测试 (4个场景)
    # =====================================================

    def test_initialization(self):
        """场景1: 正常初始化"""
        monitor = PerformanceMonitor(
            station_id=1,
            device_id=101,
            run_id=1001,
            history_size=20
        )
        
        # 验证初始化
        assert monitor.station_id == 1
        assert monitor.device_id == 101
        assert monitor.run_id == 1001
        assert monitor.history_size == 20
        assert len(monitor.history) == 0
        assert monitor.current_batch is None

    def test_start_and_end_batch(self):
        """场景2: 开始和结束批次监控"""
        monitor = PerformanceMonitor(station_id=1, device_id=101)
        
        # 开始批次
        batch_context = monitor.start_batch(batch_number=1, time_window_minutes=60)
        
        # 验证批次上下文
        assert batch_context['batch_number'] == 1
        assert batch_context['time_window_minutes'] == 60
        assert 'start_time' in batch_context
        assert 'start_memory_mb' in batch_context
        
        # 模拟一些处理时间
        time.sleep(0.1)
        
        # 结束批次
        metrics = monitor.end_batch(batch_size=10000, data_points=5000)
        
        # 验证性能指标
        assert metrics['batch_number'] == 1
        assert metrics['time_window_minutes'] == 60
        assert metrics['batch_size'] == 10000
        assert metrics['data_points'] == 5000
        assert metrics['duration_ms'] >= 100  # 至少100ms
        assert metrics['throughput'] > 0
        assert 'memory_mb' in metrics
        assert 'timestamp' in metrics

    def test_get_memory_usage(self):
        """场景3: 获取内存使用"""
        monitor = PerformanceMonitor(station_id=1, device_id=101)
        
        memory_mb = monitor.get_memory_usage()
        
        # 验证内存值合理（应该大于0）
        assert memory_mb >= 0
        # 通常Python进程至少使用几MB内存
        if monitor.process is not None:
            assert memory_mb > 0

    def test_history_accumulation(self):
        """场景4: 历史记录累积"""
        monitor = PerformanceMonitor(station_id=1, device_id=101, history_size=5)
        
        # 执行多个批次
        for i in range(7):
            monitor.start_batch(batch_number=i+1, time_window_minutes=60)
            time.sleep(0.01)
            monitor.end_batch(batch_size=10000, data_points=5000)
        
        # 验证历史记录限制
        assert len(monitor.history) == 5  # 最多保留5条
        assert monitor.history[0]['batch_number'] == 3  # 最早的是第3批
        assert monitor.history[-1]['batch_number'] == 7  # 最新的是第7批

    # =====================================================
    # 边界条件测试 (4个场景)
    # =====================================================

    def test_get_statistics_empty_history(self):
        """场景5: 空历史记录的统计信息"""
        monitor = PerformanceMonitor(station_id=1, device_id=101)
        
        stats = monitor.get_statistics()
        
        # 验证空统计
        assert stats['count'] == 0
        assert stats['avg_duration_ms'] == 0
        assert stats['avg_throughput'] == 0
        assert stats['avg_memory_mb'] == 0
        assert stats['trend'] == 'stable'

    def test_get_statistics_with_data(self):
        """场景6: 有数据的统计信息"""
        monitor = PerformanceMonitor(station_id=1, device_id=101)
        
        # 执行多个批次
        for i in range(10):
            monitor.start_batch(batch_number=i+1, time_window_minutes=60)
            time.sleep(0.01)
            monitor.end_batch(batch_size=10000, data_points=5000)
        
        stats = monitor.get_statistics(window=5)
        
        # 验证统计信息
        assert stats['count'] == 5
        assert stats['avg_duration_ms'] > 0
        assert stats['avg_throughput'] > 0
        assert stats['avg_memory_mb'] >= 0
        assert stats['trend'] in ['stable', 'improving', 'degrading']

    def test_get_recent_metrics(self):
        """场景7: 获取最近的性能指标"""
        monitor = PerformanceMonitor(station_id=1, device_id=101)
        
        # 执行多个批次
        for i in range(5):
            monitor.start_batch(batch_number=i+1, time_window_minutes=60)
            time.sleep(0.01)
            monitor.end_batch(batch_size=10000, data_points=5000)
        
        recent = monitor.get_recent_metrics(limit=3)
        
        # 验证最近3条记录
        assert len(recent) == 3
        assert recent[0]['batch_number'] == 3
        assert recent[-1]['batch_number'] == 5

    def test_clear_history(self):
        """场景8: 清空历史记录"""
        monitor = PerformanceMonitor(station_id=1, device_id=101)
        
        # 执行几个批次
        for i in range(3):
            monitor.start_batch(batch_number=i+1, time_window_minutes=60)
            time.sleep(0.01)
            monitor.end_batch(batch_size=10000, data_points=5000)
        
        assert len(monitor.history) == 3
        
        # 清空历史
        monitor.clear_history()
        
        assert len(monitor.history) == 0

    # =====================================================
    # 异常情况测试 (3个场景)
    # =====================================================

    def test_end_batch_without_start(self):
        """场景9: 未调用start_batch就调用end_batch"""
        monitor = PerformanceMonitor(station_id=1, device_id=101)
        
        with pytest.raises(ValueError) as exc_info:
            monitor.end_batch(batch_size=10000, data_points=5000)
        
        assert "未调用start_batch" in str(exc_info.value)

    def test_memory_usage_when_process_unavailable(self):
        """场景10: 进程对象不可用时的内存使用"""
        monitor = PerformanceMonitor(station_id=1, device_id=101)
        
        # 模拟进程对象不可用
        monitor.process = None
        
        memory_mb = monitor.get_memory_usage()
        
        # 验证返回0而不是抛出异常
        assert memory_mb == 0.0

    def test_save_to_db_with_connection_error(self):
        """场景11: 数据库连接失败时保存性能指标"""
        monitor = PerformanceMonitor(station_id=1, device_id=101)
        
        # Mock数据库连接失败
        with patch('app.services.calculation.performance_monitor.get_connection') as mock_conn:
            from app.core.exceptions import DatabaseError
            mock_conn.side_effect = DatabaseError("连接失败")
            
            # 准备性能指标
            metrics = {
                'batch_number': 1,
                'time_window_minutes': 60,
                'batch_size': 10000,
                'data_points': 5000,
                'duration_ms': 1000,
                'memory_mb': 100,
                'throughput': 5000,
                'adjustment_type': 'none',
                'adjustment_reason': None,
                'old_value': None,
                'new_value': None
            }
            
            # 验证不抛出异常（只记录日志）
            monitor.save_to_db(metrics)  # 应该不抛出异常

    # =====================================================
    # 性能测试 (2个场景)
    # =====================================================

    def test_trend_detection_degrading(self):
        """场景12: 性能退化趋势检测"""
        monitor = PerformanceMonitor(station_id=1, device_id=101)
        
        # 模拟性能逐渐退化（处理时间逐渐增加）
        for i in range(10):
            monitor.start_batch(batch_number=i+1, time_window_minutes=60)
            # 后半部分睡眠时间更长
            sleep_time = 0.01 if i < 5 else 0.03
            time.sleep(sleep_time)
            monitor.end_batch(batch_size=10000, data_points=5000)
        
        stats = monitor.get_statistics(window=10)
        
        # 验证检测到退化趋势
        assert stats['trend'] == 'degrading'

    def test_trend_detection_improving(self):
        """场景13: 性能改善趋势检测"""
        monitor = PerformanceMonitor(station_id=1, device_id=101)
        
        # 模拟性能逐渐改善（处理时间逐渐减少）
        for i in range(10):
            monitor.start_batch(batch_number=i+1, time_window_minutes=60)
            # 后半部分睡眠时间更短
            sleep_time = 0.03 if i < 5 else 0.01
            time.sleep(sleep_time)
            monitor.end_batch(batch_size=10000, data_points=5000)
        
        stats = monitor.get_statistics(window=10)
        
        # 验证检测到改善趋势
        assert stats['trend'] == 'improving'


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

