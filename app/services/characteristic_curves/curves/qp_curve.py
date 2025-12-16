"""
Q-P曲线处理器 (app.services.characteristic_curves.curves.qp_curve)

流量-功率曲线的专用处理器。

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/04_曲线模块/02_QP曲线.md

物理特性:
- 单调性: 全范围单调递增 (dP/dQ > 0)
- 零流量点: P₀ > 0 (空载功率)
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from app.services.characteristic_curves.curves.base_curve import (
    BaseCurve,
    CurveType,
    FitResult,
    MonotonicityType,
)


class QPCurve(BaseCurve):
    """Q-P曲线处理器

    流量-功率曲线，物理约束为单调递增。

    使用方式:
        curve = QPCurve()
        result = curve.fit(Q_values, P_values)
    """

    curve_type = CurveType.QP
    monotonicity = MonotonicityType.INCREASING
    recommended_methods = ["physics_power_eq", "math_poly_2", "math_poly_3"]

    def __init__(self) -> None:
        """初始化Q-P曲线处理器"""
        super().__init__()

    def _init_submodules(self) -> None:
        """初始化子模块"""
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def extract_data(
        self, device_id: int, start_time: datetime, end_time: datetime
    ) -> pd.DataFrame:
        """提取Q-P数据"""
        self._logger.info(f"提取Q-P数据: device_id={device_id}")
        return pd.DataFrame(columns=["Q", "P"])

    def preprocess(self, data: pd.DataFrame) -> pd.DataFrame:
        """预处理Q-P数据"""
        if data.empty:
            return data
        clean = data.dropna(subset=["Q", "P"])
        clean = clean[(clean["Q"] >= 0) & (clean["P"] >= 0)]
        return clean

    def calculate_constraints(
        self, data: pd.DataFrame, device_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """计算Q-P曲线约束"""
        constraints = self.get_default_constraints()
        constraints.update({
            "monotonicity_direction": "increasing",
            "min_P": 0,
            "max_P": device_params.get("P_rated", 100) * 1.5,
            "min_Q": 0,
            "max_Q": device_params.get("Q_rated", 300) * 1.2,
        })
        return constraints

    def _do_fit(
        self, x_values: np.ndarray, y_values: np.ndarray, method_id: str, **kwargs: Any
    ) -> FitResult:
        """执行Q-P曲线拟合

        使用二次多项式: P = a₀ + a₁Q + a₂Q²
        约束: a₂ > 0 且 a₁ > 0 (保证递增)
        """
        try:
            degree = kwargs.get("degree", 2)
            coeffs = np.polyfit(x_values, y_values, degree)

            y_fitted = np.polyval(coeffs, x_values)

            # 计算R²
            ss_res = np.sum((y_values - y_fitted) ** 2)
            ss_tot = np.sum((y_values - np.mean(y_values)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

            rmse = np.sqrt(np.mean((y_values - y_fitted) ** 2))

            # 检查单调递增约束
            if degree >= 2:
                # 二次多项式，检查在数据范围内是否递增
                # dP/dQ = 2*a₂*Q + a₁ > 0 for all Q in range
                a2, a1 = coeffs[0], coeffs[1]
                q_min, q_max = x_values.min(), x_values.max()
                derivative_at_min = 2 * a2 * q_min + a1
                constraints_satisfied = derivative_at_min > 0 and a2 > 0
            else:
                constraints_satisfied = coeffs[0] > 0

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
            )

        except Exception as e:
            self._logger.error(f"Q-P曲线拟合失败: {e}")
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
        return "P = " + " + ".join(terms)

