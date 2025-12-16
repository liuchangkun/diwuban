"""
P0核心模块单元测试 (test_p0_core_modules.py)

测试P0阶段的核心模块：
- core/data_structures.py: 数据结构
- core/enums.py: 枚举类型  
- preprocessing模块: 数据预处理
- constraints模块: 约束计算

版本: v1.0
创建日期: 2025-12-11
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from app.services.characteristic_curves.core.data_structures import (
    FitResult,
    ConstraintResult,
    SteadyStateResult,
    DataCleaningResult,
    DeviceParams,
    DataQualityReport,
    ScenarioDetectionResult,
)
from app.services.characteristic_curves.core.enums import (
    Scenario,
    CurveType,
    PipelineStage,
)


class TestDataStructures:
    """数据结构测试"""

    def test_fit_result_creation(self):
        """DS-001: FitResult创建和基本属性"""
        result = FitResult(
            device_id=1001,
            curve_type="qh",
            method_id="poly2",
            method_name="二次多项式",
            version="20251211_140000",
            coefficients={"a": -0.005, "b": 0.0, "c": 50.0},
            r_squared=0.95,
            rmse=1.2,
            mae=0.8,
            mape=0.02,
            data_points=50,
            time_range={"start": "2025-12-01", "end": "2025-12-10"},
            valid_q_range=(0.0, 100.0),
            valid_h_range=(0.0, 50.0),
            normalization_params={},
            created_at=datetime.now(),
            success=True,
            formula="H = -0.005*Q^2 + 50.0",
        )

        assert result.device_id == 1001
        assert result.curve_type == "qh"
        assert result.r_squared == 0.95
        assert result.success is True
        assert len(result.coefficients) == 3

    def test_constraint_result_structure(self):
        """DS-002: ConstraintResult结构验证"""
        constraint = ConstraintResult(
            curve_type="qh",
            bounds={"a": (-0.01, 0.0), "b": (-10.0, 10.0), "c": (40.0, 60.0)},
            monotonicity_type="decreasing",
            boundary_values={"H0": 50.0, "Q_max": 100.0},
            additional_constraints=[
                {"type": "monotonicity", "direction": "decreasing"},
            ],
        )

        assert constraint.curve_type == "qh"
        assert constraint.monotonicity_type == "decreasing"
        assert "a" in constraint.bounds
        assert constraint.bounds["a"][0] == -0.01

    def test_steady_state_result(self):
        """DS-003: SteadyStateResult创建"""
        result = SteadyStateResult(
            steady_segments=[(0, 20), (30, 50)],
            segment_count=2,
            total_steady_points=40,
            steady_ratio=0.8,
        )

        assert result.segment_count == 2
        assert result.total_steady_points == 40
        assert result.steady_ratio == 0.8

    def test_data_quality_report(self):
        """DS-004: DataQualityReport创建"""
        report = DataQualityReport(
            total_points=200,
            time_span_days=7.0,
            missing_ratio=0.05,
            quality_score=85.0,
            meets_minimum=True,
            issues=[],
        )

        assert report.total_points == 200
        assert report.quality_score == 85.0
        assert report.meets_minimum is True

    def test_device_params_structure(self):
        """DS-005: DeviceParams结构"""
        params = DeviceParams(
            device_id=1001,
            device_type="single_pump",
            rated_flow=100.0,
            rated_head=50.0,
            rated_power=45.0,
            rated_efficiency=0.75,
            min_frequency=30.0,
            max_frequency=50.0,
        )

        assert params.device_id == 1001
        assert params.rated_flow == 100.0
        assert params.max_frequency == 50.0


class TestEnums:
    """枚举类型测试"""

    def test_scenario_enum_values(self):
        """EN-001: Scenario枚举值"""
        assert Scenario.SOFT_START_SINGLE.value == "soft_start_single"
        assert Scenario.VFD_SINGLE.value == "vfd_single"
        assert Scenario.QUASI_FIXED_FREQ_SINGLE.value == "quasi_fixed_freq_single"
        
        # 验证枚举数量（9个场景）
        scenarios = list(Scenario)
        assert len(scenarios) == 9

    def test_curve_type_enum(self):
        """EN-002: CurveType枚举"""
        assert CurveType.QH.value == "qh"
        assert CurveType.QP.value == "qp"
        assert CurveType.QETA.value == "qeta"

    def test_pipeline_stage_enum(self):
        """EN-003: PipelineStage枚举（16个阶段）"""
        stages = list(PipelineStage)
        # 实际有PLOT_GENERATION和REPORT_GENERATION，总共18个阶段
        assert len(stages) == 18
        
        # 验证P0必需阶段存在
        assert PipelineStage.TIME_WINDOW_SPLIT in stages
        assert PipelineStage.DATA_EXTRACT in stages
        assert PipelineStage.CURVE_FIT in stages
        assert PipelineStage.RESULT_STORE in stages


class TestDataCleaner:
    """DataCleaner测试"""

    def test_clean_basic(self):
        """DC-001: 基本清洗功能"""
        from app.services.characteristic_curves.preprocessing import DataCleaner
        from app.services.characteristic_curves.preprocessing.data_cleaner import CleaningResult

        # 创建测试数据（包含缺失值、重复值和异常值）
        data = pd.DataFrame({
            "Q": [0, 10, 20, 20, 30, 40, 50, 60, 70, 80, 90, 100, 1000],  # 1000是异常值
            "H": [50, 48, 45, 45, 41, 36, 30, 23, 15, 6, np.nan, -5, 10],  # nan和-5是问题数据
        })

        cleaner = DataCleaner()
        result = cleaner.clean(data, x_col="Q", y_col="H")

        # 验证返回类型（CleaningResult而非DataCleaningResult）
        assert isinstance(result, CleaningResult)
        assert isinstance(result.cleaned_data, pd.DataFrame)
        
        # 验证清洗效果
        assert result.removed_count > 0  # 应该移除了一些点
        assert len(result.cleaned_data) < len(data)  # 数据点应该减少

    def test_clean_no_outliers(self):
        """DC-002: 禁用异常值检测"""
        from app.services.characteristic_curves.preprocessing import DataCleaner

        data = pd.DataFrame({
            "Q": np.linspace(0, 100, 20),
            "H": 50 - 0.005 * np.linspace(0, 100, 20) ** 2,
        })

        cleaner = DataCleaner()
        result = cleaner.clean(data, x_col="Q", y_col="H", remove_outliers=False)

        # 没有异常值检测，只处理缺失值和重复值
        assert result.removed_count == 0


class TestSteadyStateDetector:
    """SteadyStateDetector测试"""

    def test_detect_steady_points_all_steady(self):
        """SSD-001: 全稳态数据检测"""
        from app.services.characteristic_curves.preprocessing import SteadyStateDetector

        # 创建稳态数据（流量和扬程波动很小）
        data = pd.DataFrame({
            "flow": [100.0] * 50 + np.random.normal(0, 0.5, 50),
            "head": [50.0] * 50 + np.random.normal(0, 0.3, 50),
        })

        detector = SteadyStateDetector()
        steady_data, result = detector.detect_steady_points(data)

        assert isinstance(result, SteadyStateResult)
        assert result.steady_ratio > 0.5  # 大部分应该是稳态

    def test_detect_steady_points_no_steady(self):
        """SSD-002: 非稳态数据检测"""
        from app.services.characteristic_curves.preprocessing import SteadyStateDetector

        # 创建非稳态数据（大幅波动）
        data = pd.DataFrame({
            "flow": np.random.uniform(0, 200, 50),
            "head": np.random.uniform(0, 100, 50),
        })

        detector = SteadyStateDetector()
        steady_data, result = detector.detect_steady_points(data)

        assert result.steady_ratio < 0.5  # 很少稳态点


class TestScenarioDetector:
    """ScenarioDetector测试"""

    def test_detect_fixed_freq_single(self):
        """SD-001: 检测准恒频单泵场景"""
        from app.services.characteristic_curves.preprocessing import ScenarioDetector

        # 创建准恒频单泵数据（频率基本不变）
        data = pd.DataFrame({
            "Q": np.linspace(0, 100, 50),
            "H": 50 - 0.005 * np.linspace(0, 100, 50) ** 2,
            "frequency": [50.0] * 50,  # 恒定频率
        })

        device_params = {
            "device_type": "single_pump",
            "pump_type": "fixed_frequency",
        }

        detector = ScenarioDetector()
        result = detector.detect(
            device_id=1001,
            device_params=device_params,
            data=data,
        )

        assert isinstance(result, ScenarioDetectionResult)
        # 场景枚举比较需要用值比较
        assert result.scenario.value == Scenario.QUASI_FIXED_FREQ_SINGLE.value
        assert result.supported is True


class TestConstraintCalculator:
    """ConstraintCalculator测试"""

    def test_calculate_qh_constraints(self):
        """CC-001: 计算QH曲线约束"""
        from app.services.characteristic_curves.constraints import ConstraintCalculator

        data = pd.DataFrame({
            "flow": np.linspace(0, 100, 50),
            "head": 50 - 0.005 * np.linspace(0, 100, 50) ** 2,
        })

        device_params = {
            "rated_flow": 100.0,
            "rated_head": 50.0,
            "rated_power": 45.0,
        }

        config = {
            "constraints": {
                "monotonicity_tolerance": 0.01,
                "boundary_tolerance": 0.05,
            }
        }

        calculator = ConstraintCalculator()
        result = calculator.calculate(
            curve_type="qh",
            data=data,
            device_params=device_params,
            config=config,
        )

        assert isinstance(result, ConstraintResult)
        assert result.curve_type == "qh"
        assert result.monotonicity_type == "decreasing"
        assert "a" in result.bounds
        assert "H0" in result.boundary_values


class TestNormalizer:
    """Normalizer测试"""

    def test_minmax_normalization(self):
        """NM-001: MinMax归一化"""
        from app.services.characteristic_curves.preprocessing import Normalizer

        values = np.array([0, 25, 50, 75, 100])
        
        normalizer = Normalizer(method="minmax")
        normalized = normalizer.fit_transform(values)

        # MinMax应该将数据归一化到[0, 1]
        assert normalized.min() == 0.0
        assert normalized.max() == 1.0
        assert normalizer.params is not None

    def test_zscore_normalization(self):
        """NM-002: Z-Score归一化"""
        from app.services.characteristic_curves.preprocessing import Normalizer

        values = np.array([10, 20, 30, 40, 50])
        
        normalizer = Normalizer(method="zscore")
        normalized = normalizer.fit_transform(values)

        # Z-Score后均值应接近0，标准差接近1
        assert abs(normalized.mean()) < 0.1
        assert abs(normalized.std() - 1.0) < 0.1

    def test_inverse_transform(self):
        """NM-003: 逆变换还原"""
        from app.services.characteristic_curves.preprocessing import Normalizer

        original = np.array([10, 20, 30, 40, 50])
        
        normalizer = Normalizer(method="minmax")
        normalized = normalizer.fit_transform(original)
        restored = normalizer.inverse_transform(normalized)

        # 还原后应该接近原始值
        np.testing.assert_array_almost_equal(original, restored, decimal=10)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
