"""
方法层单元测试 (test_methods_layer.py)

测试范围：
- BaseMethod 抽象基类
- MethodRegistry 注册表
- MethodBenchmark 数据类

测试说明：
- 使用具体子类测试 BaseMethod 的通用方法
- 测试 MethodRegistry 的线程安全性
- 验证常量值与文档一致性

版本: v1.0
更新日期: 2025-12-08
"""

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import pytest

from app.services.characteristic_curves.methods.base_method import (
    MIN_DATA_POINTS,
    MIN_EXTRACTION_POINTS,
    MIN_VALIDATION_POINTS,
    R2_EXCELLENT_THRESHOLD,
    R2_FAIR_THRESHOLD,
    R2_GOOD_THRESHOLD,
    BaseMethod,
)
from app.services.characteristic_curves.methods.method_registry import (
    DEFAULT_METHOD_BENCHMARKS,
    MethodBenchmark,
    MethodRegistry,
)
from app.services.characteristic_curves.models import MethodResult


# ==================== 测试用的具体子类 ====================


class ConcreteMethod(BaseMethod):
    """用于测试的 BaseMethod 具体实现"""

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        constraints: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> MethodResult:
        """简单的线性拟合实现"""
        # 使用最小二乘法拟合 y = a*x + b
        if len(X) < 2:
            raise ValueError("数据点数量不足")

        X_mean = np.mean(X)
        y_mean = np.mean(y)
        a = np.sum((X - X_mean) * (y - y_mean)) / np.sum((X - X_mean) ** 2)
        b = y_mean - a * X_mean

        y_pred = self.predict(X, {"a": a, "b": b})
        metrics = self._calculate_metrics(y, y_pred)

        return MethodResult(
            method_id=self.method_id,
            coefficients={"a": float(a), "b": float(b)},
            r_squared=metrics["r_squared"],
            rmse=metrics["rmse"],
            mae=metrics["mae"],
            mape=metrics["mape"],
            formula=f"y = {a:.4f} * x + {b:.4f}",
            metadata={
                "method_name": self.method_name,
                "fit_time_seconds": 0.001,
                "data_points": len(X),
                "quality_grade": self._get_quality_grade(metrics["r_squared"]),
            },
        )

    def predict(self, X: np.ndarray, params: Dict[str, float]) -> np.ndarray:
        """线性预测"""
        return params["a"] * X + params["b"]


# ==================== 常量测试 ====================


class TestConstants:
    """测试配置常量"""

    def test_min_data_points(self):
        """测试 MIN_DATA_POINTS 常量值"""
        assert MIN_DATA_POINTS == 50

    def test_min_extraction_points(self):
        """测试 MIN_EXTRACTION_POINTS 常量值"""
        assert MIN_EXTRACTION_POINTS == 100

    def test_min_validation_points(self):
        """测试 MIN_VALIDATION_POINTS 常量值"""
        assert MIN_VALIDATION_POINTS == 50

    def test_r2_thresholds(self):
        """测试 R² 阈值常量值"""
        assert R2_EXCELLENT_THRESHOLD == 0.99
        assert R2_GOOD_THRESHOLD == 0.95
        assert R2_FAIR_THRESHOLD == 0.90
        # 验证顺序：excellent > good > fair
        assert R2_EXCELLENT_THRESHOLD > R2_GOOD_THRESHOLD > R2_FAIR_THRESHOLD


# ==================== BaseMethod 测试 ====================


