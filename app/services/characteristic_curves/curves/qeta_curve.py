"""
Q-η曲线处理器 (app.services.characteristic_curves.curves.qeta_curve)

流量-效率曲线的专用处理器。

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/04_曲线模块/03_QEta曲线.md

物理特性:
- 单调性: 单峰 (先增后减)
- 效率范围: η ∈ [0, 100%]
- 最佳效率点: BEP (Best Efficiency Point)
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from app.services.characteristic_curves.curves.base_curve import (
    BaseCurve,
    CurveType,
    FitResult,
    MonotonicityType,
)


class QEtaCurve(BaseCurve):
    """Q-η曲线处理器

    流量-效率曲线，物理约束为单峰特性。

    使用方式:
        curve = QEtaCurve()
        result = curve.fit(Q_values, eta_values)
    """

    curve_type = CurveType.QETA
    monotonicity = MonotonicityType.UNIMODAL
    recommended_methods = ["math_stat_gaussian", "math_poly_3", "math_poly_4"]

    def __init__(self) -> None:
        """初始化Q-η曲线处理器"""
        super().__init__()

    def _init_submodules(self) -> None:
        """初始化子模块"""
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def extract_data(
        self, device_id: int, start_time: datetime, end_time: datetime
    ) -> pd.DataFrame:
        """提取Q-η数据"""
        self._logger.info(f"提取Q-η数据: device_id={device_id}")
        return pd.DataFrame(columns=["Q", "eta"])

    def preprocess(self, data: pd.DataFrame) -> pd.DataFrame:
        """预处理Q-η数据"""
        if data.empty:
            return data
        clean = data.dropna(subset=["Q", "eta"])
        # 效率范围约束
        clean = clean[(clean["Q"] >= 0) & (clean["eta"] >= 0) & (clean["eta"] <= 100)]
        return clean

    def calculate_constraints(
        self, data: pd.DataFrame, device_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """计算Q-η曲线约束"""
        constraints = self.get_default_constraints()
        constraints.update({
            "monotonicity_type": "unimodal",
            "min_eta": 0,
            "max_eta": 100,
            "min_Q": 0,
            "max_Q": device_params.get("Q_rated", 300) * 1.2,
            "eta_rated": device_params.get("eta_rated", 80),
        })
        return constraints

    def _do_fit(
        self, x_values: np.ndarray, y_values: np.ndarray, method_id: str, **kwargs: Any
    ) -> FitResult:
        """执行Q-η曲线拟合

        使用高斯型或多项式: η = η_max * exp(-((Q-Q_bep)/σ)²)
        或三次多项式
        """
        try:
            # 使用三次多项式拟合单峰曲线
            degree = kwargs.get("degree", 3)
            coeffs = np.polyfit(x_values, y_values, degree)

            y_fitted = np.polyval(coeffs, x_values)

            # 限制拟合值在[0, 100]范围
            y_fitted = np.clip(y_fitted, 0, 100)

            # 计算R²
            ss_res = np.sum((y_values - y_fitted) ** 2)
            ss_tot = np.sum((y_values - np.mean(y_values)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

            rmse = np.sqrt(np.mean((y_values - y_fitted) ** 2))

            # 检查单峰约束：应有且仅有一个极大值点
            dydx = np.diff(y_fitted)
            sign_changes = np.sum(np.diff(np.sign(dydx)) != 0)
            constraints_satisfied = sign_changes == 1  # 应有一个极值点

            # 找到最佳效率点
            bep_idx = np.argmax(y_fitted)
            q_bep = x_values[bep_idx]
            eta_max = y_fitted[bep_idx]

            formula = self._generate_formula(coeffs)

            if r_squared >= 0.98:
                quality_grade = "excellent"
            elif r_squared >= 0.95:
                quality_grade = "good"
            elif r_squared >= 0.90:
                quality_grade = "acceptable"
            else:
                quality_grade = "poor"

            return FitResult(
                success=True,
                curve_type=self.curve_type.value,
                method_id=method_id,
                coefficients=coeffs.tolist(),
                formula=formula,
                r_squared=r_squared,
                rmse=rmse,
                quality_grade=quality_grade,
                x_values=x_values,
                y_fitted=y_fitted,
                constraints_satisfied=constraints_satisfied,
                metadata={"Q_bep": float(q_bep), "eta_max": float(eta_max)},
            )

        except Exception as e:
            self._logger.error(f"Q-η曲线拟合失败: {e}")
            return FitResult(
                success=False,
                curve_type=self.curve_type.value,
                method_id=method_id,
                metadata={"error": str(e)},
            )

    def _generate_formula(self, coeffs: np.ndarray) -> str:
        """生成公式字符串"""
        degree = len(coeffs) - 1
        terms = []
        for i, c in enumerate(coeffs):
            power = degree - i
            if power == 0:
                terms.append(f"{c:.4f}")
            elif power == 1:
                terms.append(f"{c:.4f}*Q")
            else:
                terms.append(f"{c:.6f}*Q^{power}")
        return "η = " + " + ".join(terms)

