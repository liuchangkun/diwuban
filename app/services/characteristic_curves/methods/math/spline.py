"""
样条拟合方法 (app.services.characteristic_curves.methods.math.spline)

本模块实现样条类拟合方法：
- MathSplineCubicMethod: 三次样条 (math_spline_cubic)
- MathSplineBsplineMethod: B样条 (math_spline_bspline)

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/05_拟合方法/01_数学方法.md
"""

from typing import Any, Dict, List, Optional

import numpy as np
from scipy.interpolate import BSpline, CubicSpline, splev, splrep

from app.services.characteristic_curves.methods.base_method import BaseMethod
from app.services.characteristic_curves.models import MethodResult


class MathSplineCubicMethod(BaseMethod):
    """三次样条拟合方法

    数学原理:
        在每个区间使用三次多项式，保证整体二阶连续可微
        S_i(x) = a_i + b_i(x-x_i) + c_i(x-x_i)² + d_i(x-x_i)³

    适用曲线: 所有 (qh, qp, qeta)
    """

    def __init__(self, bc_type: str = "natural") -> None:
        """初始化三次样条方法

        Args:
            bc_type: 边界条件类型 ('natural', 'clamped', 'not-a-knot')
        """
        super().__init__(method_name="三次样条", method_id="math_spline_cubic")
        self.bc_type = bc_type
        self._spline: Optional[CubicSpline] = None
        self._X_sorted: Optional[np.ndarray] = None
        self._y_sorted: Optional[np.ndarray] = None

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        constraints: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> MethodResult:
        """执行三次样条拟合"""
        # 排序数据（样条插值要求x递增）
        sorted_idx = np.argsort(X)
        self._X_sorted = X[sorted_idx]
        self._y_sorted = y[sorted_idx]

        # 创建三次样条
        self._spline = CubicSpline(self._X_sorted, self._y_sorted, bc_type=self.bc_type)

        # 计算预测值
        y_pred = self._spline(X)

        # 计算指标
        metrics = self._calculate_metrics(y, y_pred)

        # 存储样条系数用于序列化
        knots = self._X_sorted.tolist()
        coeffs_list: List[List[float]] = self._spline.c.T.tolist()

        # 创建预测函数
        spline = self._spline

        def predict_func(x: np.ndarray) -> np.ndarray:
            x = np.atleast_1d(x)
            return spline(x)

        return MethodResult(
            method_id=self.method_id,
            coefficients={"bc_type": self.bc_type, "n_knots": len(knots)},
            r_squared=metrics["r_squared"],
            rmse=metrics["rmse"],
            mae=metrics["mae"],
            mape=metrics["mape"],
            predict_func=predict_func,
            formula=f"Cubic Spline (bc_type={self.bc_type}, knots={len(knots)})",
            metadata={
                "knots": knots,
                "coeffs": coeffs_list,
                "quality_grade": self._get_quality_grade(metrics["r_squared"]),
            },
        )

    def predict(self, X: np.ndarray, params: Dict[str, float]) -> np.ndarray:
        """使用拟合参数进行预测（需要先调用fit或从metadata重建）"""
        if self._spline is None:
            raise RuntimeError("必须先调用fit()或从metadata重建样条")
        return self._spline(X)


class MathSplineBsplineMethod(BaseMethod):
    """B样条拟合方法

    数学原理:
        B样条是由B样条基函数的线性组合表示
        S(x) = Σ c_i × B_i,k(x)

    优点: 局部控制性，修改一个控制点只影响局部曲线
    适用曲线: 所有 (qh, qp, qeta)
    """

    def __init__(self, degree: int = 3, smoothing: Optional[float] = None) -> None:
        """初始化B样条方法

        Args:
            degree: 样条阶数（默认3，三次B样条）
            smoothing: 平滑参数（None表示精确插值）
        """
        super().__init__(method_name="B样条", method_id="math_spline_bspline")
        self.degree = degree
        self.smoothing = smoothing
        self._tck: Optional[tuple] = None

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        constraints: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> MethodResult:
        """执行B样条拟合"""
        # 排序数据
        sorted_idx = np.argsort(X)
        X_sorted = X[sorted_idx]
        y_sorted = y[sorted_idx]

        # 创建B样条
        self._tck = splrep(X_sorted, y_sorted, k=self.degree, s=self.smoothing)

        # 计算预测值
        y_pred = splev(X, self._tck)

        # 计算指标
        metrics = self._calculate_metrics(y, y_pred)

        # 存储B样条参数
        t, c, k = self._tck
        tck = self._tck

        # 创建预测函数
        def predict_func(x: np.ndarray) -> np.ndarray:
            x = np.atleast_1d(x)
            return splev(x, tck)

        return MethodResult(
            method_id=self.method_id,
            coefficients={"degree": self.degree, "smoothing": self.smoothing, "n_knots": len(t)},
            r_squared=metrics["r_squared"],
            rmse=metrics["rmse"],
            mae=metrics["mae"],
            mape=metrics["mape"],
            predict_func=predict_func,
            formula=f"B-Spline (degree={self.degree}, knots={len(t)})",
            metadata={
                "knots": t.tolist(),
                "coeffs": c.tolist(),
                "quality_grade": self._get_quality_grade(metrics["r_squared"]),
            },
        )

    def predict(self, X: np.ndarray, params: Dict[str, float]) -> np.ndarray:
        """使用拟合参数进行预测（需要先调用fit或从metadata重建）"""
        if self._tck is None:
            raise RuntimeError("必须先调用fit()或从metadata重建B样条")
        return splev(X, self._tck)


def register_spline_methods() -> None:
    """注册样条方法到 MethodRegistry"""
    from app.services.characteristic_curves.methods.method_registry import MethodRegistry

    registry = MethodRegistry()

    # 注册 MathSplineCubicMethod (适用于所有曲线)
    for curve_type in ["qh", "qp", "qeta"]:
        registry.register(
            curve_type=curve_type,
            method_id="math_spline_cubic",
            method_name="三次样条",
            method_class=MathSplineCubicMethod,
            priority=75,
            description="三次样条插值：保证二阶连续可微",
            dependencies=None,
            applicable_conditions={"min_data_points": 50},
        )

    # 注册 MathSplineBsplineMethod (适用于所有曲线)
    for curve_type in ["qh", "qp", "qeta"]:
        registry.register(
            curve_type=curve_type,
            method_id="math_spline_bspline",
            method_name="B样条",
            method_class=MathSplineBsplineMethod,
            priority=75,
            description="B样条：局部控制性强",
            dependencies=None,
            applicable_conditions={"min_data_points": 50},
        )