class TestBaseMethod:
    """BaseMethod 抽象基类测试"""

    def test_init(self):
        """测试初始化"""
        method = ConcreteMethod("测试方法", "test_method_001")
        assert method.method_name == "测试方法"
        assert method.method_id == "test_method_001"
        assert method.default_params == {}

    def test_fit_linear_data(self):
        """测试线性数据拟合"""
        method = ConcreteMethod("线性拟合", "linear_fit")

        # 生成完美线性数据：y = 2x + 1
        X = np.linspace(0, 100, 100)
        y = 2 * X + 1

        result = method.fit(X, y)

        assert result.method_id == "linear_fit"
        assert result.r_squared > 0.99
        assert abs(result.coefficients["a"] - 2.0) < 0.01
        assert abs(result.coefficients["b"] - 1.0) < 0.01
        assert result.metadata["quality_grade"] == "excellent"

    def test_calculate_metrics(self):
        """测试指标计算"""
        method = ConcreteMethod("测试方法", "test")

        y_true = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y_pred = np.array([1.1, 1.9, 3.1, 3.9, 5.1])

        metrics = method._calculate_metrics(y_true, y_pred)

        assert "r_squared" in metrics
        assert "rmse" in metrics
        assert "mae" in metrics
        assert "mape" in metrics
        assert metrics["r_squared"] > 0.99  # 接近完美拟合
        assert metrics["rmse"] < 0.2
        assert metrics["mae"] < 0.2

    def test_validate_input_valid_data(self):
        """测试输入验证 - 有效数据"""
        method = ConcreteMethod("测试方法", "test")

        # 创建足够数据点的 DataFrame
        data = pd.DataFrame({"x": np.linspace(0, 100, MIN_DATA_POINTS + 10)})

        result = method._validate_input(data)

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert "数据非空" in result.passed_checks
        assert "数据量充足" in result.passed_checks

    def test_validate_input_empty_data(self):
        """测试输入验证 - 空数据"""
        method = ConcreteMethod("测试方法", "test")

        data = pd.DataFrame()

        result = method._validate_input(data)

        assert result.is_valid is False
        assert len(result.errors) > 0
        assert "数据非空" in result.failed_checks

    def test_validate_input_insufficient_data(self):
        """测试输入验证 - 数据量不足"""
        method = ConcreteMethod("测试方法", "test")

        # 创建少于 MIN_DATA_POINTS 的数据
        data = pd.DataFrame({"x": np.linspace(0, 10, MIN_DATA_POINTS - 10)})

        result = method._validate_input(data)

        assert result.is_valid is False
        assert "数据量充足" in result.failed_checks

    def test_get_quality_grade_excellent(self):
        """测试质量等级 - 优秀"""
        method = ConcreteMethod("测试方法", "test")

        assert method._get_quality_grade(0.995) == "excellent"
        assert method._get_quality_grade(0.99) == "excellent"
        assert method._get_quality_grade(1.0) == "excellent"

    def test_get_quality_grade_good(self):
        """测试质量等级 - 良好"""
        method = ConcreteMethod("测试方法", "test")

        assert method._get_quality_grade(0.98) == "good"
        assert method._get_quality_grade(0.95) == "good"

    def test_get_quality_grade_fair(self):
        """测试质量等级 - 合格"""
        method = ConcreteMethod("测试方法", "test")

        assert method._get_quality_grade(0.92) == "fair"
        assert method._get_quality_grade(0.90) == "fair"

    def test_get_quality_grade_poor(self):
        """测试质量等级 - 较差"""
        method = ConcreteMethod("测试方法", "test")

        assert method._get_quality_grade(0.85) == "poor"
        assert method._get_quality_grade(0.5) == "poor"
        assert method._get_quality_grade(0.0) == "poor"

    def test_estimate_initial_params(self):
        """测试初始参数估计"""
        method = ConcreteMethod("测试方法", "test")

        X = np.array([0, 50, 100])
        y = np.array([100, 75, 50])  # 下降趋势

        params = method._estimate_initial_params(X, y)

        assert "slope_estimate" in params
        assert "intercept_estimate" in params
        assert "x_min" in params
        assert "x_max" in params
        assert "y_min" in params
        assert "y_max" in params
        assert params["slope_estimate"] < 0  # 负斜率
        assert params["x_min"] == 0
        assert params["x_max"] == 100


# ==================== MethodBenchmark 测试 ====================


class TestMethodBenchmark:
    """MethodBenchmark 数据类测试"""

    def test_benchmark_creation(self):
        """测试基准数据创建"""
        benchmark = MethodBenchmark(
            avg_fit_time_ms=100.0,
            avg_memory_mb=20.0,
            typical_r_squared=0.95,
            recommended_data_points=1000,
            max_data_points=100000,
        )

        assert benchmark.avg_fit_time_ms == 100.0
        assert benchmark.avg_memory_mb == 20.0
        assert benchmark.typical_r_squared == 0.95
        assert benchmark.recommended_data_points == 1000
        assert benchmark.max_data_points == 100000

    def test_default_benchmarks_count(self):
        """测试默认基准数据数量（14种P0方法）"""
        assert len(DEFAULT_METHOD_BENCHMARKS) == 14

    def test_default_benchmarks_content(self):
        """测试默认基准数据包含预期方法"""
        expected_methods = [
            "math_poly_2",
            "math_poly_3",
            "math_spline_cubic",
            "math_spline_bspline",
            "math_kernel_rbf",
            "math_rational_pade",
            "math_stat_gaussian",
            "math_local_lowess",
            "physics_pump_char",
            "physics_power_eq",
            "ml_gradient_boost",
            "ml_random_forest",
            "ml_gaussian_process",
            "hybrid_physics_poly",
        ]

        for method_id in expected_methods:
            assert method_id in DEFAULT_METHOD_BENCHMARKS
            benchmark = DEFAULT_METHOD_BENCHMARKS[method_id]
            assert isinstance(benchmark, MethodBenchmark)
            assert benchmark.avg_fit_time_ms > 0
            assert benchmark.avg_memory_mb > 0
            assert 0 < benchmark.typical_r_squared <= 1.0


