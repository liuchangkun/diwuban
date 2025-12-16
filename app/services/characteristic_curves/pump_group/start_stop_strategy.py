"""
泵组启停策略 (app.services.characteristic_curves.pump_group.start_stop_strategy)

实现第10条曲线：泵组启停策略曲线。
确定不同需求流量下应运行的泵台数和启停阈值。

核心功能：
- 生成N-Q曲线（台数-流量关系）
- 计算启停阈值
- 推荐启停动作
- 确定启动优先级

物理原理：
- 启动阈值：当前台数最大流量 × 启动裕度
- 停止阈值：减少一台后的最大流量 × 停止裕度
- 优先级：效率高的泵优先启动

版本: v1.0
创建日期: 2025-12-14
"""

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class StartStopStrategy:
    """泵组启停策略生成器

    根据泵组特性曲线生成启停控制策略，确定：
    1. 不同流量需求下应运行的泵台数
    2. 启动/停止阈值（含滞回区间）
    3. 泵的启动优先级序列

    应用场景：
    - 自动化泵站调度
    - 需求响应控制
    - 节能优化
    """

    def __init__(
        self,
        synthesizer: Any,  # ParallelSynthesizer
        start_margin: float = 0.95,
        stop_margin: float = 0.70,
        min_run_time: float = 300.0,
        pump_infos: Optional[Dict[int, Dict[str, Any]]] = None,
        pump_frequencies: Optional[Dict[int, float]] = None
    ):
        """
        Args:
            synthesizer: 并联合成器
            start_margin: 启动裕度（当流量达到当前最大的该比例时启动下一台）
            stop_margin: 停止裕度（当流量降到减一台后最大的该比例时停止）
            min_run_time: 最短运行时间（秒），防止频繁启停
            pump_infos: 泵信息字典
            pump_frequencies: 各泵运行频率
        """
        self._synthesizer = synthesizer
        self._start_margin = start_margin
        self._stop_margin = stop_margin
        self._min_run_time = min_run_time
        self._pump_infos = pump_infos or {}
        self._pump_frequencies = pump_frequencies

    def generate_strategy(
        self,
        pump_ids: List[int],
        H_system: float
    ) -> Dict[str, Any]:
        """
        生成启停策略

        Args:
            pump_ids: 可用泵ID列表
            H_system: 系统扬程 (m)

        Returns:
            {
                'thresholds': {
                    'start_2nd': 600.0,   # 启动第2台的流量阈值
                    'start_3rd': 1100.0,  # 启动第3台的流量阈值
                    'stop_3rd': 900.0,    # 停止第3台的流量阈值
                    'stop_2nd': 400.0     # 停止第2台的流量阈值
                },
                'priority_sequence': [101, 102, 103],  # 启动优先级
                'curve_data': [...]  # 详细曲线数据
            }
        """
        # 生成N-Q曲线
        n_q_result = self._synthesizer.generate_n_q_curve(
            pump_ids, H_system,
            pump_infos=self._pump_infos,
            pump_frequencies=self._pump_frequencies
        )

        # 提取N-Q数据
        n_q_data = n_q_result['data']
        n_q_map = {item['N']: item['Q_total'] for item in n_q_data}

        thresholds = {}
        curve_data = []
        max_pumps = len(pump_ids)

        for n in range(1, max_pumps):
            Q_n = n_q_map.get(n, 0)
            Q_n_plus_1 = n_q_map.get(n + 1, Q_n)

            # 启动阈值：当前台数最大流量 × 启动裕度
            start_threshold = Q_n * self._start_margin
            # 停止阈值：减少一台后的最大流量 × 停止裕度
            stop_threshold = n_q_map.get(
                n, Q_n) * self._stop_margin if n > 1 else 0

            thresholds[f'start_{self._ordinal(n + 1)}'] = round(
                start_threshold, 1)
            if n > 1:
                thresholds[f'stop_{self._ordinal(n)}'] = round(
                    stop_threshold, 1)

            curve_data.append({
                'N': n,
                'Q_max': round(Q_n, 1),
                'start_next_at': round(start_threshold, 1),
                'stop_current_at': round(stop_threshold, 1) if n > 1 else None
            })

        # 确定优先级序列
        priority_sequence = self._determine_priority_sequence(
            pump_ids, H_system, self._pump_frequencies
        )

        return {
            'thresholds': thresholds,
            'priority_sequence': priority_sequence,
            'curve_data': curve_data,
            'config': {
                'start_margin': self._start_margin,
                'stop_margin': self._stop_margin,
                'min_run_time': self._min_run_time
            },
            'H_system': H_system,
            'generated_at': datetime.now().isoformat()
        }

    def recommend_action(
        self,
        Q_demand: float,
        running_pumps: List[int],
        available_pumps: List[int],
        strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        根据策略推荐启停动作

        Args:
            Q_demand: 需求流量 (m³/h)
            running_pumps: 当前运行中的泵
            available_pumps: 可用泵列表
            strategy: 启停策略（由generate_strategy生成）

        Returns:
            {
                'action': 'start' | 'stop' | 'none',
                'pump_id': int | None,
                'reason': str,
                'expected_efficiency': float | None
            }
        """
        n_running = len(running_pumps)
        thresholds = strategy['thresholds']
        priority = strategy['priority_sequence']

        # 检查是否需要启动
        start_key = f'start_{self._ordinal(n_running + 1)}'
        if start_key in thresholds and Q_demand >= thresholds[start_key]:
            for pump_id in priority:
                if pump_id not in running_pumps and pump_id in available_pumps:
                    return {
                        'action': 'start',
                        'pump_id': pump_id,
                        'reason': f'Q_demand={Q_demand:.0f} >= 启动阈值{thresholds[start_key]:.0f}',
                        'expected_efficiency': None
                    }

        # 检查是否需要停止
        stop_key = f'stop_{self._ordinal(n_running)}'
        if stop_key in thresholds and Q_demand <= thresholds[stop_key]:
            for pump_id in reversed(priority):
                if pump_id in running_pumps:
                    return {
                        'action': 'stop',
                        'pump_id': pump_id,
                        'reason': f'Q_demand={Q_demand:.0f} <= 停止阈值{thresholds[stop_key]:.0f}',
                        'expected_efficiency': None
                    }

        return {
            'action': 'none',
            'pump_id': None,
            'reason': '当前台数合适',
            'expected_efficiency': None
        }

    def _determine_priority_sequence(
        self,
        pump_ids: List[int],
        H_system: float,
        pump_frequencies: Optional[Dict[int, float]] = None
    ) -> List[int]:
        """确定泵启动优先级（效率高的优先）"""
        efficiencies = {}

        for pump_id in pump_ids:
            try:
                result = self._synthesizer.synthesize_heterogeneous(
                    [pump_id], H_system, pump_frequencies
                )
                efficiencies[pump_id] = result.eta_total
            except Exception:
                efficiencies[pump_id] = 0.0

        # 按效率降序排列
        return sorted(pump_ids, key=lambda x: efficiencies.get(x, 0), reverse=True)

    def _ordinal(self, n: int) -> str:
        """生成序数词（第n台）"""
        ordinals = {1: '1st', 2: '2nd', 3: '3rd'}
        if n in ordinals:
            return ordinals[n]
        return f'{n}th'

    def calculate_optimal_n(
        self,
        Q_demand: float,
        pump_ids: List[int],
        H_system: float
    ) -> Dict[str, Any]:
        """
        计算给定流量需求下的最优运行台数

        Args:
            Q_demand: 需求流量 (m³/h)
            pump_ids: 可用泵列表
            H_system: 系统扬程 (m)

        Returns:
            {
                'optimal_n': int,
                'expected_eta': float,
                'expected_power': float,
                'alternatives': [...]
            }
        """
        alternatives = []
        max_pumps = len(pump_ids)

        for n in range(1, max_pumps + 1):
            selected = pump_ids[:n]
            try:
                result = self._synthesizer.synthesize_heterogeneous(
                    selected, H_system, self._pump_frequencies
                )
                if result.Q_total >= Q_demand * 0.95:  # 允许5%误差
                    alternatives.append({
                        'n': n,
                        'Q_total': result.Q_total,
                        'eta_total': result.eta_total,
                        'P_total': result.P_total,
                        'can_meet_demand': True
                    })
            except Exception:
                pass

        if not alternatives:
            return {
                'optimal_n': max_pumps,
                'expected_eta': 0,
                'expected_power': 0,
                'alternatives': [],
                'warning': '所有泵运行仍无法满足需求'
            }

        # 选择效率最高的方案
        best = max(alternatives, key=lambda x: x['eta_total'])

        return {
            'optimal_n': best['n'],
            'expected_eta': best['eta_total'],
            'expected_power': best['P_total'],
            'alternatives': alternatives
        }
