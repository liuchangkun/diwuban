"""
泵组切换时机分析器 (app.services.characteristic_curves.pump_group.switching_timing_analyzer)

实现第11条曲线：泵组切换时机曲线。
确定从N台运行切换到N±1台运行的最佳时机。

核心功能：
- 分析效率交叉点
- 确定切换区间（含滞回）
- 生成效率对比曲线
- 支持变频泵

物理原理：
- 效率交叉点：η(N, Q) = η(N+1, Q) 的流量Q_crossover
- 滞回区间：[Q_crossover - Δ, Q_crossover + Δ]，防止频繁切换

版本: v1.0
创建日期: 2025-12-14
"""

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class SwitchingTimingAnalyzer:
    """泵组切换时机分析器

    分析不同台数运行时的效率曲线，找出效率交叉点，
    确定最佳切换时机和切换区间。

    应用场景：
    - 优化切换点
    - 减少频繁切换
    - 提高运行稳定性
    """

    def __init__(
        self,
        synthesizer: Any,  # ParallelSynthesizer
        system_curve_func: Optional[Callable[[float], float]] = None,
        pump_frequencies: Optional[Dict[int, float]] = None,
        hysteresis: float = 50.0
    ):
        """
        Args:
            synthesizer: 并联合成器
            system_curve_func: 系统曲线函数 H = f(Q)，用于给定Q求H
            pump_frequencies: 各泵运行频率
            hysteresis: 滞回宽度 (m³/h)，防止频繁切换
        """
        self._synthesizer = synthesizer
        self._system_curve_func = system_curve_func
        self._pump_frequencies = pump_frequencies
        self._hysteresis = hysteresis

    def analyze(
        self,
        pump_ids: List[int],
        H_range: Tuple[float, float] = (20.0, 60.0),
        Q_range: Tuple[float, float] = (100.0, 3000.0),
        step: float = 10.0
    ) -> Dict[str, Any]:
        """
        分析切换时机

        物理原理：
        1. 给定目标流量Q_target
        2. 反向求解对应的系统扬程H（通过系统曲线或二分法）
        3. 在该工作点计算泵组效率
        4. 比较不同台数在同一流量下的效率

        Args:
            pump_ids: 候选泵ID列表
            H_range: 扬程搜索范围 (m)
            Q_range: 流量分析范围 (m³/h)
            step: 流量步长 (m³/h)

        Returns:
            {
                'crossover_points': [
                    {'from_N': 1, 'to_N': 2, 'Q_crossover': 550.0, 'eta_at_crossover': 0.78},
                    ...
                ],
                'switching_zones': [
                    {'from_N': 1, 'to_N': 2, 'Q_min': 500.0, 'Q_max': 600.0},
                    ...
                ],
                'efficiency_curves': {...}
            }
        """
        import numpy as np

        Q_values = np.arange(Q_range[0], Q_range[1] + step, step)
        max_pumps = len(pump_ids)

        # 计算各台数下的效率曲线
        efficiency_curves: Dict[int, List[Dict]] = {
            n: [] for n in range(1, max_pumps + 1)}

        for n in range(1, max_pumps + 1):
            selected = pump_ids[:n]
            for Q_target in Q_values:
                try:
                    # 给定Q_target，反向求解工作点
                    point = self._find_operating_point(
                        selected, float(Q_target), H_range)
                    if point is not None:
                        efficiency_curves[n].append({
                            'Q': float(Q_target),
                            'H': point['H'],
                            'eta': point['eta']
                        })
                    else:
                        # 该台数无法达到目标流量
                        efficiency_curves[n].append({
                            'Q': float(Q_target),
                            'H': None,
                            'eta': None
                        })
                except Exception as e:
                    logger.debug(f"计算N={n}, Q={Q_target}时出错: {e}")
                    efficiency_curves[n].append({
                        'Q': float(Q_target),
                        'H': None,
                        'eta': None
                    })

        # 找效率交叉点
        crossover_points = []
        for n in range(1, max_pumps):
            crossover = self._find_crossover(
                efficiency_curves[n],
                efficiency_curves[n + 1],
                n, n + 1
            )
            if crossover:
                crossover_points.append(crossover)

        # 生成切换区间（含滞回）
        switching_zones = [
            {
                'from_N': cp['from_N'],
                'to_N': cp['to_N'],
                'Q_min': round(cp['Q_crossover'] - self._hysteresis, 1),
                'Q_max': round(cp['Q_crossover'] + self._hysteresis, 1)
            }
            for cp in crossover_points
        ]

        return {
            'crossover_points': crossover_points,
            'switching_zones': switching_zones,
            'efficiency_curves': efficiency_curves,
            'hysteresis': self._hysteresis,
            'pump_ids': pump_ids,
            'generated_at': datetime.now().isoformat()
        }

    def _find_crossover(
        self,
        curve_n: List[Dict],
        curve_n_plus_1: List[Dict],
        n: int,
        n_plus_1: int
    ) -> Optional[Dict]:
        """找两条效率曲线的交叉点"""
        for i in range(len(curve_n) - 1):
            eta_n_curr = curve_n[i].get('eta')
            eta_n_next = curve_n[i + 1].get('eta')
            eta_np1_curr = curve_n_plus_1[i].get(
                'eta') if i < len(curve_n_plus_1) else None
            eta_np1_next = curve_n_plus_1[i + 1].get(
                'eta') if i + 1 < len(curve_n_plus_1) else None

            if all(v is not None for v in [eta_n_curr, eta_n_next, eta_np1_curr, eta_np1_next]):
                # 检查是否交叉
                if (eta_n_curr - eta_np1_curr) * (eta_n_next - eta_np1_next) < 0:
                    Q_crossover = (curve_n[i]['Q'] + curve_n[i + 1]['Q']) / 2
                    eta_at_crossover = (eta_n_curr + eta_np1_curr) / 2
                    return {
                        'from_N': n,
                        'to_N': n_plus_1,
                        'Q_crossover': round(Q_crossover, 1),
                        'eta_at_crossover': round(eta_at_crossover, 4)
                    }

        return None

    def _find_operating_point(
        self,
        pump_ids: List[int],
        Q_target: float,
        H_range: Tuple[float, float],
        tolerance: float = 1.0
    ) -> Optional[Dict]:
        """
        给定目标流量，反向求解工作点

        物理原理：
        - 并联泵组在给定扬程H下产生总流量Q
        - 使用二分法找到使 Q_total ≈ Q_target 的 H

        Args:
            pump_ids: 运行泵ID列表
            Q_target: 目标流量 (m³/h)
            H_range: 扬程搜索范围 (m)
            tolerance: 流量容差 (m³/h)

        Returns:
            {'H': float, 'Q': float, 'eta': float} 或 None
        """
        # 如果提供了系统曲线函数，直接使用
        if self._system_curve_func is not None:
            H = self._system_curve_func(Q_target)
            result = self._synthesizer.synthesize_heterogeneous(
                pump_ids, H, self._pump_frequencies
            )
            return {
                'H': H,
                'Q': result.Q_total,
                'eta': result.eta_total
            }

        # 否则使用二分法在H_range内搜索
        H_low, H_high = H_range
        max_iterations = 50
        H_mid = (H_low + H_high) / 2

        for _ in range(max_iterations):
            H_mid = (H_low + H_high) / 2
            result = self._synthesizer.synthesize_heterogeneous(
                pump_ids, H_mid, self._pump_frequencies
            )
            Q_actual = result.Q_total

            if abs(Q_actual - Q_target) < tolerance:
                return {
                    'H': round(H_mid, 2),
                    'Q': round(Q_actual, 1),
                    'eta': round(result.eta_total, 4)
                }

            # 扬程越高，流量越低（并联泵组特性）
            if Q_actual > Q_target:
                H_low = H_mid  # 需要更高扬程来减少流量
            else:
                H_high = H_mid  # 需要更低扬程来增加流量

        # 二分法未收敛，返回最后一次结果
        result = self._synthesizer.synthesize_heterogeneous(
            pump_ids, H_mid, self._pump_frequencies
        )
        if result.Q_total >= Q_target * 0.9:  # 允许10%误差
            return {
                'H': round(H_mid, 2),
                'Q': round(result.Q_total, 1),
                'eta': round(result.eta_total, 4)
            }

        return None  # 无法达到目标流量

    def recommend_switch(
        self,
        Q_current: float,
        n_running: int,
        analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        根据分析结果推荐切换动作

        Args:
            Q_current: 当前流量 (m³/h)
            n_running: 当前运行台数
            analysis_result: analyze()的返回结果

        Returns:
            {
                'should_switch': bool,
                'target_n': int,
                'reason': str,
                'expected_eta_improvement': float
            }
        """
        switching_zones = analysis_result.get('switching_zones', [])

        for zone in switching_zones:
            if zone['from_N'] == n_running:
                if Q_current >= zone['Q_max']:
                    # 应该增加台数
                    return {
                        'should_switch': True,
                        'target_n': zone['to_N'],
                        'direction': 'increase',
                        'reason': f'流量{Q_current:.0f}超过切换区间上限{zone["Q_max"]:.0f}',
                        'expected_eta_improvement': 0.02  # 预估
                    }
            elif zone['to_N'] == n_running:
                if Q_current <= zone['Q_min']:
                    # 应该减少台数
                    return {
                        'should_switch': True,
                        'target_n': zone['from_N'],
                        'direction': 'decrease',
                        'reason': f'流量{Q_current:.0f}低于切换区间下限{zone["Q_min"]:.0f}',
                        'expected_eta_improvement': 0.01
                    }

        return {
            'should_switch': False,
            'target_n': n_running,
            'direction': 'none',
            'reason': '当前运行台数合适',
            'expected_eta_improvement': 0
        }