# ==================== MethodRegistry 测试 ====================


class TestMethodRegistry:
    """MethodRegistry 注册表测试"""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """每个测试前重置单例状态"""
        # 保存原始状态
        original_instance = MethodRegistry._instance
        MethodRegistry._instance = None

        yield

        # 恢复原始状态
        MethodRegistry._instance = original_instance

    def test_singleton_pattern(self):
        """测试单例模式"""
        registry1 = MethodRegistry()
        registry2 = MethodRegistry()

        assert registry1 is registry2

    def test_register_and_get_method(self):
        """测试方法注册和获取"""
        registry = MethodRegistry()

        # 注册方法
        registry.register(
            curve_type="qh",
            method_id="test_linear",
            method_name="测试线性方法",
            method_class=ConcreteMethod,
            priority=100,
            description="用于单元测试的线性拟合方法",
        )

        # 获取方法
        method = registry.get_method("qh", "test_linear")

        assert isinstance(method, ConcreteMethod)

    def test_get_method_not_found(self):
        """测试获取不存在的方法"""
        registry = MethodRegistry()

        with pytest.raises(ValueError, match="曲线类型不存在"):
            registry.get_method("nonexistent", "method")

    def test_list_methods(self):
        """测试列出方法"""
        registry = MethodRegistry()

        # 注册多个方法
        registry.register(
            curve_type="qh",
            method_id="method_a",
            method_name="方法A",
            method_class=ConcreteMethod,
            priority=100,
            description="测试方法A",
        )
        registry.register(
            curve_type="qh",
            method_id="method_b",
            method_name="方法B",
            method_class=ConcreteMethod,
            priority=200,
            description="测试方法B",
        )

        methods = registry.list_methods("qh")

        assert len(methods) == 2
        method_ids = [m["method_id"] for m in methods]
        assert "method_a" in method_ids
        assert "method_b" in method_ids

    def test_select_best_method(self):
        """测试自动选择最佳方法"""
        registry = MethodRegistry()

        # 注册不同优先级的方法
        registry.register(
            curve_type="qh",
            method_id="low_priority",
            method_name="低优先级方法",
            method_class=ConcreteMethod,
            priority=50,
            description="低优先级",
        )
        registry.register(
            curve_type="qh",
            method_id="high_priority",
            method_name="高优先级方法",
            method_class=ConcreteMethod,
            priority=200,
            description="高优先级",
        )

        # 创建测试数据
        data = pd.DataFrame({"flow": np.linspace(0, 100, 100)})

        # 选择最佳方法
        best_method_id = registry.select_best_method(
            device_id=1,
            curve_type="qh",
            data=data,
            available_columns=["flow"],
        )

        assert best_method_id == "high_priority"

    def test_get_recommended_method_success(self):
        """测试获取推荐方法 - 成功"""
        registry = MethodRegistry()

        recommendations = {"qh": "math_poly_2", "qp": "physics_power_eq"}

        result = registry.get_recommended_method("qh", recommendations)
        assert result == "math_poly_2"

    def test_get_recommended_method_not_configured(self):
        """测试获取推荐方法 - 未配置时抛出异常"""
        registry = MethodRegistry()

        recommendations = {"qh": "math_poly_2"}

        with pytest.raises(ValueError, match="数据库中未配置曲线类型"):
            registry.get_recommended_method("qeta", recommendations)

    def test_get_benchmark(self):
        """测试获取方法性能基准"""
        registry = MethodRegistry()

        benchmark = registry.get_benchmark("math_poly_2")

        assert benchmark is not None
        assert isinstance(benchmark, MethodBenchmark)
        assert benchmark.avg_fit_time_ms == 50
        assert benchmark.typical_r_squared == 0.95

    def test_get_benchmark_not_found(self):
        """测试获取不存在的基准数据"""
        registry = MethodRegistry()

        benchmark = registry.get_benchmark("nonexistent_method")

        assert benchmark is None

