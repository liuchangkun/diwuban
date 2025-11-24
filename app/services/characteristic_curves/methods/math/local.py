"""
局部拟合方法 (app.services.characteristic_curves.methods.math.local)

本模块实现局部类拟合方法：
- MathLocalLowessMethod: 局部加权回归 (math_local_lowess)

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/05_拟合方法/01_数学方法.md
"""

from typing import Any, Dict, Optional

import numpy as np
from scipy.interpolate import interp1d
from statsmodels.nonparametric.smoothers_lowess import lowess

from app.services.characteristic_curves.methods.base_method import BaseMethod
from app.services.characteristic_curves.models import MethodResult


class MathLocalLowessMethod(BaseMethod):
    """局部加权回归(LOWESS)拟合方法

    算法原理:
        LOWESS (Locally Weighted Scatterplot Smoothing)
        在每个点使用加权最小二乘进行局部拟合
        权重由三次权重函数确定: w(u) = (1 - |u|³)³

    优点:
        - 非参数方法，不需要假设函数形式
        - 对异常值鲁棒
        - 自动适应数据的局部特征

    适用曲线: 所有 (qh, qp, qeta)
    """

    def __init__(self, frac: float = 0.3, it: int = 3) -> None:
        """初始化LOWESS方法

        Args:
            frac: 用于估计每个点的数据比例 (0, 1]
            it: 鲁棒迭代次数
        """
        super().__init__(method_name="局部加权回归", method_id="math_local_lowess")
        self.frac = frac
        self.it = it
        self._interp: Optional[interp1d] = None
        self._smoothed: Optional[np.ndarray] = None

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        constraints: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> MethodResult:
        """执行LOWESS拟合

        Args:
            X: 自变量数组（流量Q）
            y: 因变量数组
            constraints: 物理约束参数（可选）
            **kwargs: 其他参数

        Returns:
            MethodResult: 拟合结果
        """
        # 执行LOWESS平滑
        self._smoothed = lowess(y, X, frac=self.frac, it=self.it, return_sorted=True)

        # 提取平滑后的值
        X_smooth = self._smoothed[:, 0]
        y_smooth = self._smoothed[:, 1]

        # 使用插值创建预测函数（用于预测新点）
        self._interp = interp1d(X_smooth, y_smooth, kind="linear", fill_value="extrapolate")

        # 计算预测值
        y_pred = self._interp(X)

        # 计算指标
        metrics = self._calculate_metrics(y, y_pred)

        # 创建预测函数
        interp_func = self._interp

        def predict_func(x: np.ndarray) -> np.ndarray:
            x = np.atleast_1d(x)
            return interp_func(x)

        return MethodResult(
            method_id=self.method_id,
            coefficients={"frac": self.frac, "it": self.it, "n_points": len(X_smooth)},
            r_squared=metrics["r_squared"],
            rmse=metrics["rmse"],
            mae=metrics["mae"],
            mape=metrics["mape"],
            predict_func=predict_func,
            formula=f"LOWESS (frac={self.frac}, it={self.it})",
            metadata={
                "frac": self.frac,
                "it": self.it,
                "quality_grade": self._get_quality_grade(metrics["r_squared"]),
            },
        )

    def predict(self, X: np.ndarray, params: Dict[str, float]) -> np.ndarray:
        """使用拟合参数进行预测（需要先调用fit）"""
        if self._interp is None:
            raise RuntimeError("必须先调用fit()")
        return self._interp(X)


def register_local_methods() -> None:
    """注册局部方法到 MethodRegistry"""
    from app.services.characteristic_curves.methods.method_registry import MethodRegistry

    registry = MethodRegistry()

    # 注册 MathLocalLowessMethod (适用于所有曲线)
    for curve_type in ["qh", "qp", "qeta"]:
        registry.register(
            curve_type=curve_type,
            method_id="math_local_lowess",
            method_name="局部加权回归",
            method_class=MathLocalLowessMethod,
            priority=65,
            description="LOWESS局部加权回归：非参数平滑方法",
            dependencies=None,
            applicable_conditions={"min_data_points": 50},
        )

