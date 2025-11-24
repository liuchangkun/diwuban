"""
单调性约束 (app.services.characteristic_curves.constraints.monotonicity_constraint)

验证和修正曲线的单调性约束。

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/03_核心模块/04_约束层.md 第1节
"""

from typing import Any

import numpy as np

from app.services.characteristic_curves.constraints.base_constraint import (
    BaseConstraint,
    ConstraintResult,
    ConstraintType,
)


class MonotonicityConstraint(BaseConstraint):
    """单调性约束验证器

    验证规则:
        - Q-H曲线: 单调递减 (流量增加，扬程下降)
        - Q-P曲线: 单调递增 (流量增加，功率增加)
        - Q-η曲线: 单峰 (先增后减，存在最高效率点)

    Attributes:
        constraint_type: MONOTONICITY
        constraint_name: 单调性约束
    """

    constraint_type = ConstraintType.MONOTONICITY
    constraint_name = "单调性约束"

    def validate(
        self,
        curve_type: str,
        x_values: np.ndarray,
        y_values: np.ndarray,
        tolerance: float = 0.01,
        **kwargs: Any,
    ) -> ConstraintResult:
        """验证单调性约束

        Args:
            curve_type: 曲线类型 ('qh', 'qp', 'qeta')
            x_values: X轴值（流量Q）
            y_values: Y轴值
            tolerance: 容差（相对于y值范围的比例）

        Returns:
            ConstraintResult: 验证结果
        """
        self._validate_input(x_values, y_values)

        if curve_type == "qh":
            return self._validate_decreasing(x_values, y_values, tolerance)
        elif curve_type == "qp":
            return self._validate_increasing(x_values, y_values, tolerance)
        elif curve_type == "qeta":
            return self._validate_unimodal(x_values, y_values, tolerance)
        else:
            raise ValueError(f"不支持的曲线类型: {curve_type}")

    def _validate_decreasing(
        self, x_values: np.ndarray, y_values: np.ndarray, tolerance: float
    ) -> ConstraintResult:
        """验证单调递减（Q-H曲线）"""
        diff = np.diff(y_values)
        y_range = np.max(y_values) - np.min(y_values)
        threshold = tolerance * y_range if y_range > 0 else tolerance

        violation_mask = diff > threshold
        violation_points = np.where(violation_mask)[0].tolist()
        violation_ratio = len(violation_points) / len(diff) if len(diff) > 0 else 0

        return ConstraintResult(
            is_valid=len(violation_points) == 0,
            constraint_type=self.constraint_type,
            violation_ratio=violation_ratio,
            violation_points=violation_points,
            details={"expected": "decreasing", "threshold": threshold},
            message="Q-H曲线应单调递减" if violation_points else "单调递减验证通过",
        )

    def _validate_increasing(
        self, x_values: np.ndarray, y_values: np.ndarray, tolerance: float
    ) -> ConstraintResult:
        """验证单调递增（Q-P曲线）"""
        diff = np.diff(y_values)
        y_range = np.max(y_values) - np.min(y_values)
        threshold = tolerance * y_range if y_range > 0 else tolerance

        violation_mask = diff < -threshold
        violation_points = np.where(violation_mask)[0].tolist()
        violation_ratio = len(violation_points) / len(diff) if len(diff) > 0 else 0

        return ConstraintResult(
            is_valid=len(violation_points) == 0,
            constraint_type=self.constraint_type,
            violation_ratio=violation_ratio,
            violation_points=violation_points,
            details={"expected": "increasing", "threshold": threshold},
            message="Q-P曲线应单调递增" if violation_points else "单调递增验证通过",
        )

    def _validate_unimodal(
        self, x_values: np.ndarray, y_values: np.ndarray, tolerance: float
    ) -> ConstraintResult:
        """验证单峰（Q-η曲线）"""
        peak_idx = int(np.argmax(y_values))
        peak_x = float(x_values[peak_idx])
        peak_y = float(y_values[peak_idx])

        left_result = self._validate_increasing(
            x_values[: peak_idx + 1], y_values[: peak_idx + 1], tolerance
        )
        right_result = self._validate_decreasing(
            x_values[peak_idx:], y_values[peak_idx:], tolerance
        )

        violation_points = left_result.violation_points + [
            p + peak_idx for p in right_result.violation_points
        ]
        avg_ratio = (left_result.violation_ratio + right_result.violation_ratio) / 2

        return ConstraintResult(
            is_valid=left_result.is_valid and right_result.is_valid,
            constraint_type=self.constraint_type,
            violation_ratio=avg_ratio,
            violation_points=violation_points,
            details={"expected": "unimodal", "peak_x": peak_x, "peak_y": peak_y},
            message="Q-η曲线应为单峰" if violation_points else "单峰验证通过",
        )

    def apply(
        self, curve_type: str, x_values: np.ndarray, y_values: np.ndarray, **kwargs: Any
    ) -> np.ndarray:
        """应用单调性修正"""
        self._validate_input(x_values, y_values)
        y_corrected = y_values.copy()

        if curve_type == "qh":
            for i in range(1, len(y_corrected)):
                if y_corrected[i] > y_corrected[i - 1]:
                    y_corrected[i] = y_corrected[i - 1]
        elif curve_type == "qp":
            for i in range(1, len(y_corrected)):
                if y_corrected[i] < y_corrected[i - 1]:
                    y_corrected[i] = y_corrected[i - 1]
        elif curve_type == "qeta":
            peak_idx = int(np.argmax(y_corrected))
            for i in range(1, peak_idx + 1):
                if y_corrected[i] < y_corrected[i - 1]:
                    y_corrected[i] = y_corrected[i - 1]
            for i in range(peak_idx + 1, len(y_corrected)):
                if y_corrected[i] > y_corrected[i - 1]:
                    y_corrected[i] = y_corrected[i - 1]

        return y_corrected

