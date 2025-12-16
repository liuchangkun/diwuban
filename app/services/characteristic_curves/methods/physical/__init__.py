"""
物理模型拟合方法子包 (app.services.characteristic_curves.methods.physics)

本模块包含所有物理模型类拟合方法的实现，包括：
- 泵特性方程 (pump_characteristic.py): Q-H曲线专用
- 功率方程 (power_equation.py): Q-P曲线专用

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/05_拟合方法/02_物理模型.md
"""

from .pump_characteristic import (
    PhysicsPumpCharMethod,
    register_pump_char_methods,
)
from .power_equation import (
    PhysicsPowerEqMethod,
    register_power_eq_methods,
)

__all__ = [
    # 泵特性方程
    "PhysicsPumpCharMethod",
    "register_pump_char_methods",
    # 功率方程
    "PhysicsPowerEqMethod",
    "register_power_eq_methods",
    # 注册函数
    "register_all_physics_methods",
]


def register_all_physics_methods() -> None:
    """注册所有物理模型方法到 MethodRegistry"""
    register_pump_char_methods()
    register_power_eq_methods()

