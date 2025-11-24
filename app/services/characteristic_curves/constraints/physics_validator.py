"""
物理验证器 (app.services.characteristic_curves.constraints.physics_validator)

综合验证拟合结果的物理合理性。

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/03_核心模块/04_约束层.md 第3节
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from app.services.characteristic_curves.constraints.base_constraint import (
    ConstraintResult,
)
from app.services.characteristic_curves.constraints.boundary_constraint import (
    BoundaryConstraint,
)
from app.services.characteristic_curves.constraints.monotonicity_constraint import (
    MonotonicityConstraint,
)


@dataclass
class ValidationResult:
    """综合验证结果

    Attributes:
        overall_passed: 总体是否通过
        monotonicity_passed: 单调性是否通过
        boundary_passed: 边界是否通过
        physics_score: 物理得分 (0-100)
        monotonicity_details: 单调性验证详情
        boundary_details: 边界验证详情
        suggestions: 修复建议
    """

    overall_passed: bool
    monotonicity_passed: bool
    boundary_passed: bool
    physics_score: float
    monotonicity_details: Dict[str, Any] = field(default_factory=dict)
    boundary_details: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "overall_passed": self.overall_passed,
            "monotonicity_passed": self.monotonicity_passed,
            "boundary_passed": self.boundary_passed,
            "physics_score": self.physics_score,
            "monotonicity_details": self.monotonicity_details,
            "boundary_details": self.boundary_details,
            "suggestions": self.suggestions,
        }


class PhysicsValidator:
    """物理验证器（组合多种约束）

    评分规则:
        - 单调性权重: 40%
        - 边界条件权重: 60%

    Attributes:
        _monotonicity: 单调性约束验证器
        _boundary: 边界约束验证器
    """

    def __init__(self) -> None:
        """初始化物理验证器"""
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._monotonicity = MonotonicityConstraint()
        self._boundary = BoundaryConstraint()

    def validate(
        self,
        curve_type: str,
        x_values: np.ndarray,
        y_values: np.ndarray,
        device_params: Optional[Dict[str, float]] = None,
        tolerance: float = 0.01,
    ) -> ValidationResult:
        """执行完整物理验证

        Args:
            curve_type: 曲线类型
            x_values: X轴值
            y_values: Y轴值（拟合值）
            device_params: 设备额定参数
            tolerance: 容差

        Returns:
            ValidationResult: 综合验证结果
        """
        device_params = device_params or {}

        # 单调性验证
        mono_result = self._monotonicity.validate(
            curve_type=curve_type,
            x_values=x_values,
            y_values=y_values,
            tolerance=tolerance,
        )

        # 边界验证
        bound_result = self._boundary.validate(
            curve_type=curve_type,
            x_values=x_values,
            y_values=y_values,
            tolerance=tolerance,
            device_params=device_params,
        )

        # 综合结果
        overall_passed = mono_result.is_valid and bound_result.is_valid
        physics_score = self._calculate_physics_score(mono_result, bound_result)
        suggestions = self._generate_suggestions(mono_result, bound_result)

        return ValidationResult(
            overall_passed=overall_passed,
            monotonicity_passed=mono_result.is_valid,
            boundary_passed=bound_result.is_valid,
            physics_score=physics_score,
            monotonicity_details=mono_result.to_dict(),
            boundary_details=bound_result.to_dict(),
            suggestions=suggestions,
        )

    def _calculate_physics_score(
        self, mono_result: ConstraintResult, bound_result: ConstraintResult
    ) -> float:
        """计算物理得分 (0-100)"""
        mono_score = 100 * (1 - mono_result.violation_ratio)

        checks = bound_result.details.get("boundary_checks", [])
        if checks:
            passed_count = sum(1 for c in checks if c.get("passed", False))
            bound_score = 100 * passed_count / len(checks)
        else:
            bound_score = 100 if bound_result.is_valid else 0

        return 0.4 * mono_score + 0.6 * bound_score

    def _generate_suggestions(
        self, mono_result: ConstraintResult, bound_result: ConstraintResult
    ) -> List[str]:
        """生成修复建议"""
        suggestions = []

        if not mono_result.is_valid:
            suggestions.append("单调性违反：考虑使用带单调性约束的拟合方法")
            suggestions.append("检查数据是否存在异常点或噪声")

        if not bound_result.is_valid:
            suggestions.append("边界条件违反：检查设备额定参数是否正确")
            suggestions.append("验证数据采集范围是否覆盖完整工况")

        return suggestions

    def check_efficiency_range(self, eta_values: np.ndarray) -> bool:
        """检查效率范围是否在 0-100%"""
        return bool(np.all(eta_values >= 0) and np.all(eta_values <= 1))

    def check_energy_conservation(
        self, Q: np.ndarray, H: np.ndarray, P: np.ndarray, eta: np.ndarray
    ) -> Dict[str, Any]:
        """检查能量守恒: η = ρgQH / P"""
        rho = 1000  # kg/m³
        g = 9.81  # m/s²
        Q_m3s = Q / 3600  # m³/h → m³/s
        P_w = P * 1000  # kW → W

        eta_calc = (rho * g * Q_m3s * H) / P_w
        deviation = np.abs(eta - eta_calc)
        max_dev = float(np.max(deviation))

        return {
            "is_valid": max_dev < 0.1,
            "max_deviation": max_dev,
            "mean_deviation": float(np.mean(deviation)),
        }

