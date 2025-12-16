"""
泵组直接拟合集成测试

测试新增的直接拟合功能：
- GroupDataExtractor
- GroupCurveFitter
- GroupCurveComparator
- DualMethodExecutor
- P2Pipeline集成

版本: v1.0
创建日期: 2025-12-09
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import numpy as np

from app.services.characteristic_curves.pump_group.models import (
    GroupOperatingPoint,
    DirectFitResult,
    ComparisonResult,
    CurveFitMethod,
)
from app.services.characteristic_curves.pump_group.group_data_extractor import (
    GroupDataExtractor,
)
from app.services.characteristic_curves.pump_group.group_curve_fitter import (
    GroupCurveFitter,
)
from app.services.characteristic_curves.pump_group.group_curve_comparator import (
    GroupCurveComparator,
)
from app.services.characteristic_curves.pump_group.dual_method_executor import (
    DualMethodExecutor,
)


class TestGroupDataExtractor:
    """测试数据提取器"""

    @pytest.fixture
    def extractor(self):
        return GroupDataExtractor()

    def test_group_by_pump_combination(self, extractor):
        """测试按泵组合分组"""
        points = [
            GroupOperatingPoint(
                ts_bucket=datetime.now(),
                Q_total=100.0,
                H_system=50.0,
                running_pumps=(1, 2),
            ),
            GroupOperatingPoint(
                ts_bucket=datetime.now(),
                Q_total=150.0,
                H_system=45.0,
                running_pumps=(1, 2, 3),
            ),
            GroupOperatingPoint(
                ts_bucket=datetime.now(),
                Q_total=110.0,
                H_system=48.0,
                running_pumps=(1, 2),
            ),
        ]

        groups = extractor.group_by_pump_combination(points)

        assert len(groups) == 2
        assert len(groups[(1, 2)]) == 2
        assert len(groups[(1, 2, 3)]) == 1


class TestGroupCurveFitter:
    """测试曲线拟合器"""

    @pytest.fixture
    def fitter(self):
        return GroupCurveFitter()

    @pytest.fixture
    def sample_points(self):
        """生成样本数据点（150个）"""
        np.random.seed(42)
        Q = np.linspace(50, 300, 150)
        # H = 60 - 0.001 * Q^2 + noise
        H = 60 - 0.001 * Q**2 + np.random.normal(0, 0.5, 150)

        points = []
        for q, h in zip(Q, H):
            point = GroupOperatingPoint(
                ts_bucket=datetime.now(),
                Q_total=float(q),
                H_system=float(h),
                running_pumps=(1, 2),
            )
            points.append(point)

        return points

    def test_fit_polynomial_success(self, fitter, sample_points):
        """测试多项式拟合成功"""
        result = fitter.fit_polynomial(
            station_id=1,
            pump_combination=[1, 2],
            points=sample_points,
            curve_type="qh",
            degree=2,
        )

        assert isinstance(result, DirectFitResult)
        assert result.polynomial_degree == 2
        assert result.r_squared > 0.85
        assert result.rmse > 0
        # PolynomialFeatures(degree=2, include_bias=True) → [1, x, x^2] → 4 coefficients (intercept + 3)
        assert len(result.coefficients) >= 3


class TestGroupCurveComparator:
    """测试曲线对比器"""

    @pytest.fixture
    def comparator(self):
        return GroupCurveComparator()

    def test_compare_direct_fit_better(self, comparator):
        """测试直接拟合更好的情况"""
        direct_fit = DirectFitResult(
            station_id=1,
            pump_combination=[1, 2],
            curve_type="qh",
            coefficients=[60.0, -0.1, -0.001],
            polynomial_degree=2,
            r_squared=0.95,
            rmse=0.5,
            mae=0.4,
            mape=1.0,
            data_points_used=150,
        )

        synthesis = {
            "r_squared": 0.90,
            "rmse": 0.8,
            "mae": 0.6,
            "mape": 1.5,
        }

        result = comparator.compare(direct_fit, synthesis)

        assert isinstance(result, ComparisonResult)
        assert result.recommended_method == CurveFitMethod.DIRECT_FIT
        assert result.r_squared_diff_pct > 0  # 直接拟合R²更高
        assert "直接拟合" in result.recommendation_reason

