"""
有理函数拟合方法 (app.services.characteristic_curves.methods.math.rational)

本模块实现有理函数类拟合方法：
- MathRationalPadeMethod: Padé逼近 (math_rational_pade)

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/05_拟合方法/01_数学方法.md
"""

from typing import Any, Dict, Optional

import numpy as np
from scipy.optimize import curve_fit

from app.services.characteristic_curves.methods.base_method import BaseMethod
from app.services.characteristic_curves.core.data_structures import MethodResult


class MathRationalPadeMethod(BaseMethod):
    """Padé逼近拟合方法

    数学公式:
        f(x) = (a0 + a1*x + a2*x²) / (1 + b1*x + b2*x²)

    优点:
        - 比多项式有更好的外推性能
        - 能够表示渐近行为
        - 适合有极点或渐近线的曲线

    适用曲线: 所有 (qh, qp, qeta)
    """

    def __init__(self, num_degree: int = 2, den_degree: int = 2) -> None:
        """初始化Padé逼近方法

        Args:
            num_degree: 分子多项式阶数
            den_degree: 分母多项式阶数
        """
        super().__init__(method_name="Padé逼近", method_id="math_rational_pade")
        self.num_degree = num_degree
        self.den_degree = den_degree

    @staticmethod
    def _pade_22(x: np.ndarray, a0: float, a1: float, a2: float, b1: float, b2: float) -> np.ndarray:
        """Padé(2,2)逼近函数"""
        numerator = a0 + a1 * x + a2 * x**2
        denominator = 1 + b1 * x + b2 * x**2
        return numerator / denominator

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        constraints: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> MethodResult:
        """执行Padé逼近拟合

        Args:
            X: 自变量数组（流量Q）
            y: 因变量数组
            constraints: 物理约束参数（可选）
            **kwargs: 其他参数

        Returns:
            MethodResult: 拟合结果
        """
        # 初始猜测（基于数据特征）
        y_init = float(y[0]) if len(y) > 0 else 1.0
        p0 = [y_init, 0.01, -0.0001, 0.001, 0.00001]

        try:
            popt, _ = curve_fit(
                self._pade_22,
                X,
                y,
                p0=p0,
                maxfev=10000,
            )
            a0, a1, a2, b1, b2 = popt

            # 计算预测值
            y_pred = self._pade_22(X, a0, a1, a2, b1, b2)

            # 计算指标
            metrics = self._calculate_metrics(y, y_pred)

            # 创建预测函数
            def predict_func(x: np.ndarray) -> np.ndarray:
                x = np.atleast_1d(x)
                numerator = a0 + a1 * x + a2 * x**2
                denominator = 1 + b1 * x + b2 * x**2
                return numerator / denominator

            return MethodResult(
                method_id=self.method_id,
                coefficients={
                    "a0": float(a0), "a1": float(a1), "a2": float(a2),
                    "b1": float(b1), "b2": float(b2),
                },
                r_squared=metrics["r_squared"],
                rmse=metrics["rmse"],
                mae=metrics["mae"],
                mape=metrics["mape"],
                predict_func=predict_func,
                formula=f"f(x) = ({a0:.4f} + {a1:.4f}x + {a2:.6f}x²) / (1 + {b1:.4f}x + {b2:.6f}x²)",
                metadata={"quality_grade": self._get_quality_grade(metrics["r_squared"])},
            )

        except (RuntimeError, ValueError) as e:
            self._logger.warning(f"Padé逼近拟合失败: {e}")
            return MethodResult(
                method_id=self.method_id,
                coefficients={},
                r_squared=0.0,
                rmse=float("inf"),
                mae=float("inf"),
                mape=0.0,
                predict_func=None,
                formula="拟合失败",
                metadata={"error": str(e)},
            )

    def predict(self, X: np.ndarray, params: Dict[str, float]) -> np.ndarray:
        """使用拟合参数进行预测"""
        a0, a1, a2 = params["a0"], params["a1"], params["a2"]
        b1, b2 = params["b1"], params["b2"]
        numerator = a0 + a1 * X + a2 * X**2
        denominator = 1 + b1 * X + b2 * X**2
        return numerator / denominator


def register_rational_methods() -> None:
    """注册有理函数方法到 MethodRegistry"""
    from app.services.characteristic_curves.methods.method_registry import MethodRegistry

    registry = MethodRegistry()

    # 注册 MathRationalPadeMethod (适用于所有曲线)
    for curve_type in ["qh", "qp", "qeta"]:
        registry.register(
            curve_type=curve_type,
            method_id="math_rational_pade",
            method_name="Padé逼近",
            method_class=MathRationalPadeMethod,
            priority=70,
            description="Padé逼近：有理函数拟合，适合渐近行为",
            dependencies=None,
            applicable_conditions={"min_data_points": 50},
        )

