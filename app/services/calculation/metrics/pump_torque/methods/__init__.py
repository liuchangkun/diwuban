"""
pump_torque 计算方法模块

包含：
- method_a: 功率-转速法
- method_b: 水力功率法
"""

from . import method_a
from . import method_b

__all__ = ['method_a', 'method_b']

