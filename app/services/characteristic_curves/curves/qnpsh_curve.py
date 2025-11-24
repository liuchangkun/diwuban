"""
Q-NPSH曲线处理器 (app.services.characteristic_curves.curves.qnpsh_curve)

流量-汽蚀余量曲线的专用处理器。

版本: v1.0
更新日期: 2025-12-08

物理特性:
- 单调性: 一般为递增 (流量增加时汽蚀余量需求增加)
- NPSH范围: NPSHr > 0
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


class QNPSHCurve(BaseCurve):
    """Q-NPSH曲线处理器

    流量-汽蚀余量曲线，物理约束为递增特性。
    """

    curve_type = CurveType.QNPSH
    monotonicity = MonotonicityType.INCREASING
    recommended_methods = ["math_poly_2", "math_poly_3"]

    def __init__(self) -> None:
        super().__init__()

    def _init_submodules(self) -> None:
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def extract_data(
        self, device_id: int, start_time: datetime, end_time: datetime
    ) -> pd.DataFrame:
        self._logger.info(f"提取Q-NPSH数据: device_id={device_id}")
        return pd.DataFrame(columns=["Q", "NPSH"])

    def preprocess(self, data: pd.DataFrame) -> pd.DataFrame:
        if data.empty:
            return data
        clean = data.dropna(subset=["Q", "NPSH"])
        clean = clean[(clean["Q"] >= 0) & (clean["NPSH"] >= 0)]
        return clean

    def calculate_constraints(
        self, data: pd.DataFrame, device_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        constraints = self.get_default_constraints()
        constraints.update({
            "monotonicity_direction": "increasing",
            "min_NPSH": 0,
        })
        return constraints

    def _do_fit(
        self, x_values: np.ndarray, y_values: np.ndarray, method_id: str, **kwargs: Any
    ) -> FitResult:
        try:
            degree = kwargs.get("degree", 2)
            coeffs = np.polyfit(x_values, y_values, degree)
            y_fitted = np.polyval(coeffs, x_values)
            y_fitted = np.maximum(y_fitted, 0)

            ss_res = np.sum((y_values - y_fitted) ** 2)
            ss_tot = np.sum((y_values - np.mean(y_values)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            rmse = np.sqrt(np.mean((y_values - y_fitted) ** 2))

            # 检查递增约束
            dydx = np.diff(y_fitted)
            constraints_satisfied = np.all(dydx >= 0)

            quality_grade = "excellent" if r_squared >= 0.98 else "good" if r_squared >= 0.95 else "acceptable" if r_squared >= 0.90 else "poor"

            return FitResult(
                success=True,
                curve_type=self.curve_type.value,
                method_id=method_id,
                coefficients=coeffs.tolist(),
                formula=f"NPSH = poly{degree}(Q)",
                r_squared=r_squared,
                rmse=rmse,
                quality_grade=quality_grade,
                x_values=x_values,
                y_fitted=y_fitted,
                constraints_satisfied=constraints_satisfied,
            )
        except Exception as e:
            self._logger.error(f"Q-NPSH曲线拟合失败: {e}")
            return FitResult(
                success=False,
                curve_type=self.curve_type.value,
                method_id=method_id,
                metadata={"error": str(e)},
            )

