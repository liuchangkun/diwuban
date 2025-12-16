"""
多项式拟合方法 (app.services.characteristic_curves.methods.math.polynomial)

本模块实现多项式类拟合方法：
- MathPoly2Method: 2次多项式 (math_poly_2)
- MathPoly3Method: 3次多项式 (math_poly_3)

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/05_拟合方法/01_数学方法.md
"""

from typing import Any, Dict, Optional

import numpy as np

from app.services.characteristic_curves.methods.base_method import BaseMethod
from app.services.characteristic_curves.core.data_structures import MethodResult


class MathPoly2Method(BaseMethod):
    """2次多项式拟合方法

    数学公式:
        y = a0 + a1*x + a2*x²

    适用曲线: Q-H, Q-P

    约束条件:
        - Q-H: a2 < 0 (保证递减)
        - Q-P: a1 > 0, a2 < 0 (保证递增且上凸)
    """

    def __init__(
        self,
        method_name: str = "2次多项式",
        method_id: str = "math_poly_2"
    ) -> None:
        """初始化2次多项式方法

        Args:
            method_name: 方法显示名称
            method_id: 方法唯一标识
        """
        super().__init__(method_name=method_name, method_id=method_id)
        self.degree = 2

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        constraints: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> MethodResult:
        """执行2次多项式拟合

        Args:
            X: 自变量数组（流量Q）
            y: 因变量数组（扬程H/功率P）
            constraints: 物理约束参数（可选）
            **kwargs: 其他参数

        Returns:
            MethodResult: 拟合结果
        """
        # 普通最小二乘拟合
        coefficients = np.polyfit(X, y, self.degree)
        a2, a1, a0 = coefficients  # polyfit返回从高次到低次

        # 计算预测值
        y_pred = a0 + a1 * X + a2 * X**2

        # 计算指标
        metrics = self._calculate_metrics(y, y_pred)

        # 创建预测函数（闭包捕获系数）
        def predict_func(x: np.ndarray) -> np.ndarray:
            x = np.atleast_1d(x)
            return a0 + a1 * x + a2 * x**2

        return MethodResult(
            method_id=self.method_id,
            coefficients={"a0": float(a0), "a1": float(a1), "a2": float(a2)},
            r_squared=metrics["r_squared"],
            rmse=metrics["rmse"],
            mae=metrics["mae"],
            mape=metrics["mape"],
            predict_func=predict_func,
            formula=f"y = {a0:.6f} + {a1:.6f}*x + {a2:.8f}*x²",
            metadata={"degree": self.degree, "quality_grade": self._get_quality_grade(
                metrics["r_squared"])},
        )

    def predict(self, X: np.ndarray, params: Dict[str, float]) -> np.ndarray:
        """使用拟合参数进行预测

        Args:
            X: 自变量数组
            params: 拟合参数 {'a0': ..., 'a1': ..., 'a2': ...}

        Returns:
            np.ndarray: 预测值数组
        """
        a0 = params["a0"]
        a1 = params["a1"]
        a2 = params["a2"]
        return a0 + a1 * X + a2 * X**2


class MathPoly3Method(BaseMethod):
    """3次多项式拟合方法

    数学公式:
        y = a0 + a1*x + a2*x² + a3*x³

    适用曲线: Q-H, Q-P, Q-η（所有曲线）
    """

    def __init__(
        self,
        method_name: str = "3次多项式",
        method_id: str = "math_poly_3"
    ) -> None:
        """初始化3次多项式方法

        Args:
            method_name: 方法显示名称
            method_id: 方法唯一标识
        """
        super().__init__(method_name=method_name, method_id=method_id)
        self.degree = 3

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        constraints: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> MethodResult:
        """执行3次多项式拟合"""
        # 普通最小二乘拟合
        coefficients = np.polyfit(X, y, self.degree)
        a3, a2, a1, a0 = coefficients

        # 计算预测值
        y_pred = a0 + a1 * X + a2 * X**2 + a3 * X**3

        # 计算指标
        metrics = self._calculate_metrics(y, y_pred)

        # 创建预测函数
        def predict_func(x: np.ndarray) -> np.ndarray:
            x = np.atleast_1d(x)
            return a0 + a1 * x + a2 * x**2 + a3 * x**3

        return MethodResult(
            method_id=self.method_id,
            coefficients={"a0": float(a0), "a1": float(
                a1), "a2": float(a2), "a3": float(a3)},
            r_squared=metrics["r_squared"],
            rmse=metrics["rmse"],
            mae=metrics["mae"],
            mape=metrics["mape"],
            predict_func=predict_func,
            formula=f"y = {a0:.6f} + {a1:.6f}*x + {a2:.8f}*x² + {a3:.10f}*x³",
            metadata={"degree": self.degree, "quality_grade": self._get_quality_grade(
                metrics["r_squared"])},
        )

    def predict(self, X: np.ndarray, params: Dict[str, float]) -> np.ndarray:
        """使用拟合参数进行预测"""
        a0, a1, a2, a3 = params["a0"], params["a1"], params["a2"], params["a3"]
        return a0 + a1 * X + a2 * X**2 + a3 * X**3


def register_polynomial_methods() -> None:
    """注册多项式方法到 MethodRegistry"""
    from app.services.characteristic_curves.methods.method_registry import MethodRegistry

    registry = MethodRegistry()

    # 注册 MathPoly2Method
    for curve_type in ["qh", "qp"]:
        registry.register(
            curve_type=curve_type,
            method_id="math_poly_2",
            method_name="2次多项式",
            method_class=MathPoly2Method,
            priority=80,
            description="2次多项式拟合：y = a0 + a1*x + a2*x²",
            dependencies=None,
            applicable_conditions={"min_data_points": 50},
        )

    # 注册 MathPoly3Method
    for curve_type in ["qh", "qp", "qeta"]:
        registry.register(
            curve_type=curve_type,
            method_id="math_poly_3",
            method_name="3次多项式",
            method_class=MathPoly3Method,
            priority=85,
            description="3次多项式拟合：y = a0 + a1*x + a2*x² + a3*x³",
            dependencies=None,
            applicable_conditions={"min_data_points": 50},
        )
