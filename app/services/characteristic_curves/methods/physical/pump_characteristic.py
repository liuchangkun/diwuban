"""
泵特性方程拟合方法 (app.services.characteristic_curves.methods.physics.pump_characteristic)

本模块实现泵特性方程拟合方法：
- PhysicsPumpCharMethod: 泵特性方程 (physics_pump_char)

物理公式: H = H0 - K × Q²
适用曲线: Q-H 专用
优先级: 100 (最高)

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/05_拟合方法/02_物理模型.md
"""

from typing import Any, Dict, Optional

import numpy as np
from scipy.optimize import curve_fit

from app.services.characteristic_curves.methods.base_method import BaseMethod
from app.services.characteristic_curves.core.data_structures import MethodResult


class PhysicsPumpCharMethod(BaseMethod):
    """泵特性方程拟合方法

    物理公式:
        H = H0 - K × Q²

    物理意义:
        H0: 零流量扬程（截止扬程）
        K: 阻力系数

    物理约束:
        - H0 > 0 (关阀扬程为正)
        - K > 0 (阻力系数为正)
        - dH/dQ = -2KQ < 0 (单调递减，对于Q>0恒成立)

    适用曲线: Q-H 专用
    优先级: 100 (最高)
    """

    def __init__(self) -> None:
        """初始化泵特性方程方法"""
        super().__init__(method_name="泵特性方程", method_id="physics_pump_char")

    @staticmethod
    def _pump_curve(Q: np.ndarray, H0: float, K: float) -> np.ndarray:
        """泵特性方程: H = H0 - K × Q²"""
        return H0 - K * Q**2

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        constraints: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> MethodResult:
        """执行泵特性方程拟合

        Args:
            X: 流量数组（Q）
            y: 扬程数组（H）
            constraints: 物理约束参数，应包含 'H0' 和 'K' 的初始估计
            **kwargs: 其他参数

        Returns:
            MethodResult: 拟合结果

        Raises:
            ValueError: 当输入数据不满足物理要求时
        """
        # 输入验证（复用基类方法）
        self._validate_input(X, y)

        # 物理约束验证
        if np.any(X < 0):
            raise ValueError("流量Q不能为负值")
        if np.any(y < 0):
            raise ValueError("扬程H不能为负值")

        constraints = constraints or {}

        # 从约束参数获取初始猜测（禁止硬编码默认值）
        if "H0" in constraints:
            H0_init = constraints["H0"]
            if H0_init <= 0:
                raise ValueError(f"约束参数H0必须大于0，当前值: {H0_init}")
        else:
            # 基于数据估计（不是硬编码，是从数据推断）
            H0_init = float(np.max(y)) * 1.1  # 略高于最大扬程

        if "K" in constraints:
            K_init = constraints["K"]
            if K_init <= 0:
                raise ValueError(f"约束参数K必须大于0，当前值: {K_init}")
        else:
            # 基于数据估计
            Q_max = float(np.max(X))
            if Q_max > 0:
                K_init = (H0_init - float(np.min(y))) / (Q_max**2)
            else:
                raise ValueError("流量Q最大值为0，无法估计K参数")

        # 参数边界（基于初始估计动态计算，非硬编码）
        bounds = (
            [0.0, 0.0],  # 下界: H0 > 0, K > 0
            [H0_init * 2, K_init * 10],  # 上界: 基于初始值
        )

        try:
            popt, _ = curve_fit(
                self._pump_curve,
                X,
                y,
                p0=[H0_init, K_init],
                bounds=bounds,
                maxfev=5000,
            )

            H0, K = popt

            # 计算预测值
            y_pred = self._pump_curve(X, H0, K)

            # 计算指标（复用基类方法）
            metrics = self._calculate_metrics(y, y_pred)

            # 验证物理约束
            physics_valid = H0 > 0 and K > 0

            # 创建预测函数
            def predict_func(x: np.ndarray) -> np.ndarray:
                x = np.atleast_1d(x)
                return H0 - K * x**2

            return MethodResult(
                method_id=self.method_id,
                coefficients={"H0": float(H0), "K": float(K)},
                r_squared=metrics["r_squared"],
                rmse=metrics["rmse"],
                mae=metrics["mae"],
                mape=metrics["mape"],
                predict_func=predict_func,
                formula=f"H = {H0:.4f} - {K:.6f} × Q²",
                metadata={
                    "physics_valid": physics_valid,
                    "quality_grade": self._get_quality_grade(metrics["r_squared"]),
                },
            )

        except (RuntimeError, ValueError) as e:
            self._logger.warning(f"泵特性方程拟合失败: {e}")
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
        """使用拟合参数进行预测

        Args:
            X: 流量数组
            params: 拟合参数，必须包含 'H0' 和 'K'

        Returns:
            预测的扬程数组
        """
        H0 = params["H0"]
        K = params["K"]
        return H0 - K * np.atleast_1d(X) ** 2


def register_pump_char_methods() -> None:
    """注册泵特性方程方法到 MethodRegistry"""
    from app.services.characteristic_curves.methods.method_registry import MethodRegistry

    registry = MethodRegistry()

    # 泵特性方程仅适用于 Q-H 曲线
    registry.register(
        curve_type="qh",
        method_id="physics_pump_char",
        method_name="泵特性方程",
        method_class=PhysicsPumpCharMethod,
        priority=100,  # 最高优先级
        description="泵特性方程：H = H0 - K×Q²，物理模型，Q-H曲线专用",
        dependencies=None,
        applicable_conditions={"min_data_points": 10, "curve_type": "qh"},
    )

