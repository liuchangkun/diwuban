"""并联合成器 (app.services.characteristic_curves.pump_group.parallel_synthesizer)

从单泵曲线合成泵组曲线的核心组件。

核心功能：
- 同构泵组合成（synthesize_homogeneous）
- 异构泵组合成（synthesize_heterogeneous）
- VFD频率异构合成（synthesize_vfd_with_freq）
- 混合泵组合成（synthesize_mixed）
- 加权混合合成（synthesize_mixed_weighted）
- 台数特性曲线生成（generate_n_q_curve, generate_n_p_curve, generate_n_eta_curve）

版本: v1.0
创建日期: 2025-12-14
参考文档: 07_泵组处理层.md 第3节
"""

import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from app.services.characteristic_curves.core.data_structures import (
    SynthesisResult,
    GroupProcessingStrategy,
)
from app.services.characteristic_curves.shared.exceptions import (
    HeadOutOfRangeError,
    MissingCurveError,
)


logger = logging.getLogger(__name__)


class ParallelSynthesizer:
    """并联合成器

    职责：
    1. 从单泵曲线合成泵组曲线
    2. 支持同构/异构/混合泵组
    3. 计算泵组效率和功率
    """

    def __init__(self):
        """初始化"""
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}")

        # 单泵曲线注册表: {pump_id: {'qh_func': ..., 'inverse_func': ..., 'power_func': ...}}
        self._pump_curves: Dict[int, Dict[str, Callable]] = {}
        # 单泵扬程范围: {pump_id: (H_min, H_max)}
        self._pump_H_ranges: Dict[int, Tuple[float, float]] = {}
        # 额定功率: {pump_id: rated_power_kw}
        self._pump_rated_powers: Dict[int, float] = {}

        self._logger.info("[并联合成器] 初始化完成")

    def register_pump_curve(
        self,
        pump_id: int,
        curve_func: Callable[[float], float],
        inverse_func: Callable[[float], float],
        power_func: Optional[Callable[[float], float]] = None,
        H_range: Tuple[float, float] = (0, 100),
        rated_power: float = 55.0
    ) -> None:
        """注册单泵曲线

        Args:
            pump_id: 泵ID
            curve_func: Q-H曲线函数 H = f(Q)
            inverse_func: 反函数 Q = f(H)
            power_func: 功率函数 P = f(Q)，可选
            H_range: 有效扬程范围 (H_min, H_max)
            rated_power: 额定功率 (kW)
        """
        self._pump_curves[pump_id] = {
            'qh_func': curve_func,
            'inverse_func': inverse_func,
            'power_func': power_func,
        }
        self._pump_H_ranges[pump_id] = H_range
        self._pump_rated_powers[pump_id] = rated_power

        self._logger.info(
            f"[曲线注册] pump_id={pump_id}, H_range={H_range}, rated_power={rated_power}kW"
        )

    def synthesize_homogeneous(
        self,
        base_pump_id: int,
        n_pumps: int
    ) -> Callable[[float], float]:
        """同构泵组合成

        物理原理：同型号泵并联时，Q_total = n × Q_single

        Args:
            base_pump_id: 基准泵ID
            n_pumps: 运行台数

        Returns:
            Callable: 合成后的Q-H曲线函数

        Raises:
            MissingCurveError: 基准泵曲线未注册
        """
        if base_pump_id not in self._pump_curves:
            raise MissingCurveError(
                f"基准泵 {base_pump_id} 曲线未注册",
                missing_pump_ids=[base_pump_id]
            )

        base_curve = self._pump_curves[base_pump_id]['qh_func']

        def group_curve(Q_total: float) -> float:
            """泵组Q-H曲线: H = f(Q_total/n)"""
            Q_single = Q_total / n_pumps
            return base_curve(Q_single)

        self._logger.info(
            f"[同构合成] base_pump={base_pump_id}, n_pumps={n_pumps}"
        )

        return group_curve

    def synthesize_heterogeneous(
        self,
        pump_ids: List[int],
        H_system: float,
        pump_frequencies: Optional[Dict[int, float]] = None
    ) -> SynthesisResult:
        """异构泵组合成

        物理原理：并联时各泵扬程相同，Q_total = ΣQ_i

        Args:
            pump_ids: 运行泵ID列表
            H_system: 系统扬程 (m)
            pump_frequencies: 各泵运行频率 {pump_id: freq_Hz}

        Returns:
            SynthesisResult: 合成结果

        Raises:
            MissingCurveError: 某泵曲线未注册
            HeadOutOfRangeError: 扬程超出范围
        """
        # 检查曲线注册
        missing = [pid for pid in pump_ids if pid not in self._pump_curves]
        if missing:
            raise MissingCurveError(
                f"以下泵曲线未注册: {missing}",
                missing_pump_ids=missing
            )

        # 检查扬程范围
        for pump_id in pump_ids:
            H_min, H_max = self._pump_H_ranges.get(pump_id, (0, 100))
            if H_system < H_min or H_system > H_max:
                raise HeadOutOfRangeError(
                    f"泵 {pump_id} 扬程 {H_system}m 超出范围 [{H_min}, {H_max}]",
                    H_system=H_system,
                    H_min=H_min,
                    H_max=H_max,
                    pump_id=pump_id
                )

        # 计算各泵流量
        pump_flows = {}
        pump_heads = {}
        pump_powers = {}
        P_total = 0.0

        for pump_id in pump_ids:
            inverse_func = self._pump_curves[pump_id]['inverse_func']
            power_func = self._pump_curves[pump_id].get('power_func')

            # 获取频率修正比例
            freq_ratio = 1.0
            if pump_frequencies and pump_id in pump_frequencies:
                freq = pump_frequencies[pump_id]
                freq_ratio = freq / 50.0  # 相似定律

            # 计算流量: Q = inverse(H / freq_ratio²) × freq_ratio
            H_normalized = H_system / (freq_ratio ** 2)
            Q_i = inverse_func(H_normalized) * freq_ratio

            pump_flows[pump_id] = Q_i
            pump_heads[pump_id] = H_system

            # 计算功率
            if power_func:
                P_i = power_func(Q_i) * (freq_ratio ** 3)  # P ∝ f³
            else:
                # 估算功率: P = ρgQH/η，假设η=0.75
                Q_m3s = Q_i / 3600
                P_i = 1000 * 9.81 * Q_m3s * H_system / 0.75 / 1000
            pump_powers[pump_id] = P_i
            P_total += P_i

        Q_total = sum(pump_flows.values())

        # 计算总效率: η = ρgQH / P
        eta_total = 0.0
        if P_total > 0 and Q_total > 0:
            Q_m3s = Q_total / 3600
            hydraulic_power = 1000 * 9.81 * Q_m3s * H_system / 1000  # kW
            eta_total = min(hydraulic_power / P_total, 1.0)

        result = SynthesisResult(
            Q_total=Q_total,
            H_system=H_system,
            pump_flows=pump_flows,
            pump_heads=pump_heads,
            pump_powers=pump_powers,
            P_total=P_total,
            eta_total=eta_total,
            _rated_powers=self._pump_rated_powers,
        )

        self._logger.info(
            f"[异构合成] pumps={pump_ids}, H={H_system}m, "
            f"Q_total={Q_total:.1f}m³/h, P_total={P_total:.1f}kW, η={eta_total:.2%}"
        )

        return result

    def synthesize_vfd_with_freq(
        self,
        pump_ids: List[int],
        frequencies: Dict[int, float]
    ) -> Callable[[float], SynthesisResult]:
        """VFD频率异构合成

        Args:
            pump_ids: 泵ID列表
            frequencies: 各泵频率 {pump_id: freq_Hz}

        Returns:
            Callable: 输入H返回SynthesisResult的函数
        """
        def synthesize_at_H(H_system: float) -> SynthesisResult:
            return self.synthesize_heterogeneous(
                pump_ids=pump_ids,
                H_system=H_system,
                pump_frequencies=frequencies
            )

        return synthesize_at_H

    def synthesize_mixed(
        self,
        vfd_pump_ids: List[int],
        ss_pump_ids: List[int],
        pump_frequencies: Dict[int, float],
        H_system: float
    ) -> SynthesisResult:
        """混合泵组合成（VFD + SS）

        Args:
            vfd_pump_ids: 变频泵ID列表
            ss_pump_ids: 软启泵ID列表
            pump_frequencies: VFD泵频率 {pump_id: freq_Hz}
            H_system: 系统扬程

        Returns:
            SynthesisResult: 合成结果
        """
        # 检查曲线注册
        all_pump_ids = vfd_pump_ids + ss_pump_ids
        missing = [pid for pid in all_pump_ids if pid not in self._pump_curves]
        if missing:
            raise MissingCurveError(
                f"以下泵曲线未注册: {missing}",
                missing_pump_ids=missing
            )

        # 检查扬程范围
        for pump_id in all_pump_ids:
            H_min, H_max = self._pump_H_ranges.get(pump_id, (0, 100))
            if H_system < H_min or H_system > H_max:
                raise HeadOutOfRangeError(
                    f"泵 {pump_id} 扬程 {H_system}m 超出范围 [{H_min}, {H_max}]",
                    H_system=H_system,
                    H_min=H_min,
                    H_max=H_max,
                    pump_id=pump_id
                )

        pump_flows = {}
        pump_heads = {}
        pump_powers = {}
        P_total = 0.0

        # VFD泵：考虑频率
        for pump_id in vfd_pump_ids:
            inverse_func = self._pump_curves[pump_id]['inverse_func']
            power_func = self._pump_curves[pump_id].get('power_func')

            freq = pump_frequencies.get(pump_id, 50.0)
            freq_ratio = freq / 50.0

            H_normalized = H_system / (freq_ratio ** 2)
            Q_i = inverse_func(H_normalized) * freq_ratio

            pump_flows[pump_id] = Q_i
            pump_heads[pump_id] = H_system

            if power_func:
                P_i = power_func(Q_i) * (freq_ratio ** 3)
            else:
                Q_m3s = Q_i / 3600
                P_i = 1000 * 9.81 * Q_m3s * H_system / 0.75 / 1000
            pump_powers[pump_id] = P_i
            P_total += P_i

        # SS泵：固定50Hz
        for pump_id in ss_pump_ids:
            inverse_func = self._pump_curves[pump_id]['inverse_func']
            power_func = self._pump_curves[pump_id].get('power_func')

            Q_i = inverse_func(H_system)
            pump_flows[pump_id] = Q_i
            pump_heads[pump_id] = H_system

            if power_func:
                P_i = power_func(Q_i)
            else:
                Q_m3s = Q_i / 3600
                P_i = 1000 * 9.81 * Q_m3s * H_system / 0.75 / 1000
            pump_powers[pump_id] = P_i
            P_total += P_i

        Q_total = sum(pump_flows.values())

        eta_total = 0.0
        if P_total > 0 and Q_total > 0:
            Q_m3s = Q_total / 3600
            hydraulic_power = 1000 * 9.81 * Q_m3s * H_system / 1000
            eta_total = min(hydraulic_power / P_total, 1.0)

        result = SynthesisResult(
            Q_total=Q_total,
            H_system=H_system,
            pump_flows=pump_flows,
            pump_heads=pump_heads,
            pump_powers=pump_powers,
            P_total=P_total,
            eta_total=eta_total,
            _rated_powers=self._pump_rated_powers,
        )

        self._logger.info(
            f"[混合合成] VFD={vfd_pump_ids}, SS={ss_pump_ids}, "
            f"Q_total={Q_total:.1f}m³/h"
        )

        return result

    def synthesize_mixed_weighted(
        self,
        pump_infos: List[Dict[str, Any]],
        pump_frequencies: Dict[int, float],
        H_system: float
    ) -> SynthesisResult:
        """加权混合泵组合成

        Args:
            pump_infos: 泵信息列表 [{'pump_id': int, 'control_type': str, 'rated_power': float}]
            pump_frequencies: VFD泵频率
            H_system: 系统扬程

        Returns:
            SynthesisResult: 合成结果（含功率权重和流量权重）
        """
        vfd_pump_ids = [p['pump_id']
                        for p in pump_infos if p.get('control_type') == 'VFD']
        ss_pump_ids = [p['pump_id']
                       for p in pump_infos if p.get('control_type') == 'SS']

        result = self.synthesize_mixed(
            vfd_pump_ids=vfd_pump_ids,
            ss_pump_ids=ss_pump_ids,
            pump_frequencies=pump_frequencies,
            H_system=H_system
        )

        # 添加权重信息
        total_rated_power = sum(p.get('rated_power', 55.0) for p in pump_infos)
        power_weights = {
            p['pump_id']: p.get('rated_power', 55.0) / total_rated_power
            for p in pump_infos
        }

        flow_weights = {
            pid: Q / result.Q_total if result.Q_total > 0 else 0
            for pid, Q in result.pump_flows.items()
        }

        # 将权重信息存储在结果中（通过动态属性）
        result.__dict__['power_weights'] = power_weights
        result.__dict__['flow_weights'] = flow_weights

        return result

    def generate_n_q_curve(
        self,
        pump_ids: List[int],
        H_system: float,
        max_pumps: Optional[int] = None,
        selection_strategy: str = 'sequential',
        pump_infos: Optional[Dict[int, Dict]] = None,
        pump_frequencies: Optional[Dict[int, float]] = None
    ) -> Dict[str, Any]:
        """生成台数-流量曲线(N-Q)

        Args:
            pump_ids: 候选泵ID列表
            H_system: 系统扬程 (m)
            max_pumps: 最大台数（默认为len(pump_ids)）
            selection_strategy: 泵选择策略
            pump_infos: 泵信息字典
            pump_frequencies: 运行频率字典

        Returns:
            Dict[str, Any]: 包含data, selection_strategy, H_system
        """
        if max_pumps is None:
            max_pumps = len(pump_ids)

        data = []

        for n in range(1, max_pumps + 1):
            selected = self._select_pumps(
                pump_ids, n, H_system, selection_strategy, pump_infos, pump_frequencies
            )

            try:
                result = self.synthesize_heterogeneous(
                    pump_ids=selected,
                    H_system=H_system,
                    pump_frequencies=pump_frequencies
                )

                data.append({
                    'N': n,
                    'Q_total': result.Q_total,
                    'selected_pumps': selected,
                    'synthesis_method': 'heterogeneous'
                })
            except Exception as e:
                self._logger.warning(f"[N-Q曲线] N={n}合成失败: {e}")

        return {
            'data': data,
            'selection_strategy': selection_strategy,
            'H_system': H_system,
            'generated_at': datetime.now().isoformat()
        }

    def generate_n_p_curve(
        self,
        pump_ids: List[int],
        H_system: float,
        max_pumps: Optional[int] = None,
        selection_strategy: str = 'sequential',
        pump_infos: Optional[Dict[int, Dict]] = None,
        pump_frequencies: Optional[Dict[int, float]] = None
    ) -> Dict[str, Any]:
        """生成台数-功率曲线(N-P)"""
        if max_pumps is None:
            max_pumps = len(pump_ids)

        data = []

        for n in range(1, max_pumps + 1):
            selected = self._select_pumps(
                pump_ids, n, H_system, selection_strategy, pump_infos, pump_frequencies
            )

            try:
                result = self.synthesize_heterogeneous(
                    pump_ids=selected,
                    H_system=H_system,
                    pump_frequencies=pump_frequencies
                )

                data.append({
                    'N': n,
                    'P_total': result.P_total,
                    'selected_pumps': selected
                })
            except Exception as e:
                self._logger.warning(f"[N-P曲线] N={n}合成失败: {e}")

        return {
            'data': data,
            'selection_strategy': selection_strategy,
            'H_system': H_system,
            'generated_at': datetime.now().isoformat()
        }

    def generate_n_eta_curve(
        self,
        pump_ids: List[int],
        H_system: float,
        max_pumps: Optional[int] = None,
        selection_strategy: str = 'sequential',
        pump_infos: Optional[Dict[int, Dict]] = None,
        pump_frequencies: Optional[Dict[int, float]] = None
    ) -> Dict[str, Any]:
        """生成台数-效率曲线(N-η)"""
        if max_pumps is None:
            max_pumps = len(pump_ids)

        data = []

        for n in range(1, max_pumps + 1):
            selected = self._select_pumps(
                pump_ids, n, H_system, selection_strategy, pump_infos, pump_frequencies
            )

            try:
                result = self.synthesize_heterogeneous(
                    pump_ids=selected,
                    H_system=H_system,
                    pump_frequencies=pump_frequencies
                )

                # 各泵效率
                eta_per_pump = {}
                for pump_id in selected:
                    Q_i = result.pump_flows.get(pump_id, 0)
                    P_i = result.pump_powers.get(pump_id, 0)
                    if P_i > 0 and Q_i > 0:
                        Q_m3s = Q_i / 3600
                        eta_i = 1000 * 9.81 * Q_m3s * H_system / 1000 / P_i
                        eta_per_pump[pump_id] = min(eta_i, 1.0)

                data.append({
                    'N': n,
                    'eta_total': result.eta_total,
                    'selected_pumps': selected,
                    'eta_per_pump': eta_per_pump
                })
            except Exception as e:
                self._logger.warning(f"[N-η曲线] N={n}合成失败: {e}")

        return {
            'data': data,
            'selection_strategy': selection_strategy,
            'H_system': H_system,
            'generated_at': datetime.now().isoformat()
        }

    def find_optimal_region(
        self,
        pump_ids: List[int],
        H_range: Tuple[float, float] = (25, 50),
        Q_range: Tuple[float, float] = (500, 2000),
        efficiency_threshold: float = 0.75,
        step: float = 1.0,
        pump_frequencies: Optional[Dict[int, float]] = None
    ) -> Dict[str, Any]:
        """找到最优运行区域

        Args:
            pump_ids: 泵ID列表
            H_range: 扬程扫描范围
            Q_range: 流量过滤范围
            efficiency_threshold: 效率阈值
            step: 扫描步长
            pump_frequencies: 运行频率

        Returns:
            Dict: 包含region_points, bep, boundary
        """
        region_points = []
        best_point = None
        best_eta = 0.0

        H_values = np.arange(H_range[0], H_range[1] + step, step)

        for H in H_values:
            for n in range(1, len(pump_ids) + 1):
                selected = pump_ids[:n]
                try:
                    result = self.synthesize_heterogeneous(
                        selected, float(H), pump_frequencies
                    )

                    if result.eta_total >= efficiency_threshold:
                        point = {
                            'H': float(H),
                            'Q': result.Q_total,
                            'eta': result.eta_total,
                            'N': n
                        }
                        region_points.append(point)

                        if result.eta_total > best_eta:
                            best_eta = result.eta_total
                            best_point = point
                except Exception:
                    continue

        boundary = None
        if region_points:
            boundary = {
                'H_min': min(p['H'] for p in region_points),
                'H_max': max(p['H'] for p in region_points),
                'Q_min': min(p['Q'] for p in region_points),
                'Q_max': max(p['Q'] for p in region_points)
            }

        return {
            'region_points': region_points,
            'bep': best_point,
            'boundary': boundary,
            'efficiency_threshold': efficiency_threshold,
            'pump_ids': pump_ids,
            'H_range': list(H_range),
            'generated_at': datetime.now().isoformat()
        }

    def _select_pumps(
        self,
        pump_ids: List[int],
        n: int,
        H_system: float,
        strategy: str,
        pump_infos: Optional[Dict[int, Dict]] = None,
        pump_frequencies: Optional[Dict[int, float]] = None
    ) -> List[int]:
        """根据策略选择n台泵

        Args:
            pump_ids: 候选泵ID列表
            n: 需要选择的泵数量
            H_system: 系统扬程
            strategy: 选择策略 ('sequential', 'best_efficiency', 'lowest_power')
            pump_infos: 泵信息
            pump_frequencies: 运行频率

        Returns:
            List[int]: 选中的泵ID列表
        """
        if n >= len(pump_ids):
            return pump_ids

        if strategy == 'sequential':
            return pump_ids[:n]

        elif strategy == 'best_efficiency':
            # 按效率排序选择
            efficiencies = []
            for pump_id in pump_ids:
                try:
                    result = self.synthesize_heterogeneous(
                        [pump_id], H_system, pump_frequencies
                    )
                    efficiencies.append((pump_id, result.eta_total))
                except Exception:
                    efficiencies.append((pump_id, 0.0))

            efficiencies.sort(key=lambda x: x[1], reverse=True)
            return [pid for pid, _ in efficiencies[:n]]

        elif strategy == 'lowest_power':
            # 按功率排序选择
            powers = []
            for pump_id in pump_ids:
                try:
                    result = self.synthesize_heterogeneous(
                        [pump_id], H_system, pump_frequencies
                    )
                    powers.append((pump_id, result.P_total))
                except Exception:
                    powers.append((pump_id, float('inf')))

            powers.sort(key=lambda x: x[1])
            return [pid for pid, _ in powers[:n]]

        else:
            return pump_ids[:n]

    def _calculate_pump_power(
        self,
        pump_id: int,
        Q: float,
        H: float,
        frequency: float = 50.0
    ) -> float:
        """计算单泵功率

        Args:
            pump_id: 泵ID
            Q: 流量 (m³/h)
            H: 扬程 (m)
            frequency: 运行频率 (Hz)

        Returns:
            float: 功率 (kW)
        """
        freq_ratio = frequency / 50.0

        if pump_id in self._pump_curves:
            power_func = self._pump_curves[pump_id].get('power_func')
            if power_func:
                return power_func(Q) * (freq_ratio ** 3)

        # 默认估算
        Q_m3s = Q / 3600
        eta = 0.75  # 假设效率
        return 1000 * 9.81 * Q_m3s * H / eta / 1000 * (freq_ratio ** 3)

    def generate_specific_energy_curve(
        self,
        pump_ids: List[int],
        H_range: Tuple[float, float] = (20, 60),
        step: float = 2.0,
        pump_frequencies: Optional[Dict[int, float]] = None
    ) -> Dict[str, Any]:
        """生成比能耗曲线（SEC vs H）【第14条曲线】

        比能耗(SEC, Specific Energy Consumption)：
        - 定义：单位流量的能耗 (kWh/m³)
        - 公式：SEC = P / Q
        - 物理意义：泵送1m³水所消耗的电能

        Args:
            pump_ids: 运行泵ID列表
            H_range: 扬程扫描范围 (m)
            step: 扫描步长 (m)
            pump_frequencies: 各泵运行频率 {pump_id: freq_Hz}

        Returns:
            Dict[str, Any]: {
                'curve_data': [{'H': 20, 'Q': 1800, 'P': 180, 'SEC': 0.100}, ...],
                'min_sec': {'H': 35, 'Q': 1200, 'P': 155, 'SEC': 0.129},
                'avg_sec': 0.125,
                'pump_ids': [...],
                'H_range': [...],
                'unit_sec': 'kWh/m³',
                'generated_at': '...'
            }
        """
        curve_data = []
        H_values = np.arange(H_range[0], H_range[1] + step, step)

        for H in H_values:
            try:
                result = self.synthesize_heterogeneous(
                    pump_ids=pump_ids,
                    H_system=float(H),
                    pump_frequencies=pump_frequencies
                )
                Q = result.Q_total
                P = result.P_total

                if Q > 0:
                    sec = P / Q  # kWh/m³
                    curve_data.append({
                        'H': float(H),
                        'Q': Q,
                        'P': P,
                        'SEC': sec
                    })
            except Exception as e:
                self._logger.warning(f"[比能耗曲线] H={H}m 计算失败: {e}")
                continue

        if not curve_data:
            return {
                'curve_data': [],
                'min_sec': None,
                'avg_sec': None,
                'pump_ids': pump_ids,
                'H_range': list(H_range),
                'unit_sec': 'kWh/m³',
                'generated_at': datetime.now().isoformat()
            }

        min_point = min(curve_data, key=lambda x: x['SEC'])
        avg_sec = sum(p['SEC'] for p in curve_data) / len(curve_data)

        self._logger.info(
            f"[比能耗曲线] pumps={pump_ids}, H={H_range}, "
            f"min_SEC={min_point['SEC']:.4f}kWh/m³ @ H={min_point['H']}m"
        )

        return {
            'curve_data': curve_data,
            'min_sec': min_point,
            'avg_sec': avg_sec,
            'pump_ids': pump_ids,
            'H_range': list(H_range),
            'unit_sec': 'kWh/m³',
            'generated_at': datetime.now().isoformat()
        }

    def _calculate_total_efficiency(
        self,
        Q_total: float,
        H_system: float,
        P_total: float
    ) -> float:
        """计算泵组总效率

        Args:
            Q_total: 总流量 (m³/h)
            H_system: 系统扬程 (m)
            P_total: 总功率 (kW)

        Returns:
            float: 总效率 (0-1)
        """
        if P_total <= 0 or Q_total <= 0:
            return 0.0

        Q_m3s = Q_total / 3600
        hydraulic_power = 1000 * 9.81 * Q_m3s * H_system / 1000  # kW
        return min(hydraulic_power / P_total, 1.0)
