"""
曲线模块 (app.services.characteristic_curves.curves)

本模块提供各类型曲线的专用处理器：
- BaseCurve: 曲线抽象基类
- CurveRegistry: 曲线注册器
- QHCurve: Q-H曲线处理器
- QPCurve: Q-P曲线处理器
- QEtaCurve: Q-η曲线处理器
- HEtaCurve: H-η曲线处理器
- PEtaCurve: P-η曲线处理器
- QNPSHCurve: Q-NPSH曲线处理器
- ParallelPumpGroupCurve: 并联泵组曲线处理器

版本: v1.0
更新日期: 2025-12-09
"""

from app.services.characteristic_curves.curves.base_curve import (
    BaseCurve,
    CurveType,
    FitResult,
    MonotonicityType,
)
from app.services.characteristic_curves.curves.curve_registry import (
    CurveRegistry,
    get_curve_registry,
)
from app.services.characteristic_curves.curves.qh_curve import QHCurve
from app.services.characteristic_curves.curves.qp_curve import QPCurve
from app.services.characteristic_curves.curves.qeta_curve import QEtaCurve
from app.services.characteristic_curves.curves.heta_curve import HEtaCurve
from app.services.characteristic_curves.curves.peta_curve import PEtaCurve
from app.services.characteristic_curves.curves.qnpsh_curve import QNPSHCurve
from app.services.characteristic_curves.curves.parallel_pump_group_curve import (
    ParallelPumpGroupCurve,
    PumpCurveEntry,
    GroupCurveResult,
)

__all__ = [
    "BaseCurve",
    "CurveType",
    "FitResult",
    "MonotonicityType",
    "CurveRegistry",
    "get_curve_registry",
    "QHCurve",
    "QPCurve",
    "QEtaCurve",
    "HEtaCurve",
    "PEtaCurve",
    "QNPSHCurve",
    "ParallelPumpGroupCurve",
    "PumpCurveEntry",
    "GroupCurveResult",
]

