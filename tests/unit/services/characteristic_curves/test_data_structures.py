"""
数据结构测试 (test_data_structures.py)

测试 models.py 中定义的所有数据类：
- FitResult: 拟合结果
- MethodResult: 方法结果
- ValidationResult: 验证结果
- EvaluationReport: 评估报告
- FittingScenario: 拟合场景枚举

测试用例遵循约束：
- 禁止使用默认值，所有参数显式指定
- 禁止回退机制
"""

from datetime import datetime

import numpy as np
import pytest

from app.services.characteristic_curves.models import (
    CurveType,
    EvaluationReport,
    FitResult,
    FittingScenario,
    GroupProcessingStrategy,
    MethodResult,
    ValidationResult,
)


class TestFitResult:
    """FitResult 数据类测试"""

    def test_fit_result_creation_and_to_dict(self):
        """DS-001: FitResult 创建和序列化"""
        # 显式指定所有参数，不使用默认值
        fit_result = FitResult(
            device_id=105,
            curve_type="qh",
            method_id="math_poly_2",
            method_name="二次多项式",
            version="20251208_150000",
            coefficients={"a": -0.001, "b": 0.0, "c": 120.0},
            r_squared=0.9856,
            rmse=1.234,
            mae=0.987,
            mape=2.5,
            data_points=200,
            time_range={"start": "2025-01-01T00:00:00", "end": "2025-01-31T23:59:59"},
            valid_q_range=(0.0, 300.0),
            valid_h_range=(30.0, 120.0),
            normalization_params={"Q": {"min": 0.0, "max": 300.0}},
            created_at=datetime(2025, 12, 8, 15, 0, 0),
            fitted_at=datetime(2025, 12, 8, 15, 0, 1),
            metadata={"source": "test"},
        )

        result_dict = fit_result.to_dict()

        assert result_dict["method_id"] == "math_poly_2"
        assert result_dict["method_name"] == "二次多项式"
        assert result_dict["version"] == "20251208_150000"
        assert result_dict["coefficients"]["a"] == -0.001
        assert result_dict["r_squared"] == 0.9856
        assert result_dict["data_points"] == 200
        assert "start" in result_dict["time_range"]

    def test_fit_result_from_dict(self):
        """DS-002: FitResult 反序列化"""
        data = {
            "method_id": "physics_pump_char",
            "method_name": "泵特性方程",
            "version": "20251208_160000",
            "coefficients": {"H0": 120.0, "K": 0.001},
            "r_squared": 0.9912,
            "rmse": 0.876,
            "mae": 0.654,
            "mape": 1.8,
            "data_points": 150,
            "time_range": {"start": "2025-02-01T00:00:00", "end": "2025-02-28T23:59:59"},
            "normalization_params": {},
            "created_at": "2025-12-08T16:00:00",
            "metadata": {"validated": True},
        }

        fit_result = FitResult.from_dict(data)

        assert fit_result.method_id == "physics_pump_char"
        assert fit_result.r_squared == 0.9912
        assert fit_result.coefficients["H0"] == 120.0
        assert isinstance(fit_result.created_at, datetime)


class TestMethodResult:
    """MethodResult 数据类测试"""

    def test_method_result_creation_and_serialization(self):
        """DS-003: MethodResult 创建和序列化"""
        # 创建预测函数
        def predict_func(x: np.ndarray) -> np.ndarray:
            return 120.0 - 0.001 * x**2

        method_result = MethodResult(
            method_id="math_poly_2",
            coefficients={"a": -0.001, "b": 0.0, "c": 120.0},
            r_squared=0.9856,
            rmse=1.234,
            mae=0.987,
            mape=2.5,
            predict_func=predict_func,
            formula="H = -0.001*Q² + 120.0",
            metadata={"iterations": 10},
        )

        result_dict = method_result.to_dict()

        # to_dict() 不应包含 predict_func
        assert "predict_func" not in result_dict
        assert result_dict["method_id"] == "math_poly_2"
        assert result_dict["formula"] == "H = -0.001*Q² + 120.0"
        assert result_dict["coefficients"]["a"] == -0.001

    def test_method_result_from_dict(self):
        """DS-004: MethodResult 从字典创建"""
        data = {
            "method_id": "math_spline_cubic",
            "coefficients": {"knots": 5},
            "r_squared": 0.9923,
            "rmse": 0.654,
            "mae": 0.432,
            "mape": 1.2,
            "formula": "三次样条插值",
            "metadata": {"smoothing": 0.5},
        }

        method_result = MethodResult.from_dict(data)

        assert method_result.method_id == "math_spline_cubic"
        assert method_result.r_squared == 0.9923
        assert method_result.predict_func is None  # 从字典创建时 predict_func 为 None


