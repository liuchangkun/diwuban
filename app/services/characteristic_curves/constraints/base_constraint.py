"""
约束层基类 (app.services.characteristic_curves.constraints.base_constraint)

定义约束的抽象接口和通用数据结构。

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/03_核心模块/04_约束层.md
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np


class ConstraintType(Enum):
    """约束类型枚举"""

    MONOTONICITY = "monotonicity"  # 单调性约束
    BOUNDARY = "boundary"  # 边界约束
    PHYSICS = "physics"  # 物理约束
    RANGE = "range"  # 范围约束
    CUSTOM = "custom"  # 自定义约束


@dataclass
class ConstraintResult:
    """约束验证结果

    Attributes:
        is_valid: 是否通过验证
        constraint_type: 约束类型
        violation_ratio: 违反比例 (0-1)
        violation_points: 违反点的索引列表
        details: 详细信息字典
        message: 结果描述信息
    """

    is_valid: bool
    constraint_type: ConstraintType
    violation_ratio: float = 0.0
    violation_points: List[int] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "is_valid": self.is_valid,
            "constraint_type": self.constraint_type.value,
            "violation_ratio": self.violation_ratio,
            "violation_points": self.violation_points,
            "details": self.details,
            "message": self.message,
        }


class BaseConstraint(ABC):
    """约束抽象基类

    所有约束类必须继承此基类并实现 validate() 和 apply() 方法。

    Attributes:
        constraint_type: 约束类型
        constraint_name: 约束名称
    """

    constraint_type: ConstraintType = ConstraintType.CUSTOM
    constraint_name: str = "基础约束"

    def __init__(self) -> None:
        """初始化约束"""
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def validate(
        self,
        curve_type: str,
        x_values: np.ndarray,
        y_values: np.ndarray,
        tolerance: float = 0.01,
        **kwargs: Any,
    ) -> ConstraintResult:
        """验证约束是否满足

        Args:
            curve_type: 曲线类型 ('qh', 'qp', 'qeta')
            x_values: X轴值（流量Q）
            y_values: Y轴值（扬程H/功率P/效率η）
            tolerance: 容差
            **kwargs: 其他参数

        Returns:
            ConstraintResult: 验证结果
        """
        pass

    @abstractmethod
    def apply(
        self,
        curve_type: str,
        x_values: np.ndarray,
        y_values: np.ndarray,
        **kwargs: Any,
    ) -> np.ndarray:
        """应用约束修正数据

        Args:
            curve_type: 曲线类型
            x_values: X轴值
            y_values: Y轴值
            **kwargs: 其他参数

        Returns:
            np.ndarray: 修正后的Y值
        """
        pass

    def _validate_input(
        self, x_values: np.ndarray, y_values: np.ndarray
    ) -> None:
        """验证输入数据

        Args:
            x_values: X轴值
            y_values: Y轴值

        Raises:
            ValueError: 当输入数据无效时
        """
        if x_values is None or y_values is None:
            raise ValueError("输入数据不能为None")

        if len(x_values) != len(y_values):
            raise ValueError(
                f"X和Y长度不一致: {len(x_values)} vs {len(y_values)}"
            )

        if len(x_values) < 2:
            raise ValueError(f"数据点数量不足: {len(x_values)} < 2")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(type={self.constraint_type.value})"

