"""
约束验证器 (app.services.characteristic_curves.constraints.constraint_validator)

组合多个约束进行验证。

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/03_核心模块/04_约束层.md
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from app.services.characteristic_curves.constraints.base_constraint import (
    BaseConstraint,
    ConstraintResult,
)
from app.services.characteristic_curves.constraints.boundary_constraint import (
    BoundaryConstraint,
)
from app.services.characteristic_curves.constraints.monotonicity_constraint import (
    MonotonicityConstraint,
)


@dataclass
class CombinedValidationResult:
    """组合验证结果

    Attributes:
        overall_valid: 总体是否通过
        results: 各约束验证结果
        failed_constraints: 失败的约束类型列表
        total_violation_ratio: 总违反比例
    """

    overall_valid: bool
    results: Dict[str, ConstraintResult] = field(default_factory=dict)
    failed_constraints: List[str] = field(default_factory=list)
    total_violation_ratio: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "overall_valid": self.overall_valid,
            "results": {k: v.to_dict() for k, v in self.results.items()},
            "failed_constraints": self.failed_constraints,
            "total_violation_ratio": self.total_violation_ratio,
        }


class ConstraintValidator:
    """约束验证器（组合多个约束）

    组合MonotonicityConstraint和BoundaryConstraint进行验证。

    Attributes:
        constraints: 约束列表
    """

    def __init__(self, constraints: Optional[List[BaseConstraint]] = None) -> None:
        """初始化约束验证器

        Args:
            constraints: 约束列表，如果为None则使用默认约束
        """
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.constraints = constraints or [
            MonotonicityConstraint(),
            BoundaryConstraint(),
        ]

    def add_constraint(self, constraint: BaseConstraint) -> None:
        """添加约束"""
        self.constraints.append(constraint)

    def remove_constraint(self, constraint_type: str) -> bool:
        """移除指定类型的约束"""
        original_len = len(self.constraints)
        self.constraints = [
            c for c in self.constraints if c.constraint_type.value != constraint_type
        ]
        return len(self.constraints) < original_len

    def validate_all(
        self,
        curve_type: str,
        x_values: np.ndarray,
        y_values: np.ndarray,
        tolerance: float = 0.01,
        **kwargs: Any,
    ) -> CombinedValidationResult:
        """执行所有约束验证

        Args:
            curve_type: 曲线类型
            x_values: X轴值
            y_values: Y轴值
            tolerance: 容差
            **kwargs: 额外参数

        Returns:
            CombinedValidationResult: 组合验证结果
        """
        results: Dict[str, ConstraintResult] = {}
        failed_constraints: List[str] = []
        total_violations = 0.0

        for constraint in self.constraints:
            try:
                result = constraint.validate(
                    curve_type=curve_type,
                    x_values=x_values,
                    y_values=y_values,
                    tolerance=tolerance,
                    **kwargs,
                )
                constraint_name = constraint.constraint_type.value
                results[constraint_name] = result

                if not result.is_valid:
                    failed_constraints.append(constraint_name)

                total_violations += result.violation_ratio

            except Exception as e:
                self._logger.error(f"约束验证失败 {constraint.constraint_name}: {e}")
                failed_constraints.append(constraint.constraint_type.value)

        overall_valid = len(failed_constraints) == 0
        avg_violation = total_violations / len(self.constraints) if self.constraints else 0

        return CombinedValidationResult(
            overall_valid=overall_valid,
            results=results,
            failed_constraints=failed_constraints,
            total_violation_ratio=avg_violation,
        )

    def get_constraint_names(self) -> List[str]:
        """获取所有约束名称"""
        return [c.constraint_name for c in self.constraints]