class TestValidationResult:
    """ValidationResult 数据类测试"""

    def test_validation_result_creation(self):
        """DS-005: ValidationResult 创建"""
        validation_result = ValidationResult(
            is_valid=True,
            overall_passed=True,
            monotonicity_passed=True,
            boundary_passed=True,
            physics_passed=True,
            physics_score=95.5,
            checks=[
                {"name": "monotonicity", "passed": True},
                {"name": "boundary", "passed": True},
            ],
            passed_checks=["monotonicity", "boundary", "physics"],
            failed_checks=[],
            errors=[],
            warnings=["扬程接近边界值"],
            details={"max_violation": 0.02},
        )

        assert validation_result.is_valid is True
        assert validation_result.physics_score == 95.5
        assert len(validation_result.passed_checks) == 3
        assert len(validation_result.warnings) == 1

        result_dict = validation_result.to_dict()
        assert result_dict["overall_passed"] is True
        assert result_dict["physics_score"] == 95.5


class TestEvaluationReport:
    """EvaluationReport 数据类测试"""

    def test_evaluation_report_creation(self):
        """DS-006: EvaluationReport 创建"""
        report = EvaluationReport(
            device_id=105,
            curve_type="qh",
            version="20251208_170000",
            data_quality={
                "total_points": 200,
                "valid_points": 195,
                "outlier_ratio": 0.025,
            },
            fit_quality={
                "r_squared": 0.9856,
                "rmse": 1.234,
                "within_5_percent": 0.92,
            },
            physics_validation={
                "monotonicity": True,
                "boundary": True,
                "energy_conservation": True,
            },
            stability_analysis={
                "cv_scores": [0.98, 0.97, 0.99, 0.98, 0.97],
                "mean_cv": 0.978,
            },
            recommendations=["建议增加低流量区数据点", "考虑使用物理模型方法"],
            generated_at=datetime(2025, 12, 8, 17, 0, 0),
        )

        assert report.device_id == 105
        assert report.curve_type == "qh"
        assert report.data_quality["outlier_ratio"] == 0.025
        assert len(report.recommendations) == 2

        report_dict = report.to_dict()
        assert report_dict["device_id"] == 105
        assert "generated_at" in report_dict


class TestFittingScenario:
    """FittingScenario 枚举测试"""

    def test_fitting_scenario_to_processing_strategy(self):
        """DS-007: FittingScenario 到 GroupProcessingStrategy 转换"""
        # 测试所有泵组场景的转换
        test_cases = [
            (FittingScenario.HOMOGENEOUS_GROUP, GroupProcessingStrategy.HOMOGENEOUS_GROUP),
            (FittingScenario.HETEROGENEOUS_GROUP, GroupProcessingStrategy.HETEROGENEOUS_GROUP),
            (FittingScenario.VFD_HETEROGENEOUS_FREQ, GroupProcessingStrategy.VFD_HETEROGENEOUS_FREQ),
            (FittingScenario.MIXED_GROUP, GroupProcessingStrategy.MIXED_GROUP),
            (FittingScenario.MIXED_HETEROGENEOUS, GroupProcessingStrategy.MIXED_HETEROGENEOUS),
        ]

        for scenario, expected_strategy in test_cases:
            result = FittingScenario.to_processing_strategy(scenario)
            assert result == expected_strategy, f"场景 {scenario} 转换失败"

    def test_fitting_scenario_single_pump_no_strategy(self):
        """DS-008: 单泵场景无处理策略"""
        # 单泵场景不应该有对应的 GroupProcessingStrategy
        single_pump_scenarios = [
            FittingScenario.SOFT_START_SINGLE,
            FittingScenario.VFD_SINGLE,
            FittingScenario.QUASI_FIXED_FREQ_SINGLE,
            FittingScenario.UNKNOWN,
            FittingScenario.NOT_SUPPORTED,
        ]

        for scenario in single_pump_scenarios:
            result = FittingScenario.to_processing_strategy(scenario)
            assert result is None, f"单泵场景 {scenario} 不应有处理策略"

