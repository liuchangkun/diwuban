"""
单元测试：app/services/ingest/merge_service.py 辅助函数

测试_parse_granularity和_split_window函数的各种场景：
- 正常输入
- 边界条件
- 异常输入
"""

import pytest
from datetime import datetime, timedelta

from app.services.ingest.merge_service import _parse_granularity, _split_window


class TestParseGranularity:
    """_parse_granularity函数测试"""

    def test_parse_granularity_minutes(self):
        """场景1: 解析分钟格式"""
        assert _parse_granularity("30m") == 1800  # 30 * 60
        assert _parse_granularity("15m") == 900   # 15 * 60
        assert _parse_granularity("60m") == 3600  # 60 * 60

    def test_parse_granularity_hours(self):
        """场景2: 解析小时格式"""
        assert _parse_granularity("1h") == 3600   # 1 * 3600
        assert _parse_granularity("2h") == 7200   # 2 * 3600
        assert _parse_granularity("24h") == 86400 # 24 * 3600

    def test_parse_granularity_default(self):
        """场景3: 默认值（1h）"""
        assert _parse_granularity("") == 3600
        assert _parse_granularity(None) == 3600
        assert _parse_granularity("invalid") == 3600

    def test_parse_granularity_case_insensitive(self):
        """场景4: 大小写不敏感"""
        assert _parse_granularity("30M") == 1800
        assert _parse_granularity("1H") == 3600
        assert _parse_granularity("2H") == 7200

    def test_parse_granularity_with_whitespace(self):
        """场景5: 处理空白字符"""
        assert _parse_granularity("  30m  ") == 1800
        assert _parse_granularity("  1h  ") == 3600

    def test_parse_granularity_minimum_values(self):
        """场景6: 最小值限制"""
        # 分钟最小60秒
        assert _parse_granularity("0m") == 60
        assert _parse_granularity("1m") == 60
        
        # 小时最小3600秒
        assert _parse_granularity("0h") == 3600


class TestSplitWindow:
    """_split_window函数测试"""

    def test_split_window_single_segment(self):
        """场景7: 单个时间段（窗口小于步长）"""
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 1, 0, 30, 0)
        step_seconds = 3600  # 1小时
        
        result = _split_window(start, end, step_seconds)
        
        assert len(result) == 1
        assert result[0] == (start, end)

    def test_split_window_multiple_segments(self):
        """场景8: 多个时间段（窗口大于步长）"""
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 1, 3, 0, 0)
        step_seconds = 3600  # 1小时
        
        result = _split_window(start, end, step_seconds)
        
        assert len(result) == 3
        assert result[0] == (datetime(2025, 1, 1, 0, 0, 0), datetime(2025, 1, 1, 1, 0, 0))
        assert result[1] == (datetime(2025, 1, 1, 1, 0, 0), datetime(2025, 1, 1, 2, 0, 0))
        assert result[2] == (datetime(2025, 1, 1, 2, 0, 0), datetime(2025, 1, 1, 3, 0, 0))

    def test_split_window_partial_last_segment(self):
        """场景9: 最后一段不完整"""
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 1, 2, 30, 0)
        step_seconds = 3600  # 1小时
        
        result = _split_window(start, end, step_seconds)
        
        assert len(result) == 3
        assert result[0] == (datetime(2025, 1, 1, 0, 0, 0), datetime(2025, 1, 1, 1, 0, 0))
        assert result[1] == (datetime(2025, 1, 1, 1, 0, 0), datetime(2025, 1, 1, 2, 0, 0))
        assert result[2] == (datetime(2025, 1, 1, 2, 0, 0), datetime(2025, 1, 1, 2, 30, 0))

    def test_split_window_empty(self):
        """场景10: 空窗口（start == end）"""
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 1, 0, 0, 0)
        step_seconds = 3600
        
        result = _split_window(start, end, step_seconds)
        
        assert len(result) == 0
        assert result == []

    def test_split_window_30_minute_step(self):
        """场景11: 30分钟步长"""
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 1, 2, 0, 0)
        step_seconds = 1800  # 30分钟
        
        result = _split_window(start, end, step_seconds)
        
        assert len(result) == 4
        assert result[0] == (datetime(2025, 1, 1, 0, 0, 0), datetime(2025, 1, 1, 0, 30, 0))
        assert result[1] == (datetime(2025, 1, 1, 0, 30, 0), datetime(2025, 1, 1, 1, 0, 0))
        assert result[2] == (datetime(2025, 1, 1, 1, 0, 0), datetime(2025, 1, 1, 1, 30, 0))
        assert result[3] == (datetime(2025, 1, 1, 1, 30, 0), datetime(2025, 1, 1, 2, 0, 0))

    def test_split_window_24_hour_window(self):
        """场景12: 24小时窗口，1小时步长"""
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 2, 0, 0, 0)
        step_seconds = 3600  # 1小时
        
        result = _split_window(start, end, step_seconds)
        
        assert len(result) == 24
        assert result[0][0] == start
        assert result[-1][1] == end

    def test_split_window_continuity(self):
        """场景13: 验证时间段连续性"""
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 1, 5, 0, 0)
        step_seconds = 3600
        
        result = _split_window(start, end, step_seconds)
        
        # 验证每个时间段的结束时间等于下一个时间段的开始时间
        for i in range(len(result) - 1):
            assert result[i][1] == result[i + 1][0]

    def test_split_window_coverage(self):
        """场景14: 验证完整覆盖"""
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 1, 5, 0, 0)
        step_seconds = 3600
        
        result = _split_window(start, end, step_seconds)
        
        # 验证第一个时间段的开始时间等于窗口开始时间
        assert result[0][0] == start
        
        # 验证最后一个时间段的结束时间等于窗口结束时间
        assert result[-1][1] == end

    def test_split_window_small_step(self):
        """场景15: 小步长（1分钟）"""
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 1, 0, 5, 0)
        step_seconds = 60  # 1分钟
        
        result = _split_window(start, end, step_seconds)
        
        assert len(result) == 5
        assert result[0] == (datetime(2025, 1, 1, 0, 0, 0), datetime(2025, 1, 1, 0, 1, 0))
        assert result[-1] == (datetime(2025, 1, 1, 0, 4, 0), datetime(2025, 1, 1, 0, 5, 0))

