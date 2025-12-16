"""
泵组切换过程模拟器 (app.services.characteristic_curves.pump_group.switching_process_simulator)

实现第12条曲线：泵组切换过程曲线。
描述切换过程中的流量、压力变化轨迹。

核心功能：
- 模拟启/停泵过程
- 预测压力波动
- 计算稳定时间
- 评估水锤风险

物理原理：
- 停泵：流量逐渐下降，压力先升后降
- 启泵：流量逐渐上升，压力先降后升
- 过渡时间取决于管网惯性和泵启动特性

版本: v1.0
创建日期: 2025-12-14
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import logging
import math

logger = logging.getLogger(__name__)


class SwitchingProcessSimulator:
    """泵组切换过程模拟器

    模拟泵组启停过程中的动态变化，用于：
    1. 预测水锤风险
    2. 优化切换速度
    3. 保护管网设备

    物理模型：
    - S形过渡函数：平滑模拟流量变化
    - 高斯压力波动：模拟压力冲击
    """

    def __init__(
        self,
        synthesizer: Any,  # ParallelSynthesizer
        transition_time: float = 30.0,
        time_step: float = 1.0
    ):
        """
        Args:
            synthesizer: 并联合成器
            transition_time: 过渡时间 (秒)
            time_step: 时间步长 (秒)
        """
        self._synthesizer = synthesizer
        self._transition_time = transition_time
        self._time_step = time_step

    def simulate(
        self,
        pump_ids_before: List[int],
        pump_ids_after: List[int],
        H_system: float,
        action: str = 'stop',
        pump_frequencies: Optional[Dict[int, float]] = None
    ) -> Dict[str, Any]:
        """
        模拟切换过程

        Args:
            pump_ids_before: 切换前运行的泵
            pump_ids_after: 切换后运行的泵
            H_system: 系统扬程 (m)
            action: 'start'启动 或 'stop'停止
            pump_frequencies: 运行频率字典

        Returns:
            {
                'trajectory': [
                    {'t': 0, 'Q': 1200, 'H': 35.0, 'P': 120, 'status': 'before'},
                    {'t': 5, 'Q': 1150, 'H': 35.5, 'status': 'transitioning'},
                    ...
                ],
                'max_pressure_surge': 2.5,  # 最大压力波动(m)
                'min_flow_dip': 50.0,  # 最小流量下降(m³/h)
                'stabilization_time': 25.0  # 稳定时间(秒)
            }
        """
        import numpy as np

        # 计算切换前后的稳态点
        result_before = self._synthesizer.synthesize_heterogeneous(
            pump_ids_before, H_system, pump_frequencies
        )
        result_after = self._synthesizer.synthesize_heterogeneous(
            pump_ids_after, H_system, pump_frequencies
        )

        Q_before = result_before.Q_total
        Q_after = result_after.Q_total
        P_before = result_before.P_total
        P_after = result_after.P_total

        # 生成过渡轨迹（使用S形曲线）
        trajectory = []
        t_values = np.arange(0, self._transition_time +
                             self._time_step, self._time_step)

        for t in t_values:
            # S形过渡函数
            progress = self._sigmoid_transition(t / self._transition_time)

            Q_t = Q_before + (Q_after - Q_before) * progress
            P_t = P_before + (P_after - P_before) * progress

            # 压力波动模拟（在过渡中间有峰值）
            H_surge = H_system + \
                self._pressure_surge_model(t, self._transition_time, action)

            status = 'before' if t == 0 else (
                'after' if t >= self._transition_time else 'transitioning')

            trajectory.append({
                't': float(t),
                'Q': round(float(Q_t), 1),
                'H': round(float(H_surge), 2),
                'P': round(float(P_t), 2),
                'status': status
            })

        # 计算特征值
        H_values = [p['H'] for p in trajectory]
        Q_values = [p['Q'] for p in trajectory]

        return {
            'trajectory': trajectory,
            'max_pressure_surge': round(max(H_values) - H_system, 2),
            'min_pressure_dip': round(H_system - min(H_values), 2),
            'min_flow_dip': round(Q_before - min(Q_values), 1) if action == 'stop' else 0,
            'max_flow_rise': round(max(Q_values) - Q_before, 1) if action == 'start' else 0,
            'stabilization_time': self._transition_time,
            'action': action,
            'pump_changed': list(set(pump_ids_before) ^ set(pump_ids_after)),
            'before_state': {
                'pumps': pump_ids_before,
                'Q': round(Q_before, 1),
                'P': round(P_before, 2)
            },
            'after_state': {
                'pumps': pump_ids_after,
                'Q': round(Q_after, 1),
                'P': round(P_after, 2)
            },
            'generated_at': datetime.now().isoformat()
        }

    def _sigmoid_transition(self, x: float) -> float:
        """S形过渡函数

        使用Sigmoid函数实现平滑过渡，避免阶跃变化
        """
        return 1 / (1 + math.exp(-10 * (x - 0.5)))

    def _pressure_surge_model(
        self,
        t: float,
        T: float,
        action: str
    ) -> float:
        """压力波动模型

        使用高斯函数模拟压力冲击

        Args:
            t: 当前时间
            T: 总过渡时间
            action: 'start' 或 'stop'

        Returns:
            压力偏移量 (m)
        """
        # 峰值出现在过渡时间的30%处
        peak_time = T * 0.3

        if action == 'stop':
            # 停泵时压力先升后降（水锤效应）
            magnitude = 2.0
            return magnitude * math.exp(-((t - peak_time) / 5) ** 2)
        else:
            # 启泵时压力先降后升（负压效应）
            magnitude = -1.5
            return magnitude * math.exp(-((t - peak_time) / 5) ** 2)

    def simulate_sequence(
        self,
        pump_sequence: List[Dict[str, Any]],
        H_system: float,
        pump_frequencies: Optional[Dict[int, float]] = None,
        interval: float = 5.0
    ) -> Dict[str, Any]:
        """
        模拟连续多次切换

        Args:
            pump_sequence: 切换序列
                [{'pumps': [1,2], 'action': 'start', 'delay': 0}, ...]
            H_system: 系统扬程
            pump_frequencies: 运行频率
            interval: 切换间隔 (秒)

        Returns:
            综合轨迹和分析结果
        """
        all_trajectories = []
        current_pumps = pump_sequence[0]['pumps'] if pump_sequence else []
        total_time = 0

        for i, step in enumerate(pump_sequence[1:], 1):
            next_pumps = step['pumps']
            action = 'start' if len(next_pumps) > len(
                current_pumps) else 'stop'

            sim_result = self.simulate(
                current_pumps, next_pumps, H_system, action, pump_frequencies
            )

            # 调整时间戳
            for point in sim_result['trajectory']:
                point['t'] += total_time
                all_trajectories.append(point)

            total_time += self._transition_time + interval
            current_pumps = next_pumps

        # 计算综合指标
        if all_trajectories:
            H_values = [p['H'] for p in all_trajectories]
            Q_values = [p['Q'] for p in all_trajectories]

            return {
                'trajectory': all_trajectories,
                'total_time': total_time,
                'max_H': max(H_values),
                'min_H': min(H_values),
                'max_Q': max(Q_values),
                'min_Q': min(Q_values),
                'n_switches': len(pump_sequence) - 1,
                'generated_at': datetime.now().isoformat()
            }

        return {'trajectory': [], 'total_time': 0}

    def assess_water_hammer_risk(
        self,
        simulation_result: Dict[str, Any],
        max_surge_threshold: float = 3.0
    ) -> Dict[str, Any]:
        """
        评估水锤风险

        Args:
            simulation_result: simulate()的返回结果
            max_surge_threshold: 最大允许压力波动 (m)

        Returns:
            风险评估结果
        """
        max_surge = simulation_result.get('max_pressure_surge', 0)
        min_dip = simulation_result.get('min_pressure_dip', 0)

        risk_level = 'low'
        recommendations = []

        if max_surge > max_surge_threshold:
            risk_level = 'high'
            recommendations.append(
                f'压力波动{max_surge:.1f}m超过阈值{max_surge_threshold}m')
            recommendations.append('建议：减慢阀门关闭速度')
            recommendations.append('建议：检查管道支撑')
        elif max_surge > max_surge_threshold * 0.7:
            risk_level = 'medium'
            recommendations.append('压力波动接近临界值，需关注')

        if min_dip > 2.0:
            if risk_level == 'low':
                risk_level = 'medium'
            recommendations.append(f'负压深度{min_dip:.1f}m，注意气蚀风险')

        if not recommendations:
            recommendations.append('切换过程平稳，无明显风险')

        return {
            'risk_level': risk_level,
            'max_surge': max_surge,
            'min_dip': min_dip,
            'recommendations': recommendations,
            'threshold_used': max_surge_threshold
        }

    def optimize_transition_time(
        self,
        pump_ids_before: List[int],
        pump_ids_after: List[int],
        H_system: float,
        target_max_surge: float = 2.0,
        pump_frequencies: Optional[Dict[int, float]] = None
    ) -> Dict[str, Any]:
        """
        优化过渡时间

        通过迭代找到满足压力波动约束的最短过渡时间

        Args:
            pump_ids_before: 切换前泵
            pump_ids_after: 切换后泵
            H_system: 系统扬程
            target_max_surge: 目标最大压力波动
            pump_frequencies: 运行频率

        Returns:
            优化结果
        """
        action = 'start' if len(pump_ids_after) > len(
            pump_ids_before) else 'stop'
        original_time = self._transition_time

        # 二分搜索最优时间
        t_min, t_max = 10.0, 120.0
        best_time = t_max

        for _ in range(10):
            t_mid = (t_min + t_max) / 2
            self._transition_time = t_mid

            result = self.simulate(
                pump_ids_before, pump_ids_after, H_system, action, pump_frequencies
            )
            surge = result['max_pressure_surge']

            if surge <= target_max_surge:
                best_time = t_mid
                t_max = t_mid
            else:
                t_min = t_mid

        # 恢复原始设置
        self._transition_time = original_time

        return {
            'optimal_transition_time': round(best_time, 1),
            'expected_max_surge': round(surge, 2),
            'target_max_surge': target_max_surge,
            'original_transition_time': original_time
        }
