"""
统计拟合方法 (app.services.characteristic_curves.methods.math.statistical)

本模块实现统计类拟合方法：
- MathStatGaussianMethod: 高斯函数 (math_stat_gaussian)

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/05_拟合方法/01_数学方法.md
"""

from typing import Any, Dict, Optional

import numpy as np
from scipy.optimize import curve_fit

from app.services.characteristic_curves.methods.base_method import BaseMethod
from app.services.characteristic_curves.models import MethodResult


class MathStatGaussianMethod(BaseMethod):
    """高斯函数拟合方法

    数学公式:
        η = A * exp(-((Q - μ)² / (2 * σ²)))

    适用曲线: Q-η（效率曲线的单峰特性）

    参数说明:
        - A (η_max): 最高效率
        - μ (Q_bep): 最佳效率点流量
        - σ: 峰宽参数
    """

    def __init__(self) -> None:
        """初始化高斯函数方法"""
        super().__init__(method_name="高斯函数", method_id="math_stat_gaussian")

    @staticmethod
    def _gaussian(x: np.ndarray, A: float, mu: float, sigma: float) -> np.ndarray:
        """高斯函数"""
        return A * np.exp(-((x - mu) ** 2) / (2 * sigma**2))

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        constraints: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> MethodResult:
        """执行高斯函数拟合

        Args:
            X: 自变量数组（流量Q）
            y: 因变量数组（效率η）
            constraints: 物理约束参数（可选）
            **kwargs: 其他参数

        Returns:
            MethodResult: 拟合结果
        """
        # 初始猜测
        A_init = float(np.max(y))
        mu_init = float(X[np.argmax(y)])
        sigma_init = float((np.max(X) - np.min(X)) / 4)

        # 参数边界
        bounds = (
            [0, float(np.min(X)), 0],  # 下界: A > 0, mu >= X_min, sigma > 0
            [1.5, float(np.max(X)), float(np.max(X) - np.min(X))],  # 上界
        )

        try:
            popt, _ = curve_fit(
                self._gaussian,
                X,
                y,
                p0=[A_init, mu_init, sigma_init],
                bounds=bounds,
                maxfev=5000,
            )
            A, mu, sigma = popt

            # 计算预测值
            y_pred = self._gaussian(X, A, mu, sigma)

            # 计算指标
            metrics = self._calculate_metrics(y, y_pred)

            # 创建预测函数
            def predict_func(x: np.ndarray) -> np.ndarray:
                x = np.atleast_1d(x)
                return A * np.exp(-((x - mu) ** 2) / (2 * sigma**2))

            return MethodResult(
                method_id=self.method_id,
                coefficients={"A": float(A), "mu": float(mu), "sigma": float(sigma)},
                r_squared=metrics["r_squared"],
                rmse=metrics["rmse"],
                mae=metrics["mae"],
                mape=metrics["mape"],
                predict_func=predict_func,
                formula=f"η = {A:.4f} * exp(-((Q - {mu:.2f})² / (2 * {sigma:.2f}²)))",
                metadata={"quality_grade": self._get_quality_grade(metrics["r_squared"])},
            )

        except (RuntimeError, ValueError) as e:
            self._logger.warning(f"高斯拟合失败: {e}")
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
        A, mu, sigma = params["A"], params["mu"], params["sigma"]
        return A * np.exp(-((X - mu) ** 2) / (2 * sigma**2))


def register_statistical_methods() -> None:
    """注册统计方法到 MethodRegistry"""
    from app.services.characteristic_curves.methods.method_registry import MethodRegistry

    registry = MethodRegistry()

    # 注册 MathStatGaussianMethod (仅适用于 qeta 曲线)
    registry.register(
        curve_type="qeta",
        method_id="math_stat_gaussian",
        method_name="高斯函数",
        method_class=MathStatGaussianMethod,
        priority=90,
        description="高斯函数拟合：η = A * exp(-((Q - μ)² / (2σ²)))，专用于效率曲线",
        dependencies=None,
        applicable_conditions={"min_data_points": 50, "curve_type": "qeta"},
    )

