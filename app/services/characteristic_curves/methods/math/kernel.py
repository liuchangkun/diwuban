"""
核函数拟合方法 (app.services.characteristic_curves.methods.math.kernel)

本模块实现核函数类拟合方法：
- MathKernelRbfMethod: 径向基函数 (math_kernel_rbf)

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/05_拟合方法/01_数学方法.md
"""

from typing import Any, Dict, Optional

import numpy as np
from scipy.interpolate import RBFInterpolator

from app.services.characteristic_curves.methods.base_method import BaseMethod
from app.services.characteristic_curves.models import MethodResult


class MathKernelRbfMethod(BaseMethod):
    """径向基函数(RBF)拟合方法

    数学公式:
        f(x) = Σ w_i × φ(||x - x_i||)

    其中 φ 是径向基函数，常用选择:
        - thin_plate_spline: φ(r) = r² * log(r)
        - multiquadric: φ(r) = √(1 + (r/ε)²)
        - gaussian: φ(r) = exp(-r²/(2σ²))

    适用曲线: 所有 (qh, qp, qeta)
    """

    def __init__(
        self, kernel: str = "thin_plate_spline", epsilon: Optional[float] = None
    ) -> None:
        """初始化RBF方法

        Args:
            kernel: 核函数类型 ('thin_plate_spline', 'multiquadric', 'gaussian')
            epsilon: 形状参数（仅对某些核函数有效）
        """
        super().__init__(method_name="径向基函数", method_id="math_kernel_rbf")
        self.kernel = kernel
        self.epsilon = epsilon
        self._rbf: Optional[RBFInterpolator] = None
        self._X_train: Optional[np.ndarray] = None

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        constraints: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> MethodResult:
        """执行RBF拟合

        Args:
            X: 自变量数组（流量Q）
            y: 因变量数组
            constraints: 物理约束参数（可选）
            **kwargs: 其他参数

        Returns:
            MethodResult: 拟合结果
        """
        # 重塑数据为2D（RBFInterpolator要求）
        X_2d = X.reshape(-1, 1)
        self._X_train = X_2d

        # 创建RBF插值器
        if self.epsilon is not None:
            self._rbf = RBFInterpolator(X_2d, y, kernel=self.kernel, epsilon=self.epsilon)
        else:
            self._rbf = RBFInterpolator(X_2d, y, kernel=self.kernel)

        # 计算预测值
        y_pred = self._rbf(X_2d)

        # 计算指标
        metrics = self._calculate_metrics(y, y_pred)

        # 创建预测函数
        rbf = self._rbf

        def predict_func(x: np.ndarray) -> np.ndarray:
            x = np.atleast_1d(x).reshape(-1, 1)
            return rbf(x)

        return MethodResult(
            method_id=self.method_id,
            coefficients={"kernel": self.kernel, "epsilon": self.epsilon, "n_centers": len(X)},
            r_squared=metrics["r_squared"],
            rmse=metrics["rmse"],
            mae=metrics["mae"],
            mape=metrics["mape"],
            predict_func=predict_func,
            formula=f"RBF (kernel={self.kernel})",
            metadata={
                "kernel": self.kernel,
                "epsilon": self.epsilon,
                "quality_grade": self._get_quality_grade(metrics["r_squared"]),
            },
        )

    def predict(self, X: np.ndarray, params: Dict[str, float]) -> np.ndarray:
        """使用拟合参数进行预测（需要先调用fit）"""
        if self._rbf is None:
            raise RuntimeError("必须先调用fit()")
        X_2d = np.atleast_1d(X).reshape(-1, 1)
        return self._rbf(X_2d)


def register_kernel_methods() -> None:
    """注册核方法到 MethodRegistry"""
    from app.services.characteristic_curves.methods.method_registry import MethodRegistry

    registry = MethodRegistry()

    # 注册 MathKernelRbfMethod (适用于所有曲线)
    for curve_type in ["qh", "qp", "qeta"]:
        registry.register(
            curve_type=curve_type,
            method_id="math_kernel_rbf",
            method_name="径向基函数",
            method_class=MathKernelRbfMethod,
            priority=70,
            description="径向基函数(RBF)插值：非参数非线性拟合",
            dependencies=None,
            applicable_conditions={"min_data_points": 50},
        )

