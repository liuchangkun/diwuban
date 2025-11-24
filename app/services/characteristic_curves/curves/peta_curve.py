"""
P-η曲线处理器 (app.services.characteristic_curves.curves.peta_curve)

功率-效率曲线的专用处理器。

版本: v1.0
更新日期: 2025-12-08

物理特性:
- 单调性: 单峰 (先增后减)
- 效率范围: η ∈ [0, 100%]
"""

import logging
from datetime import datetime
from typing import Any, Dict

import numpy as np
import pandas as pd

from app.services.characteristic_curves.curves.base_curve import (
    BaseCurve,
    CurveType,
    FitResult,
    MonotonicityType,
)


class PEtaCurve(BaseCurve):
    """P-η曲线处理器

    功率-效率曲线，物理约束为单峰特性。
    """

    curve_type = CurveType.PETA
    monotonicity = MonotonicityType.UNIMODAL
    recommended_methods = ["math_poly_3", "math_stat_gaussian"]

    def __init__(self) -> None:
        super().__init__()

    def _init_submodules(self) -> None:
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def extract_data(
        self, device_id: int, start_time: datetime, end_time: datetime
    ) -> pd.DataFrame:
        self._logger.info(f"提取P-η数据: device_id={device_id}")
        return pd.DataFrame(columns=["P", "eta"])

    def preprocess(self, data: pd.DataFrame) -> pd.DataFrame:
        if data.empty:
            return data
        clean = data.dropna(subset=["P", "eta"])
        clean = clean[(clean["P"] >= 0) & (clean["eta"] >= 0) & (clean["eta"] <= 100)]
        return clean

    def calculate_constraints(
        self, data: pd.DataFrame, device_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        constraints = self.get_default_constraints()
        constraints.update({
            "monotonicity_type": "unimodal",
            "min_eta": 0,
            "max_eta": 100,
        })
        return constraints

    def _do_fit(
        self, x_values: np.ndarray, y_values: np.ndarray, method_id: str, **kwargs: Any
    ) -> FitResult:
        try:
            degree = kwargs.get("degree", 3)
            coeffs = np.polyfit(x_values, y_values, degree)
            y_fitted = np.clip(np.polyval(coeffs, x_values), 0, 100)

            ss_res = np.sum((y_values - y_fitted) ** 2)
            ss_tot = np.sum((y_values - np.mean(y_values)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            rmse = np.sqrt(np.mean((y_values - y_fitted) ** 2))

            dydx = np.diff(y_fitted)
            sign_changes = np.sum(np.diff(np.sign(dydx)) != 0)
            constraints_satisfied = sign_changes == 1

            quality_grade = "excellent" if r_squared >= 0.98 else "good" if r_squared >= 0.95 else "acceptable" if r_squared >= 0.90 else "poor"

            return FitResult(
                success=True,
                curve_type=self.curve_type.value,
                method_id=method_id,
                coefficients=coeffs.tolist(),
                formula=f"η = poly{degree}(P)",
                r_squared=r_squared,
                rmse=rmse,
                quality_grade=quality_grade,
                x_values=x_values,
                y_fitted=y_fitted,
                constraints_satisfied=constraints_satisfied,
            )
        except Exception as e:
            self._logger.error(f"P-η曲线拟合失败: {e}")
            return FitResult(
                success=False,
                curve_type=self.curve_type.value,
                method_id=method_id,
                metadata={"error": str(e)},
            )

