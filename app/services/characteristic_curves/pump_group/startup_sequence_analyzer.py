"""
启停顺序影响分析器 (app.services.characteristic_curves.pump_group.startup_sequence_analyzer)

分析不同启停顺序对泵组特性曲线的影响。

核心功能：
- 分析不同启动顺序对泵组曲线的影响
- 评估启停顺序对效率的影响
- 推荐最优启停顺序
- 量化顺序敏感性

物理背景：
- 并联泵组中，先启动的泵占据有利工况点
- 后启动的泵可能被迫在低效区运行
- 不同顺序导致流量分配不同，影响总效率

版本: v1.0
创建日期: 2025-12-14
"""

from dataclasses import dataclass, field
from datetime import datetime
from itertools import permutations
from typing import Any, Callable, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class SequenceAnalysisResult:
    """启停顺序分析结果"""
    sequence: List[int]  # 启动顺序

    # 效率指标
    total_efficiency: float = 0.0  # 最终总效率
    avg_efficiency_during_startup: float = 0.0  # 启动过程平均效率
    efficiency_variance: float = 0.0  # 各泵效率方差

    # 流量分配
    flow_distribution: Dict[int, float] = field(default_factory=dict)
    flow_imbalance: float = 0.0  # 流量不均衡度

    # 功率指标
    total_power: float = 0.0
    peak_power_during_startup: float = 0.0  # 启动过程峰值功率

    # 时间指标
    estimated_startup_time: float = 0.0  # 估计启动时间(s)

    # 评分
    score: float = 0.0  # 综合评分(0-100)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sequence": self.sequence,
            "total_efficiency": self.total_efficiency,
            "avg_efficiency_during_startup": self.avg_efficiency_during_startup,
            "efficiency_variance": self.efficiency_variance,
            "flow_distribution": self.flow_distribution,
            "flow_imbalance": self.flow_imbalance,
            "total_power": self.total_power,
            "peak_power_during_startup": self.peak_power_during_startup,
            "estimated_startup_time": self.estimated_startup_time,
            "score": self.score,
        }


@dataclass
class StartupSequenceReport:
    """启停顺序分析报告"""
    pump_ids: List[int]
    H_system: float

    # 所有分析的顺序
    analyzed_sequences: List[SequenceAnalysisResult] = field(
        default_factory=list)

    # 最优顺序
    optimal_sequence: List[int] = field(default_factory=list)
    optimal_score: float = 0.0

    # 最差顺序
    worst_sequence: List[int] = field(default_factory=list)
    worst_score: float = 0.0

    # 顺序敏感性
    sequence_sensitivity: float = 0.0  # 最优与最差的差异百分比

    # 建议
    recommendations: List[str] = field(default_factory=list)

    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pump_ids": self.pump_ids,
            "H_system": self.H_system,
            "analyzed_sequences": [s.to_dict() for s in self.analyzed_sequences],
            "optimal_sequence": self.optimal_sequence,
            "optimal_score": self.optimal_score,
            "worst_sequence": self.worst_sequence,
            "worst_score": self.worst_score,
            "sequence_sensitivity": self.sequence_sensitivity,
            "recommendations": self.recommendations,
            "generated_at": self.generated_at.isoformat(),
        }


