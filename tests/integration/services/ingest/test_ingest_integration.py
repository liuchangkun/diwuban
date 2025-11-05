"""
集成测试：app/services/ingest/ 模块集成

测试ingest模块的组件协作：
- create_staging + merge_service 集成
- merge_service辅助函数集成
- 数据流集成
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timedelta

from app.services.ingest.create_staging import create_staging
from app.services.ingest.merge_service import _parse_granularity, _split_window
from app.core.config.loader_new import Settings


class TestCreateStagingMergeIntegration:
    """create_staging + merge_service 集成测试"""

    @patch('app.services.ingest.create_staging.get_conn')
    @patch('app.services.ingest.create_staging.create_staging_if_not_exists')
    def test_create_staging_prepares_for_merge(self, mock_create_fn, mock_get_conn):
        """场景1: create_staging为merge准备staging表"""
        # Mock数据库连接
        mock_conn = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        # Mock Settings
        settings = Mock(spec=Settings)
        
        # 执行create_staging
        create_staging(settings)
        
        # 验证staging表被创建
        mock_create_fn.assert_called_once_with(mock_conn)

    def test_parse_granularity_for_merge_window(self):
        """场景2: _parse_granularity为merge_window提供粒度"""
        # 测试不同粒度
        assert _parse_granularity("30m") == 1800
        assert _parse_granularity("1h") == 3600
        assert _parse_granularity("2h") == 7200
        
        # 验证粒度可用于split_window
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 1, 2, 0, 0)
        
        # 使用30分钟粒度
        segments_30m = _split_window(start, end, _parse_granularity("30m"))
        assert len(segments_30m) == 4
        
        # 使用1小时粒度
        segments_1h = _split_window(start, end, _parse_granularity("1h"))
        assert len(segments_1h) == 2


class TestMergeServiceHelperIntegration:
    """merge_service辅助函数集成测试"""

    def test_parse_granularity_and_split_window_integration(self):
        """场景3: _parse_granularity和_split_window协作"""
        # 解析粒度
        granularity_30m = _parse_granularity("30m")
        granularity_1h = _parse_granularity("1h")
        
        # 使用粒度切分窗口
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 1, 3, 0, 0)
        
        segments_30m = _split_window(start, end, granularity_30m)
        segments_1h = _split_window(start, end, granularity_1h)
        
        # 验证切分结果
        assert len(segments_30m) == 6  # 3小时 / 30分钟 = 6段
        assert len(segments_1h) == 3   # 3小时 / 1小时 = 3段

    def test_split_window_handles_various_granularities(self):
        """场景4: _split_window处理各种粒度"""
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 1, 6, 0, 0)
        
        # 测试不同粒度
        test_cases = [
            ("15m", 900, 24),   # 6小时 / 15分钟 = 24段
            ("30m", 1800, 12),  # 6小时 / 30分钟 = 12段
            ("1h", 3600, 6),    # 6小时 / 1小时 = 6段
            ("2h", 7200, 3),    # 6小时 / 2小时 = 3段
        ]
        
        for spec, expected_seconds, expected_segments in test_cases:
            granularity = _parse_granularity(spec)
            assert granularity == expected_seconds
            
            segments = _split_window(start, end, granularity)
            assert len(segments) == expected_segments


class TestDataFlowIntegration:
    """数据流集成测试"""

    def test_time_window_continuity(self):
        """场景5: 时间窗口连续性"""
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 1, 12, 0, 0)
        
        # 使用1小时粒度
        segments = _split_window(start, end, 3600)
        
        # 验证连续性
        for i in range(len(segments) - 1):
            assert segments[i][1] == segments[i + 1][0]

    def test_time_window_coverage(self):
        """场景6: 时间窗口完整覆盖"""
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 1, 12, 0, 0)
        
        # 使用1小时粒度
        segments = _split_window(start, end, 3600)
        
        # 验证覆盖
        assert segments[0][0] == start
        assert segments[-1][1] == end

    def test_partial_last_segment_handling(self):
        """场景7: 处理不完整的最后一段"""
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 1, 2, 30, 0)  # 2.5小时
        
        # 使用1小时粒度
        segments = _split_window(start, end, 3600)
        
        # 验证最后一段
        assert len(segments) == 3
        assert segments[-1][1] == end
        assert (segments[-1][1] - segments[-1][0]).total_seconds() == 1800  # 30分钟


class TestErrorHandlingIntegration:
    """错误处理集成测试"""

    @patch('app.services.ingest.create_staging.get_conn')
    @patch('app.services.ingest.create_staging.create_staging_if_not_exists')
    def test_create_staging_error_propagation(self, mock_create_fn, mock_get_conn):
        """场景8: create_staging错误传播"""
        # Mock数据库连接失败
        mock_get_conn.side_effect = Exception("Database connection failed")
        
        # Mock Settings
        settings = Mock(spec=Settings)
        
        # 验证异常被传播
        with pytest.raises(Exception) as exc_info:
            create_staging(settings)
        
        assert "Database connection failed" in str(exc_info.value)

    def test_parse_granularity_invalid_input_fallback(self):
        """场景9: _parse_granularity无效输入回退"""
        # 测试无效输入
        assert _parse_granularity("invalid") == 3600  # 回退到1小时
        assert _parse_granularity("") == 3600
        assert _parse_granularity(None) == 3600

    def test_split_window_empty_window(self):
        """场景10: _split_window空窗口"""
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 1, 0, 0, 0)
        
        # 空窗口
        segments = _split_window(start, end, 3600)
        
        # 验证返回空列表
        assert len(segments) == 0
        assert segments == []


class TestBoundaryConditions:
    """边界条件集成测试"""

    def test_very_small_granularity(self):
        """场景11: 非常小的粒度"""
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 1, 0, 5, 0)
        
        # 使用1分钟粒度（最小值）
        segments = _split_window(start, end, 60)
        
        # 验证切分
        assert len(segments) == 5

    def test_very_large_window(self):
        """场景12: 非常大的时间窗口"""
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 2, 0, 0, 0)  # 24小时
        
        # 使用1小时粒度
        segments = _split_window(start, end, 3600)
        
        # 验证切分
        assert len(segments) == 24

    def test_single_segment_window(self):
        """场景13: 单段窗口"""
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 1, 0, 30, 0)
        
        # 使用1小时粒度（窗口小于粒度）
        segments = _split_window(start, end, 3600)
        
        # 验证只有一段
        assert len(segments) == 1
        assert segments[0] == (start, end)


class TestPerformanceConsiderations:
    """性能考虑集成测试"""

    def test_large_number_of_segments(self):
        """场景14: 大量段"""
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 8, 0, 0, 0)  # 7天
        
        # 使用1小时粒度
        segments = _split_window(start, end, 3600)
        
        # 验证段数
        assert len(segments) == 168  # 7天 * 24小时

    def test_granularity_parsing_performance(self):
        """场景15: 粒度解析性能"""
        # 多次解析相同粒度
        for _ in range(100):
            assert _parse_granularity("30m") == 1800
            assert _parse_granularity("1h") == 3600


class TestEdgeCases:
    """边缘情况集成测试"""

    def test_midnight_crossing(self):
        """场景16: 跨越午夜"""
        start = datetime(2025, 1, 1, 23, 0, 0)
        end = datetime(2025, 1, 2, 1, 0, 0)
        
        # 使用1小时粒度
        segments = _split_window(start, end, 3600)
        
        # 验证跨越午夜
        assert len(segments) == 2
        assert segments[0][0].day == 1
        assert segments[1][1].day == 2

    def test_month_crossing(self):
        """场景17: 跨越月份"""
        start = datetime(2025, 1, 31, 23, 0, 0)
        end = datetime(2025, 2, 1, 1, 0, 0)
        
        # 使用1小时粒度
        segments = _split_window(start, end, 3600)
        
        # 验证跨越月份
        assert len(segments) == 2
        assert segments[0][0].month == 1
        assert segments[1][1].month == 2

    def test_year_crossing(self):
        """场景18: 跨越年份"""
        start = datetime(2024, 12, 31, 23, 0, 0)
        end = datetime(2025, 1, 1, 1, 0, 0)
        
        # 使用1小时粒度
        segments = _split_window(start, end, 3600)
        
        # 验证跨越年份
        assert len(segments) == 2
        assert segments[0][0].year == 2024
        assert segments[1][1].year == 2025


class TestConfigurationIntegration:
    """配置集成测试"""

    def test_granularity_configuration_variations(self):
        """场景19: 粒度配置变化"""
        # 测试各种粒度配置
        configs = [
            ("15m", 900),
            ("30m", 1800),
            ("45m", 2700),
            ("1h", 3600),
            ("2h", 7200),
            ("3h", 10800),
            ("6h", 21600),
            ("12h", 43200),
            ("24h", 86400),
        ]
        
        for spec, expected_seconds in configs:
            assert _parse_granularity(spec) == expected_seconds

    @patch('app.services.ingest.create_staging.get_conn')
    @patch('app.services.ingest.create_staging.create_staging_if_not_exists')
    @patch('app.services.ingest.create_staging._act')
    def test_create_staging_with_logging(self, mock_logger, mock_create_fn, mock_get_conn):
        """场景20: create_staging日志记录"""
        # Mock数据库连接
        mock_conn = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        # Mock Settings
        settings = Mock(spec=Settings)
        
        # 执行
        create_staging(settings)
        
        # 验证日志记录
        assert mock_logger.info.call_count >= 2  # 至少有开始和完成日志

