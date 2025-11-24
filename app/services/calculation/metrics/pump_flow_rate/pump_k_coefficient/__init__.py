"""
泵 k 系数模块（app.services.calculation.metrics.pump_flow_rate.pump_k_coefficient）

本模块提供泵 k 系数学习和出水检测功能：
- PumpKCoefficientLearner: 从高频数据学习 k 系数
- WaterOutputDetector: 基于 k 系数判断泵是否出水

核心物理公式：
    k = H_rated / f_rated²     （k 系数定义）
    f_min = sqrt(P_outlet × 102 / k)  （最小有效频率）
    is_outputting = 1 if f >= f_min else 0  （出水判断）

所有可调参数从 calculation_parameters 表读取，禁止硬编码。
"""

from __future__ import annotations

from .learner import PumpKCoefficientLearner
from .detector import WaterOutputDetector
from .constants import (
    PRESSURE_TO_HEAD,
    METRIC_KEY,
    PARAM_NAME_K_COEFFICIENT,
)

__all__ = [
    "PumpKCoefficientLearner",
    "WaterOutputDetector",
    "PRESSURE_TO_HEAD",
    "METRIC_KEY",
    "PARAM_NAME_K_COEFFICIENT",
]