class StartupSequenceAnalyzer:
    """启停顺序影响分析器

    职责：
    1. 分析不同启动顺序的效率影响
    2. 评估流量分配均衡性
    3. 计算启动过程能耗
    4. 推荐最优启停顺序

    物理模型：
    - 先启动的泵在空载系统中运行在大流量点
    - 后续泵启动后，系统阻力增加，先启动泵流量减小
    - 最终各泵分担的流量取决于各自特性曲线和启动顺序
    """

    def __init__(
        self,
        synthesizer=None,
        max_sequences: int = 24,  # 最多分析24种顺序（4!）
        startup_interval: float = 30.0  # 泵启动间隔(s)
    ):
        """初始化

        Args:
            synthesizer: ParallelSynthesizer实例
            max_sequences: 最大分析顺序数
            startup_interval: 相邻泵启动间隔时间
        """
        self._synthesizer = synthesizer
        self._max_sequences = max_sequences
        self._startup_interval = startup_interval
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}")

    def analyze(
        self,
        pump_ids: List[int],
        H_system: float,
        pump_infos: Optional[Dict[int, Dict]] = None,
        pump_frequencies: Optional[Dict[int, float]] = None
    ) -> StartupSequenceReport:
        """分析所有可能的启动顺序

        Args:
            pump_ids: 泵ID列表
            H_system: 系统扬程
            pump_infos: 泵信息
            pump_frequencies: 泵频率

        Returns:
            StartupSequenceReport: 分析报告
        """
        report = StartupSequenceReport(
            pump_ids=pump_ids,
            H_system=H_system,
        )

        # 生成所有排列
        all_sequences = list(permutations(pump_ids))

        # 限制分析数量
        if len(all_sequences) > self._max_sequences:
            # 采样：保留第一个、最后一个，和随机中间的
            import random
            sequences_to_analyze = [
                all_sequences[0],
                all_sequences[-1],
            ]
            remaining = random.sample(
                all_sequences[1:-1],
                min(self._max_sequences - 2, len(all_sequences) - 2)
            )
            sequences_to_analyze.extend(remaining)
        else:
            sequences_to_analyze = all_sequences

        # 分析每种顺序
        for seq in sequences_to_analyze:
            result = self._analyze_sequence(
                list(seq), H_system, pump_infos, pump_frequencies
            )
            report.analyzed_sequences.append(result)

        # 找出最优和最差
        if report.analyzed_sequences:
            sorted_results = sorted(
                report.analyzed_sequences,
                key=lambda r: r.score,
                reverse=True
            )

            best = sorted_results[0]
            worst = sorted_results[-1]

            report.optimal_sequence = best.sequence
            report.optimal_score = best.score
            report.worst_sequence = worst.sequence
            report.worst_score = worst.score

            # 计算敏感性
            if worst.score > 0:
                report.sequence_sensitivity = (
                    (best.score - worst.score) / worst.score * 100
                )

        # 生成建议
        self._generate_recommendations(report)

        self._logger.info(
            f"[顺序分析] 分析{len(report.analyzed_sequences)}种顺序, "
            f"最优={report.optimal_sequence}, 敏感性={report.sequence_sensitivity:.1f}%"
        )

        return report

    # 别名方法，保持接口兼容
    def analyze_impact(
        self,
        pump_ids: List[int],
        H_system: float,
        pump_infos: Optional[Dict[int, Dict]] = None,
        pump_frequencies: Optional[Dict[int, float]] = None
    ) -> StartupSequenceReport:
        """analyze 的别名方法"""
        return self.analyze(pump_ids, H_system, pump_infos, pump_frequencies)

    def _analyze_sequence(
        self,
        sequence: List[int],
        H_system: float,
        pump_infos: Optional[Dict[int, Dict]],
        pump_frequencies: Optional[Dict[int, float]]
    ) -> SequenceAnalysisResult:
        """分析单个启动顺序"""
        result = SequenceAnalysisResult(sequence=sequence)

        efficiencies_during_startup = []
        peak_power = 0.0

        # 模拟逐台启动过程
        running_pumps = []
        for pump_id in sequence:
            running_pumps.append(pump_id)

            # 计算当前状态
            try:
                if self._synthesizer is not None:
                    synth_result = self._synthesizer.synthesize_heterogeneous(
                        pump_ids=running_pumps,
                        H_system=H_system,
                        pump_frequencies=pump_frequencies
                    )

                    efficiencies_during_startup.append(synth_result.eta_total)
                    peak_power = max(peak_power, synth_result.P_total)

                    # 最后一台启动后的状态
                    if len(running_pumps) == len(sequence):
                        result.total_efficiency = synth_result.eta_total
                        result.total_power = synth_result.P_total
                        result.flow_distribution = dict(
                            synth_result.pump_flows)

            except Exception as e:
                self._logger.warning(f"[顺序分析] 合成失败: {e}")

        # 计算统计指标
        if efficiencies_during_startup:
            result.avg_efficiency_during_startup = (
                sum(efficiencies_during_startup) /
                len(efficiencies_during_startup)
            )

        result.peak_power_during_startup = peak_power
        result.estimated_startup_time = len(sequence) * self._startup_interval

        # 计算流量不均衡度
        if result.flow_distribution:
            flows = list(result.flow_distribution.values())
            avg_flow = sum(flows) / len(flows) if flows else 0
            if avg_flow > 0:
                variance = sum((f - avg_flow) ** 2 for f in flows) / len(flows)
                result.flow_imbalance = (variance ** 0.5) / avg_flow

        # 计算效率方差
        if result.flow_distribution and self._synthesizer:
            eta_values = []
            for pump_id in sequence:
                # 估算各泵效率（简化）
                Q_i = result.flow_distribution.get(pump_id, 0)
                if Q_i > 0:
                    eta_values.append(result.total_efficiency)

            if eta_values:
                avg_eta = sum(eta_values) / len(eta_values)
                result.efficiency_variance = sum(
                    (e - avg_eta) ** 2 for e in eta_values
                ) / len(eta_values)

        # 综合评分
        result.score = self._calculate_score(result)

        return result

    def _calculate_score(self, result: SequenceAnalysisResult) -> float:
        """计算综合评分"""
        score = 0.0

        # 效率权重 50%
        score += result.total_efficiency * 50

        # 启动过程平均效率权重 20%
        score += result.avg_efficiency_during_startup * 20

        # 流量均衡性权重 15%（不均衡度越小越好）
        if result.flow_imbalance < 0.1:
            score += 15
        elif result.flow_imbalance < 0.2:
            score += 10
        elif result.flow_imbalance < 0.3:
            score += 5

        # 效率方差权重 15%（方差越小越好）
        if result.efficiency_variance < 0.01:
            score += 15
        elif result.efficiency_variance < 0.05:
            score += 10
        elif result.efficiency_variance < 0.1:
            score += 5

        return score

    def _generate_recommendations(self, report: StartupSequenceReport) -> None:
        """生成建议"""
        if report.sequence_sensitivity > 10:
            report.recommendations.append(
                f"启动顺序对效率影响显著（敏感性{report.sequence_sensitivity:.1f}%），"
                "建议严格遵循最优顺序"
            )
        elif report.sequence_sensitivity > 5:
            report.recommendations.append(
                "启动顺序对效率有一定影响，建议优先采用推荐顺序"
            )
        else:
            report.recommendations.append(
                "启动顺序对效率影响较小，可灵活选择"
            )

        if report.optimal_sequence:
            report.recommendations.append(
                f"推荐启动顺序: {' → '.join(map(str, report.optimal_sequence))}"
            )

        if report.worst_sequence:
            report.recommendations.append(
                f"避免启动顺序: {' → '.join(map(str, report.worst_sequence))}"
            )

    def compare_two_sequences(
        self,
        sequence_a: List[int],
        sequence_b: List[int],
        H_system: float,
        pump_infos: Optional[Dict[int, Dict]] = None,
        pump_frequencies: Optional[Dict[int, float]] = None
    ) -> Dict[str, Any]:
        """对比两种启动顺序

        Args:
            sequence_a: 顺序A
            sequence_b: 顺序B
            H_system: 系统扬程
            pump_infos: 泵信息
            pump_frequencies: 泵频率

        Returns:
            Dict: 对比结果
        """
        result_a = self._analyze_sequence(
            sequence_a, H_system, pump_infos, pump_frequencies
        )
        result_b = self._analyze_sequence(
            sequence_b, H_system, pump_infos, pump_frequencies
        )

        comparison = {
            "sequence_a": {
                "sequence": sequence_a,
                "efficiency": result_a.total_efficiency,
                "score": result_a.score,
            },
            "sequence_b": {
                "sequence": sequence_b,
                "efficiency": result_b.total_efficiency,
                "score": result_b.score,
            },
            "efficiency_diff": result_a.total_efficiency - result_b.total_efficiency,
            "score_diff": result_a.score - result_b.score,
            "recommended": "A" if result_a.score > result_b.score else "B",
        }

        return comparison
