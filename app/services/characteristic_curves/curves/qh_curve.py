"""
Q-H曲线处理器 (app.services.characteristic_curves.curves.qh_curve)

流量-扬程曲线的专用处理器。

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/04_曲线模块/01_QH曲线.md

物理特性:
- 单调性: 全范围单调递减 (dH/dQ < 0)
- 凸性: 下凸 (d²H/dQ² > 0)
- 零流量点: H₀ ≈ 1.1~1.3 × H_rated
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


class QHCurve(BaseCurve):
    """Q-H曲线处理器

    流量-扬程曲线，物理约束为单调递减。

    使用方式:
        curve = QHCurve()
        result = curve.fit(Q_values, H_values)
    """

    curve_type = CurveType.QH
    monotonicity = MonotonicityType.DECREASING
    recommended_methods = ["physics_pump_char", "math_poly_2", "math_poly_3"]

    def __init__(self) -> None:
        """初始化Q-H曲线处理器"""
        super().__init__()

    def _init_submodules(self) -> None:
        """初始化子模块"""
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def extract_data(
        self, device_id: int, start_time: datetime, end_time: datetime
    ) -> pd.DataFrame:
        """提取Q-H数据"""
        # 子类实际应用时从数据库提取
        self._logger.info(f"提取Q-H数据: device_id={device_id}")
        return pd.DataFrame(columns=["Q", "H"])

    def preprocess(self, data: pd.DataFrame) -> pd.DataFrame:
        """预处理Q-H数据"""
        if data.empty:
            return data
        # 去除无效值
        clean = data.dropna(subset=["Q", "H"])
        # 去除负值
        clean = clean[(clean["Q"] >= 0) & (clean["H"] >= 0)]
        return clean

    def calculate_constraints(
        self, data: pd.DataFrame, device_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """计算Q-H曲线约束"""
        constraints = self.get_default_constraints()
        constraints.update({
            "monotonicity_direction": "decreasing",
            "min_H": 0,
            "max_H": device_params.get("H_rated", 100) * 1.5,
            "min_Q": 0,
            "max_Q": device_params.get("Q_rated", 300) * 1.2,
        })
        return constraints

    def _do_fit(
        self, x_values: np.ndarray, y_values: np.ndarray, method_id: str, **kwargs: Any
    ) -> FitResult:
        """执行Q-H曲线拟合

        使用二次多项式: H = a₀ + a₁Q + a₂Q²
        约束: a₂ < 0 (保证递减)
        """
        try:
            # 默认使用二次多项式拟合
            degree = kwargs.get("degree", 2)
            coeffs = np.polyfit(x_values, y_values, degree)

            # 计算拟合值
            y_fitted = np.polyval(coeffs, x_values)

            # 计算R²
            ss_res = np.sum((y_values - y_fitted) ** 2)
            ss_tot = np.sum((y_values - np.mean(y_values)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

            # 计算RMSE
            rmse = np.sqrt(np.mean((y_values - y_fitted) ** 2))

            # 检查单调递减约束
            if degree >= 2:
                # 二次多项式a₂应为负数保证递减
                constraints_satisfied = coeffs[0] < 0  # 最高次系数
            else:
                constraints_satisfied = coeffs[0] < 0

            # 生成公式
            formula = self._generate_formula(coeffs)

            # 质量等级
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
            self._logger.error(f"Q-H曲线拟合失败: {e}")
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
        return "H = " + " + ".join(terms)

