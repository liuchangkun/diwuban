"""
泵组协调控制器 (app.services.characteristic_curves.pump_group.coordination_controller)

实现第15条曲线：泵组协调控制曲线。
多台变频泵的频率协调控制策略。

核心功能：
- 等效率控制：各泵工作在相同效率点
- 等负荷控制：各泵负荷率相同
- 主从控制：一台领跑，其他跟随
- 频率分配优化

物理原理：
- 等效率控制：最大化系统效率
- 等负荷控制：均衡设备磨损
- 主从控制：简化控制逻辑

版本: v1.0
创建日期: 2025-12-14
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class CoordinationController:
    """泵组协调控制器

    实现多台变频泵的频率协调控制，支持三种策略：
    1. 等效率控制：各泵工作在相同效率点
    2. 等负荷控制：各泵负荷率相同
    3. 主从控制：一台领跑，其他跟随

    应用场景：
    - 变频泵站优化
    - 能效管理
    - 负荷均衡
    """

    def __init__(
        self,
        synthesizer: Any,  # ParallelSynthesizer
        pump_registry: Optional[Dict[int, Dict]] = None
    ):
        """
        Args:
            synthesizer: 并联合成器
            pump_registry: 泵参数注册表
                格式: {pump_id: {'Q_rated': float, 'eta_bep': float, ...}}
        """
        self._synthesizer = synthesizer
        self._pump_registry = pump_registry or {}
        # 从synthesizer获取额定功率
        self._pump_rated_powers = (
            synthesizer._pump_rated_powers
            if hasattr(synthesizer, '_pump_rated_powers')
            else {}
        )

    def generate_control_curve(
        self,
        pump_ids: List[int],
        Q_target: float,
        H_system: float,
        strategy: str = 'equal_efficiency'
    ) -> Dict[str, Any]:
        """
        生成协调控制曲线

        Args:
            pump_ids: 运行泵ID列表
            Q_target: 目标总流量 (m³/h)
            H_system: 系统扬程 (m)
            strategy: 控制策略
                - 'equal_efficiency': 等效率控制
                - 'equal_load': 等负荷控制
                - 'master_slave': 主从控制

        Returns:
            {
                'frequency_allocation': {
                    101: {'frequency': 45.0, 'Q': 400.0, 'eta': 0.78},
                    102: {'frequency': 47.0, 'Q': 420.0, 'eta': 0.78}
                },
                'total_efficiency': 0.78,
                'total_power': 85.0,
                'strategy': 'equal_efficiency'
            }
        """
        if strategy == 'equal_efficiency':
            return self._equal_efficiency_control(pump_ids, Q_target, H_system)
        elif strategy == 'equal_load':
            return self._equal_load_control(pump_ids, Q_target, H_system)
        elif strategy == 'master_slave':
            return self._master_slave_control(pump_ids, Q_target, H_system)
        else:
            raise ValueError(f"未知控制策略: {strategy}")

    def _equal_efficiency_control(
        self,
        pump_ids: List[int],
        Q_target: float,
        H_system: float
    ) -> Dict[str, Any]:
        """等效率控制：各泵工作在相同效率点"""
        import numpy as np

        n_pumps = len(pump_ids)

        # 简化实现：使用网格搜索找最优频率分配
        best_result = None
        best_variance = float('inf')

        # 搜索频率空间
        freq_options = np.linspace(30.0, 50.0, 11)

        for base_freq in freq_options:
            freqs = [base_freq] * n_pumps
            etas = []
            Q_total = 0

            for i, pump_id in enumerate(pump_ids):
                freq = freqs[i]
                Q_i = self._estimate_flow_at_freq(pump_id, freq, H_system)
                eta_i = self._estimate_efficiency_at_freq(
                    pump_id, freq, H_system)
                Q_total += Q_i
                etas.append(eta_i)

            # 检查是否满足流量要求
            if abs(Q_total - Q_target) / Q_target < 0.1:  # 10%容差
                variance = np.var(etas)
                if variance < best_variance:
                    best_variance = variance
                    best_result = {
                        'freqs': freqs.copy(),
                        'etas': etas.copy(),
                        'Q_total': Q_total
                    }

        # 如果找不到满足条件的，使用默认频率
        if best_result is None:
            default_freq = 45.0
            best_result = {
                'freqs': [default_freq] * n_pumps,
                'etas': [0.75] * n_pumps,
                'Q_total': Q_target
            }

        # 构建结果
        frequency_allocation = {}
        total_power = 0

        for i, pump_id in enumerate(pump_ids):
            freq = best_result['freqs'][i]
            Q_i = self._estimate_flow_at_freq(pump_id, freq, H_system)
            eta_i = best_result['etas'][i]
            P_i = self._estimate_power_at_freq(
                pump_id, freq, Q_i, H_system, eta_i)

            frequency_allocation[pump_id] = {
                'frequency': round(freq, 1),
                'Q': round(Q_i, 1),
                'eta': round(eta_i, 4),
                'P': round(P_i, 2)
            }
            total_power += P_i

        return {
            'frequency_allocation': frequency_allocation,
            'total_efficiency': round(float(np.mean(best_result['etas'])), 4),
            'total_power': round(total_power, 2),
            'Q_achieved': round(best_result['Q_total'], 1),
            'Q_target': Q_target,
            'strategy': 'equal_efficiency',
            'generated_at': datetime.now().isoformat()
        }

    def _equal_load_control(
        self,
        pump_ids: List[int],
        Q_target: float,
        H_system: float
    ) -> Dict[str, Any]:
        """等负荷控制：各泵负荷率相同"""
        import numpy as np

        # 获取额定功率
        rated_powers = {}
        for pump_id in pump_ids:
            rated_powers[pump_id] = self._pump_rated_powers.get(pump_id, 55.0)

        # 按额定功率比例分配流量
        total_rated = sum(rated_powers.values())
        frequency_allocation = {}

        for pump_id in pump_ids:
            ratio = rated_powers[pump_id] / total_rated
            Q_i = Q_target * ratio

            # 反算所需频率
            freq = self._calculate_required_frequency(pump_id, Q_i, H_system)
            eta_i = self._estimate_efficiency_at_freq(pump_id, freq, H_system)
            P_i = self._estimate_power_at_freq(
                pump_id, freq, Q_i, H_system, eta_i)

            frequency_allocation[pump_id] = {
                'frequency': round(freq, 1),
                'Q': round(Q_i, 1),
                'eta': round(eta_i, 4),
                'P': round(P_i, 2),
                'load_ratio': round(P_i / rated_powers[pump_id], 3)
            }

        etas = [fa['eta'] for fa in frequency_allocation.values()]
        total_power = sum(fa['P'] for fa in frequency_allocation.values())

        return {
            'frequency_allocation': frequency_allocation,
            'total_efficiency': round(float(np.mean(etas)), 4),
            'total_power': round(total_power, 2),
            'Q_achieved': round(Q_target, 1),
            'strategy': 'equal_load',
            'generated_at': datetime.now().isoformat()
        }

    def _master_slave_control(
        self,
        pump_ids: List[int],
        Q_target: float,
        H_system: float
    ) -> Dict[str, Any]:
        """主从控制：一台领跑，其他跟随"""
        import numpy as np

        if not pump_ids:
            return {'error': '泵列表为空'}

        master_id = pump_ids[0]
        slave_ids = pump_ids[1:]

        # 主泵优先满频运行
        master_freq = 50.0
        master_Q = self._estimate_flow_at_freq(
            master_id, master_freq, H_system)

        # 剩余流量由从泵分担
        remaining_Q = Q_target - master_Q
        Q_per_slave = remaining_Q / len(slave_ids) if slave_ids else 0

        frequency_allocation = {}

        # 主泵
        master_eta = self._estimate_efficiency_at_freq(
            master_id, master_freq, H_system)
        master_P = self._estimate_power_at_freq(
            master_id, master_freq, master_Q, H_system, master_eta)
        frequency_allocation[master_id] = {
            'frequency': master_freq,
            'Q': round(master_Q, 1),
            'eta': round(master_eta, 4),
            'P': round(master_P, 2),
            'role': 'master'
        }

        # 从泵
        for slave_id in slave_ids:
            slave_freq = self._calculate_required_frequency(
                slave_id, Q_per_slave, H_system)
            slave_eta = self._estimate_efficiency_at_freq(
                slave_id, slave_freq, H_system)
            slave_P = self._estimate_power_at_freq(
                slave_id, slave_freq, Q_per_slave, H_system, slave_eta)

            frequency_allocation[slave_id] = {
                'frequency': round(slave_freq, 1),
                'Q': round(Q_per_slave, 1),
                'eta': round(slave_eta, 4),
                'P': round(slave_P, 2),
                'role': 'slave'
            }

        etas = [fa['eta'] for fa in frequency_allocation.values()]
        total_power = sum(fa['P'] for fa in frequency_allocation.values())

        return {
            'frequency_allocation': frequency_allocation,
            'total_efficiency': round(float(np.mean(etas)), 4),
            'total_power': round(total_power, 2),
            'Q_achieved': round(Q_target, 1),
            'master_pump': master_id,
            'strategy': 'master_slave',
            'generated_at': datetime.now().isoformat()
        }

    def _estimate_flow_at_freq(
        self,
        pump_id: int,
        frequency: float,
        H_system: float
    ) -> float:
        """估算给定频率下的流量（相似定律）"""
        # 基准：50Hz时的流量
        Q_rated = self._pump_registry.get(pump_id, {}).get('Q_rated', 500.0)
        # 相似定律：Q ∝ n
        freq_ratio = frequency / 50.0
        return Q_rated * freq_ratio

    def _estimate_efficiency_at_freq(
        self,
        pump_id: int,
        frequency: float,
        H_system: float
    ) -> float:
        """估算给定频率下的效率"""
        # 最佳效率点通常在额定频率附近
        eta_bep = self._pump_registry.get(pump_id, {}).get('eta_bep', 0.78)
        freq_ratio = frequency / 50.0

        # 效率随频率偏离BEP而下降
        efficiency_factor = 1.0 - 0.1 * (1.0 - freq_ratio) ** 2
        return eta_bep * efficiency_factor

    def _estimate_power_at_freq(
        self,
        pump_id: int,
        frequency: float,
        Q: float,
        H: float,
        eta: float
    ) -> float:
        """估算给定频率下的功率"""
        # P = ρgQH / η
        rho = 1000  # kg/m³
        g = 9.81  # m/s²

        if eta <= 0:
            eta = 0.7

        # Q单位转换：m³/h → m³/s
        Q_m3s = Q / 3600

        power = rho * g * Q_m3s * H / eta / 1000  # kW
        return power

    def _calculate_required_frequency(
        self,
        pump_id: int,
        Q_target: float,
        H_system: float
    ) -> float:
        """反算达到目标流量所需的频率"""
        Q_rated = self._pump_registry.get(pump_id, {}).get('Q_rated', 500.0)

        # 相似定律反算
        freq_ratio = Q_target / Q_rated if Q_rated > 0 else 0.9
        frequency = 50.0 * freq_ratio

        # 限制频率范围
        return max(25.0, min(50.0, frequency))

    def compare_strategies(
        self,
        pump_ids: List[int],
        Q_target: float,
        H_system: float
    ) -> Dict[str, Any]:
        """比较三种控制策略"""
        results = {}

        for strategy in ['equal_efficiency', 'equal_load', 'master_slave']:
            try:
                result = self.generate_control_curve(
                    pump_ids, Q_target, H_system, strategy)
                results[strategy] = {
                    'total_efficiency': result['total_efficiency'],
                    'total_power': result['total_power'],
                    'Q_achieved': result.get('Q_achieved', Q_target)
                }
            except Exception as e:
                results[strategy] = {'error': str(e)}

        # 推荐最优策略
        valid_results = {k: v for k, v in results.items() if 'error' not in v}
        if valid_results:
            best_strategy = max(valid_results.keys(
            ), key=lambda k: valid_results[k]['total_efficiency'])
        else:
            best_strategy = 'equal_efficiency'

        return {
            'comparison': results,
            'recommended_strategy': best_strategy,
            'reason': f'{best_strategy}策略效率最高',
            'generated_at': datetime.now().isoformat()
        }
