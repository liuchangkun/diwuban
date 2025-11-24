"""
物理约束多项式拟合方法 (app.services.characteristic_curves.methods.hybrid.physics_polynomial)

结合物理模型约束和多项式拟合的混合方法。

适用场景: 需要高精度且满足物理约束的场景
适用曲线: Q-H, Q-P

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/05_拟合方法/04_混合方法.md
"""

import logging
from typing import Any, Dict, Optional

import numpy as np
from scipy.optimize import minimize

from app.services.characteristic_curves.methods.base_method import BaseMethod
from app.services.characteristic_curves.models import MethodResult

logger = logging.getLogger(__name__)


class HybridPhysicsPolyMethod(BaseMethod):
    """物理约束多项式拟合方法

    算法原理:
        在物理约束条件下进行多项式拟合，保证:
        1. 物理边界条件满足（如H0在合理范围）
        2. 单调性约束满足（如Q-H递减，Q-P递增）
        3. 拟合精度最大化

    数学公式:
        Q-H曲线: H = H₀ - k₁Q - k₂Q²
        Q-P曲线: P = P₀ + k₁Q + k₂Q²

    约束条件:
        Q-H: H₀ ∈ [1.05×H_max, 1.3×H_max], k₁ ≥ 0, k₂ > 0
        Q-P: P₀ ∈ [0.8×P_min, 1.2×P_min], k₁ ≥ 0, k₂ ≥ 0

    优势:
        - 结合物理模型的可解释性
        - 结合多项式的拟合灵活性
        - 保证物理约束满足
        - 预期精度 R² > 0.98

    适用曲线: Q-H, Q-P

    Attributes:
        method_id: 'hybrid_physics_poly'
        method_name: '物理约束多项式'
        applicable_curves: ['qh', 'qp']
    """

    method_id = "hybrid_physics_poly"
    method_name = "物理约束多项式"
    applicable_curves = ["qh", "qp"]

    def __init__(self, curve_type: str = "qh") -> None:
        """初始化物理约束多项式方法

        Args:
            curve_type: 曲线类型 ('qh' 或 'qp')
        """
        super().__init__(method_name="物理约束多项式", method_id="hybrid_physics_poly")
        self.curve_type = curve_type

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        constraints: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> MethodResult:
        """执行物理约束多项式拟合

        Args:
            X: 自变量数组（流量Q）
            y: 因变量数组（扬程H/功率P）
            constraints: 物理约束参数
            **kwargs: 其他参数，可包含 curve_type

        Returns:
            MethodResult: 拟合结果
        """
        # 允许通过kwargs覆盖curve_type
        curve_type = kwargs.get("curve_type", self.curve_type)
        constraints = constraints or {}

        if curve_type == "qh":
            return self._fit_qh(X, y, constraints)
        elif curve_type == "qp":
            return self._fit_qp(X, y, constraints)
        else:
            raise ValueError(f"不支持的曲线类型: {curve_type}，仅支持 'qh' 或 'qp'")

    def _fit_qh(
        self, X: np.ndarray, y: np.ndarray, constraints: Dict[str, Any]
    ) -> MethodResult:
        """Q-H曲线拟合: H = H₀ - k₁Q - k₂Q²"""
        # 从约束获取边界，使用数据估计默认值
        H0_min = constraints.get("H0_min", float(y.max()) * 1.05)
        H0_max = constraints.get("H0_max", float(y.max()) * 1.3)

        def objective(params: np.ndarray) -> float:
            H0, k1, k2 = params
            y_pred = H0 - k1 * X - k2 * X**2
            return float(np.sum((y - y_pred) ** 2))

        # 使用bounds参数（L-BFGS-B支持）
        bounds = [
            (H0_min, H0_max),  # H0范围
            (0, None),  # k1 >= 0
            (1e-8, None),  # k2 > 0
        ]

        # 初始参数估计
        x0 = [float(y.max()) * 1.1, 0.01, 0.001]

        result = minimize(objective, x0=x0, bounds=bounds, method="L-BFGS-B")

        if not result.success:
            logger.warning(f"[{self.method_id}] 优化未完全收敛: {result.message}")

        H0, k1, k2 = result.x
        y_pred = H0 - k1 * X - k2 * X**2
        metrics = self._calculate_metrics(y, y_pred)
        quality_grade = self._get_quality_grade(metrics["r_squared"])

        def predict_func(x: np.ndarray) -> np.ndarray:
            x_arr = np.atleast_1d(x)
            return H0 - k1 * x_arr - k2 * x_arr**2

        return MethodResult(
            method_id=self.method_id,
            coefficients={"H0": float(H0), "k1": float(k1), "k2": float(k2)},
            r_squared=metrics["r_squared"],
            rmse=metrics["rmse"],
            mae=metrics["mae"],
            mape=metrics["mape"],
            predict_func=predict_func,
            formula=f"H = {H0:.4f} - {k1:.6f}×Q - {k2:.8f}×Q²",
            metadata={
                "physics_valid": True,
                "curve_type": "qh",
                "quality_grade": quality_grade,
                "optimization_success": result.success,
            },
        )

    def _fit_qp(
        self, X: np.ndarray, y: np.ndarray, constraints: Dict[str, Any]
    ) -> MethodResult:
        """Q-P曲线拟合: P = P₀ + k₁Q + k₂Q²"""
        # 从约束获取边界
        P0_min = constraints.get("P0_min", float(y.min()) * 0.8)
        P0_max = constraints.get("P0_max", float(y.min()) * 1.2)

        def objective(params: np.ndarray) -> float:
            P0, k1, k2 = params
            y_pred = P0 + k1 * X + k2 * X**2
            return float(np.sum((y - y_pred) ** 2))

        # 使用bounds参数
        bounds = [
            (P0_min, P0_max),  # P0范围
            (0, None),  # k1 >= 0
            (0, None),  # k2 >= 0
        ]

        # 初始参数估计
        x0 = [float(y.min()), 0.01, 0.0001]

        result = minimize(objective, x0=x0, bounds=bounds, method="L-BFGS-B")

        if not result.success:
            logger.warning(f"[{self.method_id}] 优化未完全收敛: {result.message}")

        P0, k1, k2 = result.x
        y_pred = P0 + k1 * X + k2 * X**2
        metrics = self._calculate_metrics(y, y_pred)
        quality_grade = self._get_quality_grade(metrics["r_squared"])

        def predict_func(x: np.ndarray) -> np.ndarray:
            x_arr = np.atleast_1d(x)
            return P0 + k1 * x_arr + k2 * x_arr**2

        return MethodResult(
            method_id=self.method_id,
            coefficients={"P0": float(P0), "k1": float(k1), "k2": float(k2)},
            r_squared=metrics["r_squared"],
            rmse=metrics["rmse"],
            mae=metrics["mae"],
            mape=metrics["mape"],
            predict_func=predict_func,
            formula=f"P = {P0:.4f} + {k1:.6f}×Q + {k2:.8f}×Q²",
            metadata={
                "physics_valid": True,
                "curve_type": "qp",
                "quality_grade": quality_grade,
                "optimization_success": result.success,
            },
        )

    def predict(self, X: np.ndarray, params: Dict[str, float]) -> np.ndarray:
        """使用参数进行预测

        Args:
            X: 自变量数组
            params: 拟合参数字典，需包含 H0/P0, k1, k2

        Returns:
            np.ndarray: 预测值数组
        """
        X_arr = np.atleast_1d(X)

        if self.curve_type == "qh":
            H0 = params.get("H0", 0.0)
            k1 = params.get("k1", 0.0)
            k2 = params.get("k2", 0.0)
            return H0 - k1 * X_arr - k2 * X_arr**2
        else:  # qp
            P0 = params.get("P0", 0.0)
            k1 = params.get("k1", 0.0)
            k2 = params.get("k2", 0.0)
            return P0 + k1 * X_arr + k2 * X_arr**2

