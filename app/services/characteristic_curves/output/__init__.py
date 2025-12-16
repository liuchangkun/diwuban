"""
输出模块 (app.services.characteristic_curves.output)

本模块提供拟合结果的可视化输出功能和JSON导出功能。

版本: v2.1
创建日期: 2025-12-09
更新日期: 2025-12-14
"""

from .high_res_plotter import (
    HighResPlotter,
    CurveAnnotations,
    PumpGroupAnnotations,
    DeviceInfo,
    RatedPoint,
    BEPPoint,
    OperatingRange,
    EfficiencyZone,
    WarningZone,
    DesignPoint,
    FitEquation,
    DataInfo,
    FitMetrics,
    MotorInfo,
    PumpGroupInfo,
    SwitchPoint,
    SpecificEnergy,
)
from .result_output import ResultOutput
from .curve_json_exporter import CurveJsonExporter, export_fit_result_to_json

__all__ = [
    # 绘图器
    "HighResPlotter",
    "ResultOutput",
    # JSON导出
    "CurveJsonExporter",
    "export_fit_result_to_json",
    # 单泵标注
    "CurveAnnotations",
    "DeviceInfo",
    "RatedPoint",
    "BEPPoint",
    "OperatingRange",
    "EfficiencyZone",
    "WarningZone",
    "DesignPoint",
    "FitEquation",
    "DataInfo",
    "FitMetrics",
    "MotorInfo",
    # 泵组标注
    "PumpGroupAnnotations",
    "PumpGroupInfo",
    "SwitchPoint",
    "SpecificEnergy",
]
