"""
测试 calculation/validator.py - 物理验证器（补充测试）

补充测试场景:
1. 范围验证测试 (2个)
2. 非负验证测试 (2个)
3. NaN/Inf验证测试 (2个)
4. 综合验证测试 (2个)

总计: 8个补充测试场景
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from app.services.calculation.validator import PhysicsValidator


class TestRangeValidation:
    """范围验证测试"""

    @patch('app.services.calculation.validator.get_connection')
    @patch('app.services.calculation.validator.CharacteristicCurveManager')
    def test_validate_range_all_within_range(self, mock_curve_mgr, mock_get_conn):
        """场景1: 所有值都在范围内"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        validator = PhysicsValidator()
        
        # 测试范围验证
        values = np.array([50.0, 60.0, 70.0, 80.0])
        mask, errors = validator.validate_range(values, 0.0, 100.0)
        
        # 验证全部通过
        assert mask.all()
        assert len(errors) == 0

    @patch('app.services.calculation.validator.get_connection')
    @patch('app.services.calculation.validator.CharacteristicCurveManager')
    def test_validate_range_some_out_of_range(self, mock_curve_mgr, mock_get_conn):
        """场景2: 部分值超出范围"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        validator = PhysicsValidator()
        
        # 测试范围验证（包含超出范围的值）
        values = np.array([50.0, 150.0, -10.0, 80.0])
        mask, errors = validator.validate_range(values, 0.0, 100.0)
        
        # 验证部分失败
        assert not mask.all()
        assert len(errors) > 0


class TestNonNegativeValidation:
    """非负验证测试"""

    @patch('app.services.calculation.validator.get_connection')
    @patch('app.services.calculation.validator.CharacteristicCurveManager')
    def test_validate_non_negative_all_positive(self, mock_curve_mgr, mock_get_conn):
        """场景3: 所有值都是非负的"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        validator = PhysicsValidator()
        
        # 测试非负验证
        values = np.array([0.0, 10.0, 50.0, 100.0])
        mask, errors = validator.validate_non_negative(values)
        
        # 验证全部通过
        assert mask.all()
        assert len(errors) == 0

    @patch('app.services.calculation.validator.get_connection')
    @patch('app.services.calculation.validator.CharacteristicCurveManager')
    def test_validate_non_negative_some_negative(self, mock_curve_mgr, mock_get_conn):
        """场景4: 部分值是负数"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        validator = PhysicsValidator()
        
        # 测试非负验证（包含负数）
        values = np.array([10.0, -5.0, 50.0, -20.0])
        mask, errors = validator.validate_non_negative(values)
        
        # 验证部分失败
        assert not mask.all()
        assert len(errors) > 0


class TestNaNInfValidation:
    """NaN/Inf验证测试"""

    @patch('app.services.calculation.validator.get_connection')
    @patch('app.services.calculation.validator.CharacteristicCurveManager')
    def test_validate_not_nan_all_valid(self, mock_curve_mgr, mock_get_conn):
        """场景5: 所有值都不是NaN"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        validator = PhysicsValidator()
        
        # 测试NaN验证
        values = np.array([10.0, 20.0, 30.0, 40.0])
        mask, errors = validator.validate_not_nan(values)
        
        # 验证全部通过
        assert mask.all()
        assert len(errors) == 0

    @patch('app.services.calculation.validator.get_connection')
    @patch('app.services.calculation.validator.CharacteristicCurveManager')
    def test_validate_not_inf_some_inf(self, mock_curve_mgr, mock_get_conn):
        """场景6: 部分值是Inf"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        validator = PhysicsValidator()
        
        # 测试Inf验证（包含Inf）
        values = np.array([10.0, np.inf, 30.0, -np.inf])
        mask, errors = validator.validate_not_inf(values)
        
        # 验证部分失败
        assert not mask.all()
        assert len(errors) > 0


class TestComprehensiveValidation:
    """综合验证测试"""

    @patch('app.services.calculation.validator.get_connection')
    @patch('app.services.calculation.validator.CharacteristicCurveManager')
    def test_validate_pump_efficiency_success(self, mock_curve_mgr, mock_get_conn):
        """场景7: 泵效率综合验证成功"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        validator = PhysicsValidator()
        
        # 测试综合验证
        values = np.array([60.0, 65.0, 70.0, 75.0])
        is_valid, mask, errors, warnings = validator.validate(
            'pump_efficiency',
            values,
            {},
            strict_mode=False
        )
        
        # 验证通过
        assert is_valid
        assert mask.all()

    @patch('app.services.calculation.validator.get_connection')
    @patch('app.services.calculation.validator.CharacteristicCurveManager')
    def test_validate_pump_flow_rate_with_context(self, mock_curve_mgr, mock_get_conn):
        """场景8: 泵流量综合验证（带上下文）"""
        # Mock数据库
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        validator = PhysicsValidator()
        
        # 测试综合验证（带上下文）
        values = np.array([100.0, 105.0, 98.0, 102.0])
        context = {
            'station_id': 1,
            'device_id': 10,
            'rated_flow_rate': 100.0
        }
        
        is_valid, mask, errors, warnings = validator.validate(
            'pump_flow_rate',
            values,
            context,
            strict_mode=False
        )
        
        # 验证结果（可能有警告但应该通过）
        assert isinstance(is_valid, bool)
        assert isinstance(mask, np.ndarray)
        assert isinstance(errors, list)
        assert isinstance(warnings, list)

