"""
约束应用器 (app.services.characteristic_curves.constraints.constraint_applier)

按顺序应用多个约束修正曲线。

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
)
from app.services.characteristic_curves.constraints.boundary_constraint import (
    BoundaryConstraint,
)
from app.services.characteristic_curves.constraints.monotonicity_constraint import (
    MonotonicityConstraint,
)


@dataclass
class ApplyResult:
    """应用结果

    Attributes:
        original_values: 原始值
        corrected_values: 修正后的值
        applied_constraints: 已应用的约束列表
        corrections_log: 修正日志
        total_corrections: 总修正点数
    """

    original_values: np.ndarray
    corrected_values: np.ndarray
    applied_constraints: List[str] = field(default_factory=list)
    corrections_log: List[Dict[str, Any]] = field(default_factory=list)
    total_corrections: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "applied_constraints": self.applied_constraints,
            "corrections_log": self.corrections_log,
            "total_corrections": self.total_corrections,
            "max_correction": float(np.max(np.abs(self.corrected_values - self.original_values))),
        }


class ConstraintApplier:
    """约束应用器

    按顺序应用多个约束，修正曲线数据。

    Attributes:
        constraints: 约束列表（按应用顺序）
    """

    def __init__(self, constraints: Optional[List[BaseConstraint]] = None) -> None:
        """初始化约束应用器

        Args:
            constraints: 约束列表，如果为None则使用默认约束
        """
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        # 默认顺序：先边界约束，后单调性约束
        self.constraints = constraints or [
            BoundaryConstraint(),
            MonotonicityConstraint(),
        ]

    def add_constraint(self, constraint: BaseConstraint, position: int = -1) -> None:
        """添加约束到指定位置"""
        if position < 0:
            self.constraints.append(constraint)
        else:
            self.constraints.insert(position, constraint)

    def apply_all(
        self,
        curve_type: str,
        x_values: np.ndarray,
        y_values: np.ndarray,
        **kwargs: Any,
    ) -> ApplyResult:
        """按顺序应用所有约束

        Args:
            curve_type: 曲线类型
            x_values: X轴值
            y_values: Y轴值（将被修正）
            **kwargs: 额外参数

        Returns:
            ApplyResult: 应用结果
        """
        original = y_values.copy()
        current_values = y_values.copy()
        applied: List[str] = []
        logs: List[Dict[str, Any]] = []
        total_corrections = 0

        for constraint in self.constraints:
            try:
                before = current_values.copy()
                current_values = constraint.apply(
                    curve_type=curve_type,
                    x_values=x_values,
                    y_values=current_values,
                    **kwargs,
                )

                # 记录修正
                diff = np.abs(current_values - before)
                corrected_count = int(np.sum(diff > 1e-10))

                applied.append(constraint.constraint_name)
                logs.append({
                    "constraint": constraint.constraint_name,
                    "corrected_points": corrected_count,
                    "max_correction": float(np.max(diff)),
                    "mean_correction": float(np.mean(diff)),
                })
                total_corrections += corrected_count

                self._logger.debug(
                    f"应用约束 {constraint.constraint_name}: 修正{corrected_count}个点"
                )

            except Exception as e:
                self._logger.error(f"应用约束失败 {constraint.constraint_name}: {e}")
                logs.append({
                    "constraint": constraint.constraint_name,
                    "error": str(e),
                })

        return ApplyResult(
            original_values=original,
            corrected_values=current_values,
            applied_constraints=applied,
            corrections_log=logs,
            total_corrections=total_corrections,
        )

    def get_constraint_order(self) -> List[str]:
        """获取约束应用顺序"""
        return [c.constraint_name for c in self.constraints]

    def reorder_constraints(self, order: List[str]) -> None:
        """重新排序约束"""
        name_to_constraint = {c.constraint_name: c for c in self.constraints}
        self.constraints = [name_to_constraint[name] for name in order if name in name_to_constraint]

