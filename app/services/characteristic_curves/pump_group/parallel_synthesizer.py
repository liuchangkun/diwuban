"""
并联合成器 (app.services.characteristic_curves.pump_group.parallel_synthesizer)

本模块提供泵组并联曲线合成功能：
- 同构泵组：Q_group = N × Q_single（简化合成）
- 异构泵组：等扬程流量叠加（迭代求解）
- 混合泵组：分类合成后再叠加
- 功率计算：基于Q-P曲线或物理公式
- 效率计算：η = ρgQH / P

物理原理：
- 并联特性：H₁ = H₂ = ... = H_N = H_system
- 流量叠加：Q_total = Q₁ + Q₂ + ... + Q_N
- 功率叠加：P_total = P₁ + P₂ + ... + P_N
- 效率计算：η_total = (ρgQ_total·H_system) / P_total

版本: v1.0
更新日期: 2025-12-09
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, TYPE_CHECKING

import logging
import numpy as np
from scipy.optimize import brentq

from app.services.characteristic_curves.models import SynthesisResult
from app.services.characteristic_curves.shared.exceptions import HeadOutOfRangeError

if TYPE_CHECKING:
    from app.services.characteristic_curves.shared.curve_registry import CurveRegistry


@dataclass
class WeightedSynthesisResult:
    """加权合成结果（用于MIXED_HETEROGENEOUS场景）

    内部类，仅用于synthesize_mixed_weighted()方法。
    """

    # 基础合成结果
    Q_total: float  # 总流量 (m³/h)
    H_system: float  # 系统扬程 (m)
    pump_flows: Dict[int, float]  # 各泵流量 {pump_id: Q_i}
    pump_heads: Dict[int, float]  # 各泵扬程 {pump_id: H_i}

    # 功率和效率
    pump_powers: Dict[int, float]  # 各泵功率 {pump_id: P_i} (kW)
    P_total: float  # 总功率 (kW)
    eta_total: float  # 总效率 (0-1)

    # 权重分析
    power_weights: Dict[int, float]  # 功率权重（基于额定功率）
    flow_weights: Dict[int, float]  # 流量权重
    power_flow_ratios: Dict[int, float]  # 功率/流量比
    vfd_stats: Dict[str, float]  # VFD子组统计信息

    # 用于负荷分配的额定功率
    _rated_powers: Optional[Dict[int, float]] = None

    def get_flow_distribution(self) -> Dict[int, float]:
        """获取流量分配比例"""
        return self.flow_weights.copy()

    def get_power_distribution(self) -> Dict[int, float]:
        """获取功率分配比例"""
        if self.P_total <= 0:
            return {pid: 0.0 for pid in self.pump_powers}
        return {pid: P / self.P_total for pid, P in self.pump_powers.items()}

    def get_load_distribution(
        self, rated_powers: Optional[Dict[int, float]] = None
    ) -> Dict[int, float]:
        """获取负荷分配比例

        负荷率 = 实际功率 / 额定功率

        Args:
            rated_powers: 各泵额定功率 {pump_id: P_rated}
                          如果不提供，使用内部存储的_rated_powers

        Returns:
            Dict[int, float]: 各泵负荷率 {pump_id: load_ratio}
        """
        powers = rated_powers or self._rated_powers

        if powers is None or self.pump_powers is None:
            return {}

        return {
            pump_id: (self.pump_powers.get(pump_id, 0) / powers.get(pump_id, 1))
            for pump_id in self.pump_powers.keys()
            if powers.get(pump_id, 0) > 0
        }


class ParallelSynthesizer:
    """
    并联合成器

    职责：
    1. 同构泵组：Q_group = N × Q_single（简化合成）
    2. 异构泵组：等扬程流量叠加（迭代求解）
    3. 混合泵组：分类合成后再叠加
    4. 功率计算：基于Q-P曲线或物理公式
    5. 效率计算：η = ρgQH / P

    物理常数：
        RHO = 1000  # 水密度 kg/m³
        G = 9.81    # 重力加速度 m/s²
    """

    # 物理常数
    RHO = 1000.0  # 水密度 kg/m³
    G = 9.81  # 重力加速度 m/s²

    def __init__(self):
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._pump_curves: Dict[int, Callable] = {}  # pump_id → Q→H 函数
        self._pump_inverse_curves: Dict[int, Callable] = {}  # pump_id → H→Q 函数
        self._pump_power_curves: Dict[int, Callable] = {}  # pump_id → Q→P 函数
        self._pump_rated_powers: Dict[int, float] = {}  # pump_id → 额定功率
        self._pump_H_ranges: Dict[int, Tuple[float, float]] = {}  # pump_id → (H_min, H_max)
        self._pump_efficiency_curves: Dict[int, Callable] = {}  # pump_id → Q→η 函数

    # ══════════════════════════════════════════════════════════════════════════
    # 📋 软启泵(SS)处理规则
    # ──────────────────────────────────────────────────────────────────────────
    # 相似律（Q∝f, H∝f², P∝f³）仅适用于变频泵(VFD)。软启泵的处理规则如下：
    #
    # 1. **固定频率**：软启泵始终使用50Hz额定频率运行，不进行频率归一化
    # 2. **曲线使用**：直接使用P0阶段拟合的50Hz额定曲线，无需反归一化
    # 3. **流量分配**：在混合泵组中，软启泵流量由系统扬程决定
    # 4. **不参与频率调节**：流量调节完全由变频泵完成
    # 5. **启停控制**：软启泵只能开/关，不能调节
    # 6. **功率计算**：软启泵功率使用50Hz额定曲线
    # ══════════════════════════════════════════════════════════════════════════

    def register_pump_curve(
        self,
        pump_id: int,
        curve_func: Callable[[float], float],
        inverse_func: Optional[Callable[[float], float]] = None,
        power_func: Optional[Callable[[float], float]] = None,
        rated_power: Optional[float] = None,
        H_range: Optional[Tuple[float, float]] = None,
        efficiency_func: Optional[Callable[[float], float]] = None
    ):
        """
        注册单泵曲线

        Args:
            pump_id: 泵ID
            curve_func: Q → H 函数
            inverse_func: H → Q 函数（可选，用于并联计算）
            power_func: Q → P 函数（可选，用于功率计算）
            rated_power: 额定功率 kW（可选，用于负荷分配和效率估算）
            H_range: 有效扬程范围 (H_min, H_max)
            efficiency_func: Q → η 函数（可选，用于效率计算）

        Note:
            如果未提供power_func，将使用物理公式估算功率：
            P = ρ × g × Q × H / η_estimated
            其中η_estimated取0.75（典型水泵效率）
        """
        self._pump_curves[pump_id] = curve_func
        if inverse_func:
            self._pump_inverse_curves[pump_id] = inverse_func
        if power_func:
            self._pump_power_curves[pump_id] = power_func
        if rated_power:
            self._pump_rated_powers[pump_id] = rated_power
        if H_range:
            self._pump_H_ranges[pump_id] = H_range
        if efficiency_func:
            self._pump_efficiency_curves[pump_id] = efficiency_func

        self._logger.debug(
            f"[曲线注册] pump_id={pump_id}, "
            f"has_inverse={inverse_func is not None}, "
            f"has_power={power_func is not None}, "
            f"rated_power={rated_power}, H_range={H_range}"
        )

    def _calculate_pump_power(
        self,
        pump_id: int,
        Q: float,
        H: float,
        default_efficiency: Optional[float] = None,
        frequency: Optional[float] = None
    ) -> float:
        """
        计算单泵功率

        Args:
            pump_id: 泵ID
            Q: 流量 m³/h
            H: 扬程 m
            default_efficiency: 默认效率（可选，None时自动获取）
            frequency: 运行频率Hz
                - None或50: 不修正（工频运行）
                - 其他值: 应用相似定律修正 P ∝ f³

        Returns:
            功率 kW
        """
        if pump_id in self._pump_power_curves:
            # 使用注册的功率曲线
            P_50 = self._pump_power_curves[pump_id](Q)
            # 变频修正
            if frequency and frequency != 50.0:
                P_f = P_50 * (frequency / 50.0) ** 3
                self._logger.debug(
                    f"[功率修正] pump={pump_id}, f={frequency}Hz, "
                    f"P={P_50:.2f}→{P_f:.2f}kW"
                )
                return P_f
            return P_50

        # 智能效率获取
        if default_efficiency is None:
            default_efficiency = self._get_estimated_efficiency(pump_id, Q, H)

        # 使用物理公式估算
        Q_m3s = Q / 3600  # m³/h → m³/s
        P_watts = self.RHO * self.G * Q_m3s * H / default_efficiency
        P_kw = P_watts / 1000

        # 变频修正
        if frequency and frequency != 50.0:
            P_kw = P_kw * (frequency / 50.0) ** 3
            self._logger.debug(
                f"[功率估算] pump={pump_id}, Q={Q:.1f}m³/h, H={H:.1f}m, "
                f"f={frequency}Hz, η_est={default_efficiency:.2f} → "
                f"P={P_kw:.2f}kW (变频修正后)"
            )
        else:
            self._logger.debug(
                f"[功率估算] pump={pump_id}, Q={Q:.1f}m³/h, H={H:.1f}m, "
                f"η_est={default_efficiency:.2f} → P={P_kw:.2f}kW"
            )
        return P_kw

    def _get_estimated_efficiency(
        self, pump_id: int, Q: float, H: float
    ) -> float:
        """
        获取估算效率

        优先级：
        1. 从efficiency_func获取（如果已注册）
        2. 从fact_measurements获取历史平均效率
        3. 使用默认值0.75
        """
        # 尝试从已注册的效率曲线获取
        if pump_id in self._pump_efficiency_curves:
            try:
                return self._pump_efficiency_curves[pump_id](Q)
            except Exception:
                pass

        # 尝试从历史数据获取
        avg_eta = self._query_historical_avg_efficiency(pump_id)
        if avg_eta and 0.5 <= avg_eta <= 0.95:
            self._logger.info(
                f"[功率计算] 泵{pump_id}使用历史平均效率η={avg_eta:.2f}"
            )
            return avg_eta

        # 回退到默认值
        self._logger.warning(
            f"[功率计算] 泵{pump_id}无历史效率数据，使用默认η=0.75"
        )
        return 0.75

    def _query_historical_avg_efficiency(self, pump_id: int) -> Optional[float]:
        """从历史数据查询平均效率"""
        try:
            from app.adapters.db.pool import get_connection

            with get_connection() as conn:
                sql = """
                    SELECT AVG(fm.value)
                    FROM fact_measurements fm
                    WHERE fm.device_id = %(pump_id)s
                      AND fm.metric_id = (
                          SELECT id FROM dim_metric_config
                          WHERE metric_key = 'pump_efficiency'
                      )
                      AND fm.value BETWEEN 0.5 AND 0.95
                      AND fm.ts_raw > NOW() - INTERVAL '30 days'
                """
                result = conn.execute(sql, {'pump_id': pump_id}).fetchone()
                return float(result[0]) if result and result[0] else None
        except Exception as e:
            self._logger.debug(f"[历史效率查询] 泵{pump_id}查询失败: {e}")
            return None

    def _calculate_total_efficiency(
        self,
        Q_total: float,
        H_system: float,
        P_total: float
    ) -> float:
        """
        计算泵组总效率

        Args:
            Q_total: 总流量 m³/h
            H_system: 系统扬程 m
            P_total: 总功率 kW

        Returns:
            总效率 (0-1)

        公式：
            η = (ρ × g × Q × H) / P
            其中Q需要从m³/h转换为m³/s，P从kW转换为W
        """
        if P_total <= 0 or Q_total <= 0:
            return 0.0

        Q_m3s = Q_total / 3600  # m³/h → m³/s
        P_watts = P_total * 1000  # kW → W

        # η = ρgQH / P
        eta = (self.RHO * self.G * Q_m3s * H_system) / P_watts

        # 限制在合理范围内
        eta = max(0.0, min(1.0, eta))

        self._logger.debug(
            f"[效率计算] Q={Q_total:.1f}m³/h, H={H_system:.1f}m, "
            f"P={P_total:.2f}kW → η={eta:.2%}"
        )
        return eta

    def _get_pump_h_max(self, pump_id: int) -> float:
        """获取泵的最大扬程（关死点）"""
        # 优先从已注册的H_range获取
        if pump_id in self._pump_H_ranges:
            return self._pump_H_ranges[pump_id][1]

        # 从CurveRegistry获取曲线范围
        try:
            from app.services.characteristic_curves.shared.curve_registry import (
                CurveRegistry,
            )

            registry = CurveRegistry()
            entry = registry.get_entry(pump_id, "qh")
            if entry and entry.H_range:
                return entry.H_range[1]
        except Exception:
            pass

        return 100.0  # 默认值

    def synthesize_homogeneous(
        self,
        base_pump_id: int,
        n_pumps: int,
        Q_range: Tuple[float, float] = (0, 3000)
    ) -> Callable[[float], float]:
        """
        同构泵组合成（返回曲线函数）

        Args:
            base_pump_id: 基准泵ID
            n_pumps: 泵数量
            Q_range: 流量范围

        Returns:
            Q_total → H_group 函数
        """
        if base_pump_id not in self._pump_curves:
            raise ValueError(f"未注册泵曲线: pump_id={base_pump_id}")

        base_curve = self._pump_curves[base_pump_id]

        def group_curve(Q_total: float) -> float:
            """同构泵组曲线：Q_single = Q_total / N"""
            Q_single = Q_total / n_pumps
            return base_curve(Q_single)

        return group_curve

    def synthesize_homogeneous_with_power(
        self,
        base_pump_id: int,
        pump_ids: List[int],
        H_system: float
    ) -> SynthesisResult:
        """
        同构泵组合成（含功率和效率计算）

        Args:
            base_pump_id: 基准泵ID
            pump_ids: 所有运行泵的ID列表
            H_system: 系统扬程

        Returns:
            SynthesisResult: 包含流量、功率、效率的完整合成结果
        """
        n_pumps = len(pump_ids)

        if base_pump_id not in self._pump_inverse_curves:
            raise ValueError(f"泵 {base_pump_id} 未注册逆函数")

        # 1. 计算各泵流量（同构泵组，流量平均分配）
        inverse_func = self._pump_inverse_curves[base_pump_id]
        Q_single = inverse_func(H_system)
        Q_total = Q_single * n_pumps

        pump_flows = {pid: Q_single for pid in pump_ids}
        pump_heads = {pid: H_system for pid in pump_ids}

        # 2. 计算各泵功率
        pump_powers = {}
        P_total = 0.0
        for pid in pump_ids:
            P_i = self._calculate_pump_power(pid, Q_single, H_system)
            pump_powers[pid] = P_i
            P_total += P_i

        # 3. 计算总效率
        eta_total = self._calculate_total_efficiency(Q_total, H_system, P_total)

        self._logger.info(
            f"[同构合成] base_pump={base_pump_id}, n={n_pumps}, "
            f"H={H_system:.1f}m → Q_total={Q_total:.1f}m³/h, "
            f"P_total={P_total:.2f}kW, η={eta_total:.2%}"
        )

        # 创建结果并设置_rated_powers
        result = SynthesisResult(
            Q_total=Q_total,
            H_system=H_system,
            pump_flows=pump_flows,
            pump_heads=pump_heads,
            pump_powers=pump_powers,
            P_total=P_total,
            eta_total=eta_total,
        )
        result._rated_powers = {
            pid: self._pump_rated_powers.get(pid, 0) for pid in pump_ids
        }
        return result

    def synthesize_vfd_with_freq(
        self,
        pump_ids: List[int],
        frequencies: Dict[int, float]
    ) -> Callable[[float], float]:
        """
        考虑频率差异的VFD泵组合成

        Args:
            pump_ids: 泵ID列表
            frequencies: 各泵当前运行频率 {pump_id: freq_Hz}

        Returns:
            H_system → Q_total 的计算函数

        物理原理：
            1. 各泵Q-H曲线已归一化到50Hz
            2. 给定系统扬程H_system，需要归一化到50Hz后查曲线
            3. 得到的Q_50Hz再反归一化到实际频率
            4. 各泵实际流量相加得到总流量

        公式：
            H_50 = H_system × (50 / f_actual)²
            Q_50 = inverse_func(H_50)
            Q_actual = Q_50 × (f_actual / 50)
            Q_total = Σ Q_actual
        """

        def calculate_total_flow(H_system: float) -> float:
            """给定系统扬程，计算总流量"""
            Q_total = 0.0

            for pump_id in pump_ids:
                if pump_id not in self._pump_inverse_curves:
                    raise ValueError(f"泵 {pump_id} 未注册逆函数")

                freq = frequencies.get(pump_id, 50.0)
                inverse_func = self._pump_inverse_curves[pump_id]

                # 1. 将实际扬程归一化到50Hz
                H_50 = H_system * (50 / freq) ** 2

                # 2. 使用50Hz逆函数计算Q_50
                Q_50 = inverse_func(H_50)

                # 3. 反归一化到实际频率
                Q_actual = Q_50 * (freq / 50)

                Q_total += Q_actual

                self._logger.debug(
                    f"[VFD合成] pump={pump_id}, freq={freq}Hz, "
                    f"H_system={H_system:.1f}m → H_50={H_50:.1f}m → "
                    f"Q_50={Q_50:.1f} → Q_actual={Q_actual:.1f}"
                )

            self._logger.info(
                f"[VFD合成] H_system={H_system:.1f}m, "
                f"pumps={pump_ids}, Q_total={Q_total:.1f}m³/h"
            )

            return Q_total

        return calculate_total_flow

    def synthesize_heterogeneous(
        self,
        pump_ids: List[int],
        H_system: float,
        pump_frequencies: Optional[Dict[int, float]] = None
    ) -> SynthesisResult:
        """
        异构泵组合成（给定系统扬程，计算各泵流量、功率、效率）

        Args:
            pump_ids: 运行中的泵ID列表
            H_system: 系统扬程
            pump_frequencies: 各泵运行频率 {pump_id: freq_Hz}
                - 如果不提供或泵不在字典中，默认50Hz（工频）
                - 非50Hz时应用相似定律：Q∝f, H∝f², P∝f³

        Returns:
            SynthesisResult: 合成结果（含功率和效率，以及_rated_powers）

        Raises:
            HeadOutOfRangeError: 系统扬程超出泵的有效范围时抛出
            ValueError: 泵曲线未注册
        """
        pump_flows = {}
        pump_powers = {}
        Q_total = 0.0
        P_total = 0.0

        for pump_id in pump_ids:
            if pump_id not in self._pump_inverse_curves:
                raise ValueError(f"泵 {pump_id} 未注册逆函数")

            inverse_func = self._pump_inverse_curves[pump_id]
            # 获取泵的运行频率
            f_actual = (
                pump_frequencies.get(pump_id, 50.0) if pump_frequencies else 50.0
            )

            try:
                if f_actual != 50.0:
                    # 变频泵：应用相似定律
                    # 将系统扬程归一化到50Hz：H_50 = H_system × (50/f)²
                    H_50hz = H_system * (50.0 / f_actual) ** 2
                    Q_50hz = inverse_func(H_50hz)
                    # 反归一化到实际频率：Q_actual = Q_50 × (f/50)
                    Q_i = Q_50hz * (f_actual / 50.0)
                else:
                    # 工频泵：直接使用曲线
                    Q_i = inverse_func(H_system)

                if Q_i <= 0:
                    H_max = self._get_pump_h_max(pump_id)
                    raise HeadOutOfRangeError(
                        message=f"系统扬程 H={H_system}m 超出泵 {pump_id} 的有效范围",
                        H_system=H_system,
                        H_min=0.0,
                        H_max=H_max,
                        pump_id=pump_id,
                    )
            except (ValueError, RuntimeError) as e:
                raise HeadOutOfRangeError(
                    message=f"系统扬程 H={H_system}m 超出泵 {pump_id} 的有效范围: {e}",
                    H_system=H_system,
                    H_min=0.0,
                    H_max=float("inf"),
                    pump_id=pump_id,
                )

            pump_flows[pump_id] = Q_i
            Q_total += Q_i

            # 计算各泵功率，传递frequency参数
            P_i = self._calculate_pump_power(
                pump_id, Q_i, H_system, frequency=f_actual
            )
            pump_powers[pump_id] = P_i
            P_total += P_i

        # 计算总效率
        eta_total = self._calculate_total_efficiency(Q_total, H_system, P_total)

        self._logger.info(
            f"[异构合成] pumps={pump_ids}, H={H_system:.1f}m, "
            f"freqs={pump_frequencies} → "
            f"Q_total={Q_total:.1f}m³/h, P_total={P_total:.2f}kW, η={eta_total:.2%}"
        )

        # 创建结果并设置_rated_powers
        result = SynthesisResult(
            Q_total=Q_total,
            H_system=H_system,
            pump_flows=pump_flows,
            pump_heads={pid: H_system for pid in pump_ids},
            pump_powers=pump_powers,
            P_total=P_total,
            eta_total=eta_total,
        )
        result._rated_powers = {
            pid: self._pump_rated_powers.get(pid, 0) for pid in pump_ids
        }
        return result

    def find_operating_point(
        self,
        pump_ids: List[int],
        system_curve: Callable[[float], float],
        Q_range: Tuple[float, float] = (100, 5000),
        pump_frequencies: Optional[Dict[int, float]] = None
    ) -> SynthesisResult:
        """
        求解泵组与管网的交点（工作点）

        Args:
            pump_ids: 运行中的泵ID列表
            system_curve: 管网曲线 Q → H_system
            Q_range: 流量搜索范围
            pump_frequencies: 各泵运行频率

        Returns:
            SynthesisResult: 工作点
        """

        def residual(Q_total: float) -> float:
            """残差函数：泵组流量 - 假设流量"""
            H_system = system_curve(Q_total)
            result = self.synthesize_heterogeneous(
                pump_ids, H_system, pump_frequencies
            )
            return result.Q_total - Q_total

        try:
            Q_op = brentq(residual, Q_range[0], Q_range[1])
            H_op = system_curve(Q_op)
            return self.synthesize_heterogeneous(pump_ids, H_op, pump_frequencies)
        except ValueError as e:
            self._logger.error(f"[并联合成] 无法找到工作点: {e}")
            raise

    def synthesize_mixed(
        self,
        vfd_pump_ids: List[int],
        ss_pump_ids: List[int],
        pump_frequencies: Dict[int, float],
        H_system: float
    ) -> SynthesisResult:
        """
        混合泵组合成（变频泵+软启泵）

        Args:
            vfd_pump_ids: 变频泵ID列表
            ss_pump_ids: 软启泵ID列表
            pump_frequencies: 各变频泵的实际频率
            H_system: 系统扬程

        Returns:
            SynthesisResult: 合成结果（含功率和效率）

        Raises:
            HeadOutOfRangeError: 当H_system超出所有泵的有效扬程范围时抛出
        """
        # 扬程范围检查
        all_pump_ids = vfd_pump_ids + ss_pump_ids
        for pump_id in all_pump_ids:
            if pump_id in self._pump_H_ranges:
                H_min, H_max = self._pump_H_ranges[pump_id]
                # 对于变频泵，需要根据频率调整有效范围
                if pump_id in vfd_pump_ids:
                    f_actual = pump_frequencies.get(pump_id, 50.0)
                    H_min_adj = H_min * (f_actual / 50.0) ** 2
                    H_max_adj = H_max * (f_actual / 50.0) ** 2
                else:
                    H_min_adj, H_max_adj = H_min, H_max

                if not (H_min_adj <= H_system <= H_max_adj):
                    raise HeadOutOfRangeError(
                        message=(
                            f"泵{pump_id}扬程范围[{H_min_adj:.1f}, {H_max_adj:.1f}]m，"
                            f"系统扬程{H_system:.1f}m超出范围"
                        ),
                        H_system=H_system,
                        H_min=H_min_adj,
                        H_max=H_max_adj,
                        pump_id=pump_id,
                    )

        pump_flows = {}
        pump_powers = {}
        Q_total = 0.0
        P_total = 0.0

        # 处理变频泵（需要频率反归一化）
        for pump_id in vfd_pump_ids:
            f_actual = pump_frequencies.get(pump_id, 50.0)

            # 将系统扬程归一化到50Hz
            H_50hz = H_system * (50.0 / f_actual) ** 2

            # 在50Hz曲线上求流量
            inverse_func = self._pump_inverse_curves[pump_id]
            Q_50hz = inverse_func(H_50hz)

            # 反归一化到实际频率
            Q_actual = Q_50hz * (f_actual / 50.0)
            pump_flows[pump_id] = Q_actual
            Q_total += Q_actual

            # 计算功率，传递frequency参数（P ∝ f³）
            P_i = self._calculate_pump_power(
                pump_id, Q_actual, H_system, frequency=f_actual
            )
            pump_powers[pump_id] = P_i
            P_total += P_i

        # 处理软启泵（直接使用曲线，工频50Hz）
        for pump_id in ss_pump_ids:
            inverse_func = self._pump_inverse_curves[pump_id]
            Q_i = inverse_func(H_system)
            pump_flows[pump_id] = Q_i
            Q_total += Q_i

            # 计算功率（软启泵固定50Hz）
            P_i = self._calculate_pump_power(
                pump_id, Q_i, H_system, frequency=50.0
            )
            pump_powers[pump_id] = P_i
            P_total += P_i

        # 计算总效率
        eta_total = self._calculate_total_efficiency(Q_total, H_system, P_total)

        self._logger.info(
            f"[混合合成] VFD={vfd_pump_ids}, SS={ss_pump_ids}, "
            f"H={H_system:.1f}m → "
            f"Q_total={Q_total:.1f}m³/h, P_total={P_total:.2f}kW, η={eta_total:.2%}"
        )

        # 创建结果并设置_rated_powers
        result = SynthesisResult(
            Q_total=Q_total,
            H_system=H_system,
            pump_flows=pump_flows,
            pump_heads={pid: H_system for pid in all_pump_ids},
            pump_powers=pump_powers,
            P_total=P_total,
            eta_total=eta_total,
        )
        result._rated_powers = {
            pid: self._pump_rated_powers.get(pid, 0) for pid in all_pump_ids
        }
        return result

    def synthesize_mixed_weighted(
        self,
        pump_infos: List[Dict[str, Any]],
        pump_frequencies: Dict[int, float],
        H_system: float
    ) -> WeightedSynthesisResult:
        """
        加权混合合成

        用于MIXED_HETEROGENEOUS场景，考虑功率差异对流量分配的影响。

        Args:
            pump_infos: 泵信息列表，包含 {'pump_id', 'rated_power', 'control_type'}
            pump_frequencies: 各变频泵的实际频率
            H_system: 系统扬程

        Returns:
            WeightedSynthesisResult: 包含功率权重信息的合成结果

        Raises:
            HeadOutOfRangeError: 当H_system超出所有泵的有效扬程范围时抛出
        """
        # 1. 计算功率权重（基于额定功率）
        rated_powers = {p["pump_id"]: p["rated_power"] for p in pump_infos}
        total_rated_power = sum(rated_powers.values())
        power_weights = {
            pid: pwr / total_rated_power for pid, pwr in rated_powers.items()
        }

        # 2. 分类泵
        vfd_infos = [p for p in pump_infos if p.get("control_type") == "VFD"]
        ss_infos = [p for p in pump_infos if p.get("control_type") == "SS"]

        vfd_pump_ids = [p["pump_id"] for p in vfd_infos]
        ss_pump_ids = [p["pump_id"] for p in ss_infos]

        # 扬程范围检查
        all_pump_ids = vfd_pump_ids + ss_pump_ids
        for pump_id in all_pump_ids:
            if pump_id in self._pump_H_ranges:
                H_min, H_max = self._pump_H_ranges[pump_id]
                if pump_id in vfd_pump_ids:
                    f_actual = pump_frequencies.get(pump_id, 50.0)
                    H_min_adj = H_min * (f_actual / 50.0) ** 2
                    H_max_adj = H_max * (f_actual / 50.0) ** 2
                else:
                    H_min_adj, H_max_adj = H_min, H_max

                if not (H_min_adj <= H_system <= H_max_adj):
                    raise HeadOutOfRangeError(
                        message=(
                            f"泵{pump_id}扬程范围[{H_min_adj:.1f}, {H_max_adj:.1f}]m，"
                            f"系统扬程{H_system:.1f}m超出范围"
                        ),
                        H_system=H_system,
                        H_min=H_min_adj,
                        H_max=H_max_adj,
                        pump_id=pump_id,
                    )

        # 3. 计算各泵流量和功率
        pump_flows = {}
        pump_powers = {}
        Q_total = 0.0
        P_total = 0.0

        # 处理变频泵
        for pump_id in vfd_pump_ids:
            f_actual = pump_frequencies.get(pump_id, 50.0)
            H_50hz = H_system * (50.0 / f_actual) ** 2
            inverse_func = self._pump_inverse_curves[pump_id]
            Q_50hz = inverse_func(H_50hz)
            Q_actual = Q_50hz * (f_actual / 50.0)
            pump_flows[pump_id] = Q_actual
            Q_total += Q_actual

            P_i = self._calculate_pump_power(
                pump_id, Q_actual, H_system, frequency=f_actual
            )
            pump_powers[pump_id] = P_i
            P_total += P_i

        # 处理软启泵
        for pump_id in ss_pump_ids:
            inverse_func = self._pump_inverse_curves[pump_id]
            Q_i = inverse_func(H_system)
            pump_flows[pump_id] = Q_i
            Q_total += Q_i

            P_i = self._calculate_pump_power(
                pump_id, Q_i, H_system, frequency=50.0
            )
            pump_powers[pump_id] = P_i
            P_total += P_i

        # 4. 计算流量权重
        flow_weights = (
            {pid: flow / Q_total for pid, flow in pump_flows.items()}
            if Q_total > 0
            else {}
        )

        # 5. 计算功率-流量比例差异
        power_flow_ratios = {}
        for pid in pump_flows.keys():
            if flow_weights.get(pid, 0) > 0:
                power_flow_ratios[pid] = power_weights[pid] / flow_weights[pid]

        # 6. 计算VFD子组统计信息
        vfd_stats: Dict[str, float] = {}
        if len(vfd_infos) > 1:
            vfd_powers = [p["rated_power"] for p in vfd_infos]
            vfd_freqs = [
                pump_frequencies.get(p["pump_id"], 50.0) for p in vfd_infos
            ]
            vfd_stats = {
                "power_std": float(np.std(vfd_powers)),
                "power_ratio": max(vfd_powers) / min(vfd_powers),
                "freq_std": float(np.std(vfd_freqs)),
                "freq_range": max(vfd_freqs) - min(vfd_freqs),
            }

        # 7. 计算总效率
        eta_total = self._calculate_total_efficiency(Q_total, H_system, P_total)

        self._logger.info(
            f"[加权混合合成] VFD={vfd_pump_ids}, SS={ss_pump_ids}, "
            f"H={H_system:.1f}m → "
            f"Q_total={Q_total:.1f}m³/h, P_total={P_total:.2f}kW, η={eta_total:.2%}"
        )

        # 创建结果
        result = WeightedSynthesisResult(
            Q_total=Q_total,
            H_system=H_system,
            pump_flows=pump_flows,
            pump_heads={pid: H_system for pid in pump_flows.keys()},
            pump_powers=pump_powers,
            P_total=P_total,
            eta_total=eta_total,
            power_weights=power_weights,
            flow_weights=flow_weights,
            power_flow_ratios=power_flow_ratios,
            vfd_stats=vfd_stats,
        )
        result._rated_powers = rated_powers
        return result

    def synthesize_mixed_auto(
        self,
        vfd_pump_ids: List[int],
        ss_pump_ids: List[int],
        H_system: float,
        freq_provider: Any
    ) -> SynthesisResult:
        """
        混合泵组合成（自动获取频率）

        Args:
            vfd_pump_ids: 变频泵ID列表
            ss_pump_ids: 软启泵ID列表
            H_system: 系统扬程
            freq_provider: 频率数据提供器（FrequencyDataProvider实例）

        Returns:
            SynthesisResult: 合成结果
        """
        # 自动获取各变频泵的频率
        pump_frequencies = freq_provider.get_latest_frequencies(vfd_pump_ids)

        # 调用原有方法
        return self.synthesize_mixed(
            vfd_pump_ids=vfd_pump_ids,
            ss_pump_ids=ss_pump_ids,
            pump_frequencies=pump_frequencies,
            H_system=H_system,
        )

