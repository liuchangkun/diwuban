"""
约束工厂 (app.services.characteristic_curves.constraints.constraint_factory)

根据曲线类型创建约束组合。

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/03_核心模块/04_约束层.md
"""

import logging
from typing import Dict, List, Type

from app.services.characteristic_curves.constraints.base_constraint import (
    BaseConstraint,
)
from app.services.characteristic_curves.constraints.boundary_constraint import (
    BoundaryConstraint,
)
from app.services.characteristic_curves.constraints.monotonicity_constraint import (
    MonotonicityConstraint,
)


# 曲线类型到约束组合的映射
CURVE_CONSTRAINT_MAP: Dict[str, List[Type[BaseConstraint]]] = {
    "qh": [MonotonicityConstraint, BoundaryConstraint],
    "qp": [MonotonicityConstraint, BoundaryConstraint],
    "qeta": [MonotonicityConstraint, BoundaryConstraint],
    "heta": [BoundaryConstraint],
    "peta": [BoundaryConstraint],
    "qnpsh": [MonotonicityConstraint, BoundaryConstraint],
}


class ConstraintFactory:
    """约束工厂

    根据曲线类型创建适当的约束组合。

    使用方式:
        factory = ConstraintFactory()
        constraints = factory.create_constraints('qh')
    """

    def __init__(self) -> None:
        """初始化约束工厂"""
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._constraint_map = CURVE_CONSTRAINT_MAP.copy()

    def create_constraints(self, curve_type: str) -> List[BaseConstraint]:
        """根据曲线类型创建约束组合

        Args:
            curve_type: 曲线类型 (qh, qp, qeta, heta, peta, qnpsh)

        Returns:
            List[BaseConstraint]: 约束实例列表
        """
        curve_type_lower = curve_type.lower()

        if curve_type_lower not in self._constraint_map:
            self._logger.warning(f"未知曲线类型: {curve_type}，使用默认约束")
            return [MonotonicityConstraint(), BoundaryConstraint()]

        constraint_classes = self._constraint_map[curve_type_lower]
        constraints = [cls() for cls in constraint_classes]

        self._logger.debug(
            f"为曲线类型 {curve_type} 创建约束: {[c.constraint_name for c in constraints]}"
        )

        return constraints

    def register_constraint(
        self, curve_type: str, constraint_classes: List[Type[BaseConstraint]]
    ) -> None:
        """注册曲线类型的约束组合

        Args:
            curve_type: 曲线类型
            constraint_classes: 约束类列表
        """
        self._constraint_map[curve_type.lower()] = constraint_classes
        self._logger.info(f"注册约束组合: {curve_type} -> {[c.__name__ for c in constraint_classes]}")

    def get_supported_curve_types(self) -> List[str]:
        """获取支持的曲线类型列表"""
        return list(self._constraint_map.keys())

    def get_constraint_info(self, curve_type: str) -> Dict[str, List[str]]:
        """获取曲线类型的约束信息

        Args:
            curve_type: 曲线类型

        Returns:
            Dict: 约束信息，包含约束名称和类型
        """
        curve_type_lower = curve_type.lower()

        if curve_type_lower not in self._constraint_map:
            return {"constraints": [], "error": f"未知曲线类型: {curve_type}"}

        constraint_classes = self._constraint_map[curve_type_lower]
        return {
            "curve_type": curve_type,
            "constraints": [cls.__name__ for cls in constraint_classes],
            "constraint_count": len(constraint_classes),
        }


# 单例工厂实例
_factory_instance: ConstraintFactory = None


def get_constraint_factory() -> ConstraintFactory:
    """获取约束工厂单例"""
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = ConstraintFactory()
    return _factory_instance

