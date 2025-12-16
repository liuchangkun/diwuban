"""
混合拟合方法模块 (app.services.characteristic_curves.methods.hybrid)

本模块提供结合物理模型和数学/ML方法的混合拟合方法。

包含方法:
- HybridPhysicsPolyMethod: 物理约束多项式拟合方法

版本: v1.0
更新日期: 2025-12-08
"""

from app.services.characteristic_curves.methods.hybrid.physics_polynomial import (
    HybridPhysicsPolyMethod,
)

__all__ = [
    "HybridPhysicsPolyMethod",
]

