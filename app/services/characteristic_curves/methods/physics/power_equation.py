"""
功率方程拟合方法 (app.services.characteristic_curves.methods.physics.power_equation)

本模块实现功率方程拟合方法：
- PhysicsPowerEqMethod: 功率方程 (physics_power_eq)

物理公式: P = P0 + K × Q^n
适用曲线: Q-P 专用
优先级: 100 (最高)

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/05_拟合方法/02_物理模型.md
"""

from typing import Any, Dict, Optional

import numpy as np
from scipy.optimize import curve_fit

from app.services.characteristic_curves.methods.base_method import BaseMethod
from app.services.characteristic_curves.models import MethodResult


class PhysicsPowerEqMethod(BaseMethod):
    """功率方程拟合方法

    物理公式:
        P = P0 + K × Q^n

    物理意义:
        P0: 空载功率
        K: 功率系数
        n: 指数（通常为1-2）

    物理约束:
        - P0 > 0 (空载功率为正)
        - K > 0 (功率系数为正)
        - 0.5 < n < 3 (指数在合理范围)
        - dP/dQ > 0 (单调递增)

    适用曲线: Q-P 专用
    优先级: 100 (最高)
    """

    def __init__(self) -> None:
        """初始化功率方程方法"""
        super().__init__(method_name="功率方程", method_id="physics_power_eq")

    @staticmethod
    def _power_curve(Q: np.ndarray, P0: float, K: float, n: float) -> np.ndarray:
        """功率方程: P = P0 + K × Q^n"""
        return P0 + K * np.power(Q, n)

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        constraints: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> MethodResult:
        """执行功率方程拟合

        Args:
            X: 流量数组（Q）
            y: 功率数组（P）
            constraints: 物理约束参数，可包含 'P0', 'K', 'n' 的初始估计
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
            raise ValueError("功率P不能为负值")

        constraints = constraints or {}

        # 从约束参数获取初始猜测（禁止硬编码默认值）
        if "P0" in constraints:
            P0_init = constraints["P0"]
            if P0_init < 0:
                raise ValueError(f"约束参数P0不能为负，当前值: {P0_init}")
        else:
            # 基于数据估计（从数据推断，非硬编码）
            P0_init = float(np.min(y)) * 0.8  # 略低于最小功率

        if "n" in constraints:
            n_init = constraints["n"]
            if n_init <= 0:
                raise ValueError(f"约束参数n必须大于0，当前值: {n_init}")
        else:
            # 典型泵功率指数范围1-2
            n_init = 1.5

        if "K" in constraints:
            K_init = constraints["K"]
            if K_init <= 0:
                raise ValueError(f"约束参数K必须大于0，当前值: {K_init}")
        else:
            # 基于数据估计
            Q_max = float(np.max(X))
            P_max = float(np.max(y))
            if Q_max > 0:
                K_init = (P_max - P0_init) / np.power(Q_max, n_init)
            else:
                raise ValueError("流量Q最大值为0，无法估计K参数")

        # 参数边界（基于数据和初始估计动态计算，非硬编码）
        P_max = float(np.max(y))
        bounds = (
            [0.0, 0.0, 0.5],  # 下界: P0 >= 0, K > 0, n > 0.5
            [P_max, K_init * 10, 3.0],  # 上界: 基于数据
        )

        try:
            popt, _ = curve_fit(
                self._power_curve,
                X,
                y,
                p0=[P0_init, K_init, n_init],
                bounds=bounds,
                maxfev=5000,
            )

            P0, K, n = popt

            # 计算预测值
            y_pred = self._power_curve(X, P0, K, n)

            # 计算指标（复用基类方法）
            metrics = self._calculate_metrics(y, y_pred)

            # 验证物理约束
            physics_valid = P0 >= 0 and K > 0 and 0.5 < n < 3

            # 创建预测函数
            def predict_func(x: np.ndarray) -> np.ndarray:
                x = np.atleast_1d(x)
                return P0 + K * np.power(x, n)

            return MethodResult(
                method_id=self.method_id,
                coefficients={"P0": float(P0), "K": float(K), "n": float(n)},
                r_squared=metrics["r_squared"],
                rmse=metrics["rmse"],
                mae=metrics["mae"],
                mape=metrics["mape"],
                predict_func=predict_func,
                formula=f"P = {P0:.4f} + {K:.6f} × Q^{n:.2f}",
                metadata={
                    "physics_valid": physics_valid,
                    "quality_grade": self._get_quality_grade(metrics["r_squared"]),
                },
            )

        except (RuntimeError, ValueError) as e:
            self._logger.warning(f"功率方程拟合失败: {e}")
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
            params: 拟合参数，必须包含 'P0', 'K', 'n'

        Returns:
            预测的功率数组
        """
        P0 = params["P0"]
        K = params["K"]
        n = params["n"]
        return P0 + K * np.power(np.atleast_1d(X), n)


def register_power_eq_methods() -> None:
    """注册功率方程方法到 MethodRegistry"""
    from app.services.characteristic_curves.methods.method_registry import MethodRegistry

    registry = MethodRegistry()

    # 功率方程仅适用于 Q-P 曲线
    registry.register(
        curve_type="qp",
        method_id="physics_power_eq",
        method_name="功率方程",
        method_class=PhysicsPowerEqMethod,
        priority=100,  # 最高优先级
        description="功率方程：P = P0 + K×Q^n，物理模型，Q-P曲线专用",
        dependencies=None,
        applicable_conditions={"min_data_points": 10, "curve_type": "qp"},
    )

