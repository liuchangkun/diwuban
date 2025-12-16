"""
曲线模块 (app.services.characteristic_curves.curves)

本模块提供特性曲线拟合的曲线类：
- BaseCurve: 曲线抽象基类
- QHCurve: Q-H曲线（流量-扬程）
- QPCurve: Q-P曲线（流量-功率）
- QEtaCurve: Q-η曲线（流量-效率）

版本: v2.1
更新日期: 2025-12-10
"""

from .base_curve import BaseCurve
from .qh_curve import QHCurve
from .qp_curve import QPCurve
from .qeta_curve import QEtaCurve

__all__ = [
    "BaseCurve",
    "QHCurve",
    "QPCurve",
    "QEtaCurve",
]
