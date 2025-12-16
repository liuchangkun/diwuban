"""
边界条件测试：app/services/ 模块边界条件

测试各种边界情况：
- 最小值/最大值
- 空输入
- 极端数据量
- 边界时间
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import numpy as np
from datetime import datetime, timedelta

from app.services.calculation.validator import PhysicsValidator
from app.services.calculation.domain import CalculationContext
from app.services.ingest.merge_service import _parse_granularity, _split_window


class TestMinimumValues:
    """最小值边界测试"""

    def test_parse_granularity_minimum_minute(self):
        """场景1: _parse_granularity最小分钟值"""
        # 测试0分钟（应该回退到60秒最小值）
        assert _parse_granularity("0m") == 60
        assert _parse_granularity("1m") == 60

    def test_parse_granularity_minimum_hour(self):
        """场景2: _parse_granularity最小小时值"""
        # 测试0小时（应该回退到3600秒最小值）
        assert _parse_granularity("0h") == 3600

    def test_split_window_minimum_duration(self):
        """场景3: _split_window最小时长"""
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 1, 0, 0, 1)  # 1秒
        
        # 使用1小时粒度
        segments = _split_window(start, end, 3600)
        
        # 验证只有一段
        assert len(segments) == 1
        assert segments[0] == (start, end)

    @patch('app.services.calculation.validator.get_connection')
    @patch('app.services.calculation.validator.CharacteristicCurveManager')
    def test_validator_minimum_range(self, mock_curve_mgr, mock_conn):
        """场景4: 验证器最小范围"""
        # Mock数据库连接
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn_obj = MagicMock()
        mock_conn_obj.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_conn_obj
        
        validator = PhysicsValidator()
        
        # 测试最小范围（0-0）
        values = np.array([0.0])
        mask, errors = validator.validate_range(values, 0.0, 0.0)
        
        # 验证边界值有效
        assert mask[0]


class TestMaximumValues:
    """最大值边界测试"""

    def test_parse_granularity_large_hour(self):
        """场景5: _parse_granularity大小时值"""
        # 测试24小时
        assert _parse_granularity("24h") == 86400

    def test_split_window_large_duration(self):
        """场景6: _split_window大时长"""
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 31, 0, 0, 0)  # 30天
        
        # 使用1小时粒度
        segments = _split_window(start, end, 3600)
        
        # 验证段数
        assert len(segments) == 720  # 30天 * 24小时

    @patch('app.services.calculation.validator.get_connection')
    @patch('app.services.calculation.validator.CharacteristicCurveManager')
    def test_validator_large_range(self, mock_curve_mgr, mock_conn):
        """场景7: 验证器大范围"""
        # Mock数据库连接
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn_obj = MagicMock()
        mock_conn_obj.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_conn_obj
        
        validator = PhysicsValidator()
        
        # 测试大范围（0-1000000）
        values = np.array([500000.0])
        mask, errors = validator.validate_range(values, 0.0, 1000000.0)
        
        # 验证中间值有效
        assert mask[0]


class TestEmptyInputs:
    """空输入边界测试"""

    def test_split_window_zero_duration(self):
        """场景8: _split_window零时长"""
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 1, 0, 0, 0)
        
        # 零时长
        segments = _split_window(start, end, 3600)
        
        # 验证返回空列表
        assert len(segments) == 0
        assert segments == []

    @patch('app.services.calculation.validator.get_connection')
    @patch('app.services.calculation.validator.CharacteristicCurveManager')
    def test_validator_empty_array(self, mock_curve_mgr, mock_conn):
        """场景9: 验证器空数组"""
        # Mock数据库连接
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn_obj = MagicMock()
        mock_conn_obj.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_conn_obj
        
        validator = PhysicsValidator()
        
        # 测试空数组
        values = np.array([])
        mask, errors = validator.validate_range(values, 0.0, 100.0)
        
        # 验证返回空结果
        assert len(mask) == 0
        assert len(errors) == 0


class TestExtremeDataVolumes:
    """极端数据量边界测试"""

    @patch('app.services.calculation.validator.get_connection')
    @patch('app.services.calculation.validator.CharacteristicCurveManager')
    def test_validator_single_value(self, mock_curve_mgr, mock_conn):
        """场景10: 验证器单个值"""
        # Mock数据库连接
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn_obj = MagicMock()
        mock_conn_obj.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_conn_obj
        
        validator = PhysicsValidator()
        
        # 测试单个值
        values = np.array([50.0])
        mask, errors = validator.validate_range(values, 0.0, 100.0)
        
        # 验证单个值有效
        assert len(mask) == 1
        assert mask[0]

    def test_split_window_single_segment(self):
        """场景11: _split_window单段"""
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 1, 0, 30, 0)
        
        # 使用1小时粒度（窗口小于粒度）
        segments = _split_window(start, end, 3600)
        
        # 验证只有一段
        assert len(segments) == 1
        assert segments[0] == (start, end)


class TestBoundaryTimes:
    """边界时间测试"""

    def test_split_window_midnight_boundary(self):
        """场景12: _split_window午夜边界"""
        start = datetime(2025, 1, 1, 23, 30, 0)
        end = datetime(2025, 1, 2, 0, 30, 0)
        
        # 使用1小时粒度
        segments = _split_window(start, end, 3600)
        
        # 验证跨越午夜
        assert len(segments) == 1
        assert segments[0][0].day == 1
        assert segments[0][1].day == 2

    def test_split_window_month_boundary(self):
        """场景13: _split_window月份边界"""
        start = datetime(2025, 1, 31, 23, 0, 0)
        end = datetime(2025, 2, 1, 1, 0, 0)
        
        # 使用1小时粒度
        segments = _split_window(start, end, 3600)
        
        # 验证跨越月份
        assert len(segments) == 2
        assert segments[0][0].month == 1
        assert segments[1][1].month == 2

    def test_split_window_year_boundary(self):
        """场景14: _split_window年份边界"""
        start = datetime(2024, 12, 31, 23, 0, 0)
        end = datetime(2025, 1, 1, 1, 0, 0)
        
        # 使用1小时粒度
        segments = _split_window(start, end, 3600)
        
        # 验证跨越年份
        assert len(segments) == 2
        assert segments[0][0].year == 2024
        assert segments[1][1].year == 2025

    def test_calculation_context_same_start_end(self):
        """场景15: CalculationContext相同开始结束时间"""
        # 创建相同开始结束时间的上下文
        same_time = datetime(2025, 1, 1, 0, 0, 0)
        ctx = CalculationContext(
            station_id=1,
            device_id=1,
            start_ts=same_time,
            end_ts=same_time
        )
        
        # 验证上下文创建成功
        assert ctx.start_ts == ctx.end_ts


class TestPrecisionBoundaries:
    """精度边界测试"""

    @patch('app.services.calculation.validator.get_connection')
    @patch('app.services.calculation.validator.CharacteristicCurveManager')
    def test_validator_exact_boundary_values(self, mock_curve_mgr, mock_conn):
        """场景16: 验证器精确边界值"""
        # Mock数据库连接
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn_obj = MagicMock()
        mock_conn_obj.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_conn_obj
        
        validator = PhysicsValidator()
        
        # 测试精确边界值
        values = np.array([0.0, 100.0])
        mask, errors = validator.validate_range(values, 0.0, 100.0)
        
        # 验证边界值有效
        assert mask[0]  # 下界
        assert mask[1]  # 上界

    @patch('app.services.calculation.validator.get_connection')
    @patch('app.services.calculation.validator.CharacteristicCurveManager')
    def test_validator_just_outside_boundaries(self, mock_curve_mgr, mock_conn):
        """场景17: 验证器刚好超出边界"""
        # Mock数据库连接
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn_obj = MagicMock()
        mock_conn_obj.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_conn_obj
        
        validator = PhysicsValidator()
        
        # 测试刚好超出边界的值
        values = np.array([-0.001, 100.001])
        mask, errors = validator.validate_range(values, 0.0, 100.0)
        
        # 验证超出边界的值无效
        assert not mask[0]  # 低于下界
        assert not mask[1]  # 高于上界


class TestSpecialCases:
    """特殊情况边界测试"""

    def test_parse_granularity_whitespace_handling(self):
        """场景18: _parse_granularity空白字符处理"""
        # 测试前后空白字符
        assert _parse_granularity("  30m  ") == 1800
        assert _parse_granularity("  1h  ") == 3600

    def test_calculation_context_default_values(self):
        """场景19: CalculationContext默认值"""
        # 创建只有必需参数的上下文
        ctx = CalculationContext(
            station_id=1,
            device_id=1,
            start_ts=datetime(2025, 1, 1, 0, 0, 0),
            end_ts=datetime(2025, 1, 1, 1, 0, 0)
        )
        
        # 验证默认值
        assert ctx.bucket_size_sec == 1
        assert ctx.run_id == ""
        assert ctx.batch_no is None
        assert ctx.strict_mode is False
        assert ctx.quality_filters == {}
        assert ctx.extra == {}

    def test_split_window_exact_multiple_of_step(self):
        """场景20: _split_window时长是步长的精确倍数"""
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 1, 3, 0, 0)  # 3小时
        
        # 使用1小时粒度（精确倍数）
        segments = _split_window(start, end, 3600)
        
        # 验证段数
        assert len(segments) == 3
        
        # 验证每段都是精确1小时
        for seg_start, seg_end in segments:
            duration = (seg_end - seg_start).total_seconds()
            assert duration == 3600

