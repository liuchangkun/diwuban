"""
pump_inlet_pressure 计算方法模块

提供2种计算方法：
- equiv_coef: 等效损失系数法（主方法）
- static_pressure: 静压法（备用方法）
"""

from app.services.calculation.metrics.pump_inlet_pressure.methods.equiv_coef import calculate_equiv_coef
from app.services.calculation.metrics.pump_inlet_pressure.methods.static_pressure import calculate_static_pressure

__all__ = [
    'calculate_equiv_coef',
    'calculate_static_pressure',
]

