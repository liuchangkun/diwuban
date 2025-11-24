"""
约束层模块 (app.services.characteristic_curves.constraints)

本模块提供曲线拟合的约束功能：
- ConstraintLearner: 从历史数据学习约束参数
- ConstraintParameterManager: 约束参数统一管理
- BaseConstraint: 约束抽象基类
- MonotonicityConstraint: 单调性约束验证
- BoundaryConstraint: 边界约束验证
- PhysicsValidator: 物理验证器

版本: v1.1
更新日期: 2025-12-08

使用方式：
    from app.services.characteristic_curves.constraints import (
        MonotonicityConstraint,
        BoundaryConstraint,
        PhysicsValidator,
    )

    mono = MonotonicityConstraint()
    result = mono.validate(curve_type='qh', x_values=Q, y_values=H)
"""

from app.services.characteristic_curves.constraints.base_constraint import (
    BaseConstraint,
    ConstraintResult,
    ConstraintType,
)
from app.services.characteristic_curves.constraints.boundary_constraint import (
    BoundaryConstraint,
)
from app.services.characteristic_curves.constraints.constraint_learner import (
    ConstraintLearner,
)
from app.services.characteristic_curves.constraints.constraint_parameter_manager import (
    ConstraintParameterManager,
)
from app.services.characteristic_curves.constraints.monotonicity_constraint import (
    MonotonicityConstraint,
)
from app.services.characteristic_curves.constraints.physics_validator import (
    PhysicsValidator,
    ValidationResult,
)
from app.services.characteristic_curves.constraints.constraint_cache import (
    ConstraintCache,
    CachedConstraint,
)
from app.services.characteristic_curves.constraints.constraint_validator import (
    ConstraintValidator,
    CombinedValidationResult,
)
from app.services.characteristic_curves.constraints.constraint_applier import (
    ConstraintApplier,
    ApplyResult,
)
from app.services.characteristic_curves.constraints.constraint_factory import (
    ConstraintFactory,
    get_constraint_factory,
)

__all__ = [
    # 基类和数据结构
    "BaseConstraint",
    "ConstraintResult",
    "ConstraintType",
    # 约束验证器
    "MonotonicityConstraint",
    "BoundaryConstraint",
    "PhysicsValidator",
    "ValidationResult",
    # 约束管理
    "ConstraintCache",
    "CachedConstraint",
    "ConstraintValidator",
    "CombinedValidationResult",
    "ConstraintApplier",
    "ApplyResult",
    "ConstraintFactory",
    "get_constraint_factory",
    # 已有模块
    "ConstraintLearner",
    "ConstraintParameterManager",
]

