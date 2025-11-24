"""
边界约束 (app.services.characteristic_curves.constraints.boundary_constraint)

验证和修正曲线的边界条件约束。

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/03_核心模块/04_约束层.md 第2节
"""

from typing import Any, Dict, List

import numpy as np

from app.services.characteristic_curves.constraints.base_constraint import (
    BaseConstraint,
    ConstraintResult,
    ConstraintType,
)


class BoundaryConstraint(BaseConstraint):
    """边界约束验证器

    验证边界条件:
        - Q-H: H₀ ≈ 1.1~1.3 × H_rated, H ≥ 0
        - Q-P: P₀ ≈ 0.3~0.5 × P_rated, P > 0
        - Q-η: η₀ = 0, 0 ≤ η ≤ 1

    Attributes:
        constraint_type: BOUNDARY
        constraint_name: 边界约束
    """

    constraint_type = ConstraintType.BOUNDARY
    constraint_name = "边界约束"

    def validate(
        self,
        curve_type: str,
        x_values: np.ndarray,
        y_values: np.ndarray,
        tolerance: float = 0.05,
        **kwargs: Any,
    ) -> ConstraintResult:
        """验证边界约束

        Args:
            curve_type: 曲线类型
            x_values: X轴值
            y_values: Y轴值
            tolerance: 容差
            **kwargs: 需包含 device_params (设备额定参数)

        Returns:
            ConstraintResult: 验证结果
        """
        self._validate_input(x_values, y_values)
        device_params = kwargs.get("device_params", {})

        checks: List[Dict[str, Any]] = []
        violations: List[str] = []

        if curve_type == "qh":
            checks, violations = self._validate_qh_boundary(
                x_values, y_values, device_params, tolerance
            )
        elif curve_type == "qp":
            checks, violations = self._validate_qp_boundary(
                x_values, y_values, device_params, tolerance
            )
        elif curve_type == "qeta":
            checks, violations = self._validate_qeta_boundary(
                x_values, y_values, tolerance
            )
        else:
            raise ValueError(f"不支持的曲线类型: {curve_type}")

        is_valid = len(violations) == 0
        violation_ratio = len(violations) / max(len(checks), 1)

        return ConstraintResult(
            is_valid=is_valid,
            constraint_type=self.constraint_type,
            violation_ratio=violation_ratio,
            violation_points=[],
            details={"boundary_checks": checks, "violations": violations},
            message="边界验证通过" if is_valid else f"边界违反: {', '.join(violations)}",
        )

    def _validate_qh_boundary(
        self,
        x_values: np.ndarray,
        y_values: np.ndarray,
        device_params: Dict[str, float],
        tolerance: float,
    ) -> tuple:
        """验证Q-H曲线边界"""
        checks = []
        violations = []

        # 值域范围检查: H ≥ 0
        min_h = float(np.min(y_values))
        h_valid = min_h >= -tolerance
        checks.append({"name": "H≥0", "actual": min_h, "expected": "≥0", "passed": h_valid})
        if not h_valid:
            violations.append(f"扬程存在负值: {min_h:.2f}")

        # 零流量点检查 (如果有设备参数)
        if device_params.get("rated_head"):
            rated_head = device_params["rated_head"]
            # 找到最小流量点的扬程
            min_q_idx = int(np.argmin(x_values))
            h0 = float(y_values[min_q_idx])
            h0_min = 1.1 * rated_head
            h0_max = 1.3 * rated_head
            h0_valid = h0_min <= h0 <= h0_max
            checks.append({
                "name": "零流量扬程",
                "actual": h0,
                "expected": f"[{h0_min:.1f}, {h0_max:.1f}]",
                "passed": h0_valid,
            })
            if not h0_valid:
                violations.append(f"H₀={h0:.1f} 超出范围")

        return checks, violations

    def _validate_qp_boundary(
        self,
        x_values: np.ndarray,
        y_values: np.ndarray,
        device_params: Dict[str, float],
        tolerance: float,
    ) -> tuple:
        """验证Q-P曲线边界"""
        checks = []
        violations = []

        # 值域范围检查: P > 0
        min_p = float(np.min(y_values))
        p_valid = min_p > -tolerance
        checks.append({"name": "P>0", "actual": min_p, "expected": ">0", "passed": p_valid})
        if not p_valid:
            violations.append(f"功率存在负值: {min_p:.2f}")

        return checks, violations

    def _validate_qeta_boundary(
        self, x_values: np.ndarray, y_values: np.ndarray, tolerance: float
    ) -> tuple:
        """验证Q-η曲线边界"""
        checks = []
        violations = []

        # 效率范围: 0 ≤ η ≤ 1
        min_eta = float(np.min(y_values))
        max_eta = float(np.max(y_values))
        range_valid = min_eta >= -tolerance and max_eta <= 1.0 + tolerance
        checks.append({
            "name": "η∈[0,1]",
            "actual": f"[{min_eta:.3f}, {max_eta:.3f}]",
            "expected": "[0, 1]",
            "passed": range_valid,
        })
        if not range_valid:
            violations.append(f"效率超出范围: [{min_eta:.3f}, {max_eta:.3f}]")

        return checks, violations

    def apply(
        self, curve_type: str, x_values: np.ndarray, y_values: np.ndarray, **kwargs: Any
    ) -> np.ndarray:
        """应用边界修正（裁剪到有效范围）"""
        self._validate_input(x_values, y_values)

        if curve_type == "qh":
            return np.maximum(y_values, 0)
        elif curve_type == "qp":
            return np.maximum(y_values, 0)
        elif curve_type == "qeta":
            return np.clip(y_values, 0, 1)
        else:
            return y_values.copy()

