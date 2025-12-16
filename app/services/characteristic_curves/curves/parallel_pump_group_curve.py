"""
并联泵组曲线处理器 (app.services.characteristic_curves.curves.parallel_pump_group_curve)

并联泵组的组合特性曲线处理。

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/04_曲线模块/04_并联泵组曲线.md

功能:
- 并联泵组Q-H曲线叠加
- 并联泵组Q-P曲线叠加
- 并联泵组Q-η曲线计算
- N台泵运行时的组合曲线生成
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from app.services.characteristic_curves.curves.base_curve import (
    BaseCurve,
    CurveType,
    FitResult,
    MonotonicityType,
)


@dataclass
class PumpCurveEntry:
    """单泵曲线条目

    Attributes:
        pump_id: 泵ID
        qh_coeffs: Q-H曲线系数
        qp_coeffs: Q-P曲线系数
        qeta_coeffs: Q-η曲线系数（可选）
        q_max: 最大流量
        rated_power: 额定功率
    """

    pump_id: int
    qh_coeffs: List[float]
    qp_coeffs: List[float]
    qeta_coeffs: Optional[List[float]] = None
    q_max: float = 300.0
    rated_power: float = 100.0


@dataclass
class GroupCurveResult:
    """泵组曲线结果"""

    success: bool
    n_pumps: int
    pump_ids: List[int]
    Q_total: np.ndarray
    H_group: np.ndarray
    P_total: np.ndarray
    eta_group: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ParallelPumpGroupCurve:
    """并联泵组曲线处理器

    计算并联泵组的组合特性曲线。

    并联规则:
    - 扬程相同时，流量相加: Q_total = Q1 + Q2 + ... + Qn
    - 功率相加: P_total = P1 + P2 + ... + Pn
    - 效率: η = (ρ*g*Q_total*H) / P_total

    使用方式:
        group_curve = ParallelPumpGroupCurve()
        group_curve.add_pump(pump_entry)
        result = group_curve.generate_group_curve([1, 2, 3])
    """

    def __init__(self) -> None:
        """初始化并联泵组曲线处理器"""
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._pump_entries: Dict[int, PumpCurveEntry] = {}

    def add_pump(self, entry: PumpCurveEntry) -> None:
        """添加单泵曲线"""
        self._pump_entries[entry.pump_id] = entry
        self._logger.info(f"添加泵曲线: pump_id={entry.pump_id}")

    def remove_pump(self, pump_id: int) -> bool:
        """移除单泵曲线"""
        if pump_id in self._pump_entries:
            del self._pump_entries[pump_id]
            return True
        return False

    def list_pumps(self) -> List[int]:
        """列出所有已注册的泵ID"""
        return list(self._pump_entries.keys())

    def generate_group_curve(
        self, pump_ids: List[int], h_range: Optional[np.ndarray] = None
    ) -> GroupCurveResult:
        """生成并联泵组曲线

        Args:
            pump_ids: 参与运行的泵ID列表
            h_range: 扬程范围（如果为None，自动计算）

        Returns:
            GroupCurveResult: 泵组曲线结果
        """
        if not pump_ids:
            return GroupCurveResult(
                success=False, n_pumps=0, pump_ids=[], Q_total=np.array([]),
                H_group=np.array([]), P_total=np.array([]),
                metadata={"error": "无运行泵"},
            )

        # 验证所有泵都已注册
        for pid in pump_ids:
            if pid not in self._pump_entries:
                return GroupCurveResult(
                    success=False, n_pumps=0, pump_ids=pump_ids,
                    Q_total=np.array([]), H_group=np.array([]), P_total=np.array([]),
                    metadata={"error": f"泵{pid}未注册"},
                )

        # 确定扬程范围
        if h_range is None:
            h_range = np.linspace(10, 120, 100)

        # 并联计算：在相同扬程下，流量相加
        Q_total = np.zeros_like(h_range)
        P_total = np.zeros_like(h_range)

        for pid in pump_ids:
            entry = self._pump_entries[pid]
            # 根据扬程反算流量 H = a0 + a1*Q + a2*Q^2 => 解Q
            q_values = self._h_to_q(h_range, entry.qh_coeffs, entry.q_max)
            p_values = np.polyval(entry.qp_coeffs, q_values)
            Q_total += q_values
            P_total += p_values

        # 计算组合效率 η = ρgQH / P (简化计算)
        # 使用 η ≈ Q*H / P * 常数
        rho_g = 9810  # ρ*g ≈ 9810 N/m³
        eta_group = np.where(
            P_total > 0,
            (rho_g * Q_total / 3600 * h_range) / (P_total * 1000) * 100,
            0.0,
        )
        eta_group = np.clip(eta_group, 0, 100)

        return GroupCurveResult(
            success=True,
            n_pumps=len(pump_ids),
            pump_ids=pump_ids,
            Q_total=Q_total,
            H_group=h_range,
            P_total=P_total,
            eta_group=eta_group,
        )

    def _h_to_q(
        self, h_values: np.ndarray, qh_coeffs: List[float], q_max: float
    ) -> np.ndarray:
        """根据扬程反算流量（二次方程求根）"""
        # H = a2*Q^2 + a1*Q + a0
        # a2*Q^2 + a1*Q + (a0 - H) = 0
        if len(qh_coeffs) < 3:
            # 线性情况
            a1, a0 = qh_coeffs[0], qh_coeffs[1] if len(qh_coeffs) > 1 else 0
            return np.clip((h_values - a0) / a1 if a1 != 0 else 0, 0, q_max)

        a2, a1, a0 = qh_coeffs[0], qh_coeffs[1], qh_coeffs[2]
        q_values = []
        for h in h_values:
            # 解二次方程
            discriminant = a1**2 - 4 * a2 * (a0 - h)
            if discriminant < 0:
                q_values.append(0.0)
            else:
                # 取正根（物理意义上的流量）
                q1 = (-a1 + np.sqrt(discriminant)) / (2 * a2)
                q2 = (-a1 - np.sqrt(discriminant)) / (2 * a2)
                q = max(0, min(q_max, q1 if q1 > 0 else q2))
                q_values.append(q)
        return np.array(q_values)

