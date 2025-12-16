"""
并联泵组流量平衡分析器 (app.services.characteristic_curves.pump_group.flow_balance_analyzer)

检测并联泵组运行中的抢流现象和流量分配不均问题。

核心功能：
- 抢流现象检测（大泵抢小泵流量）
- 流量分配不均分析
- 并联干涉系数计算
- 运行稳定性评估
- 优化建议生成

物理原理：
- 并联泵组共用同一出口压力
- 当泵曲线差异较大时，扬程高的泵会"抢"扬程低的泵的流量
- 严重时可能导致小泵零流量甚至逆流

抢流判据：
- 流量比偏离额定比例超过阈值
- 实际流量与理论流量偏差大
- 存在零流量或负流量泵

版本: v1.0
创建日期: 2025-12-14
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
import logging
import math

logger = logging.getLogger(__name__)


class FlowImbalanceLevel(Enum):
    """流量不平衡等级"""
    NORMAL = "normal"           # 正常（偏差<10%）
    SLIGHT = "slight"           # 轻微（10-20%）
    MODERATE = "moderate"       # 中等（20-30%）
    SEVERE = "severe"           # 严重（30-50%）
    CRITICAL = "critical"       # 危急（>50%或存在零/逆流）


@dataclass
class PumpFlowStatus:
    """单泵流量状态"""
    pump_id: int
    actual_flow: float          # 实际流量 (m³/h)
    expected_flow: float        # 理论流量 (m³/h)
    flow_ratio: float           # 流量比例 (actual/expected)
    deviation: float            # 偏差百分比 (%)
    is_starved: bool = False    # 是否被抢流（流量不足）
    is_dominant: bool = False   # 是否抢流方（流量过多）
    is_zero_flow: bool = False  # 是否零流量
    is_reverse: bool = False    # 是否逆流


@dataclass
class FlowBalanceResult:
    """流量平衡分析结果"""
    # 分析标识
    station_id: int
    pump_combination: List[int]
    analyzed_at: datetime = field(default_factory=datetime.now)

    # 总体状态
    imbalance_level: FlowImbalanceLevel = FlowImbalanceLevel.NORMAL
    overall_score: float = 100.0  # 平衡评分 (0-100)

    # 流量统计
    total_flow: float = 0.0
    pump_statuses: List[PumpFlowStatus] = field(default_factory=list)

    # 抢流分析
    has_flow_snatching: bool = False   # 是否存在抢流现象
    snatching_pairs: List[Tuple[int, int]] = field(
        default_factory=list)  # 抢流泵对 (抢流方, 被抢方)
    max_deviation: float = 0.0         # 最大偏差 (%)

    # 干涉系数
    interference_coefficient: float = 1.0  # 并联干涉系数 (理想=1, 有干涉>1)

    # 运行稳定性
    stability_score: float = 100.0
    stability_issues: List[str] = field(default_factory=list)

    # 建议
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'station_id': self.station_id,
            'pump_combination': self.pump_combination,
            'analyzed_at': self.analyzed_at.isoformat(),
            'imbalance_level': self.imbalance_level.value,
            'overall_score': self.overall_score,
            'total_flow': self.total_flow,
            'pump_statuses': [
                {
                    'pump_id': s.pump_id,
                    'actual_flow': s.actual_flow,
                    'expected_flow': s.expected_flow,
                    'flow_ratio': s.flow_ratio,
                    'deviation': s.deviation,
                    'is_starved': s.is_starved,
                    'is_dominant': s.is_dominant,
                    'is_zero_flow': s.is_zero_flow,
                    'is_reverse': s.is_reverse,
                }
                for s in self.pump_statuses
            ],
            'has_flow_snatching': self.has_flow_snatching,
            'snatching_pairs': self.snatching_pairs,
            'max_deviation': self.max_deviation,
            'interference_coefficient': self.interference_coefficient,
            'stability_score': self.stability_score,
            'stability_issues': self.stability_issues,
            'recommendations': self.recommendations,
        }


class FlowBalanceAnalyzer:
    """并联泵组流量平衡分析器

    检测并联泵组运行中的抢流现象，分析流量分配是否均衡。

    抢流现象成因：
    1. 泵曲线差异：扬程高的泵抢扬程低的泵流量
    2. 管路阻力差异：近端泵比远端泵流量大
    3. 变频差异：高频泵抢低频泵流量
    4. 性能退化：老旧泵被新泵抢流
    """

    def __init__(
        self,
        deviation_threshold_slight: float = 10.0,    # 轻微不平衡阈值 (%)
        deviation_threshold_moderate: float = 20.0,  # 中等不平衡阈值 (%)
        deviation_threshold_severe: float = 30.0,    # 严重不平衡阈值 (%)
        deviation_threshold_critical: float = 50.0,  # 危急不平衡阈值 (%)
        zero_flow_threshold: float = 5.0,            # 零流量判定阈值 (m³/h)
        reverse_flow_threshold: float = -1.0,        # 逆流判定阈值 (m³/h)
        pump_curve_provider: Optional[Callable[[int], Dict[str, Any]]] = None,
    ):
        """初始化

        Args:
            deviation_threshold_*: 各级不平衡阈值
            zero_flow_threshold: 零流量判定阈值
            reverse_flow_threshold: 逆流判定阈值
            pump_curve_provider: 单泵曲线数据提供器
        """
        self.deviation_slight = deviation_threshold_slight
        self.deviation_moderate = deviation_threshold_moderate
        self.deviation_severe = deviation_threshold_severe
        self.deviation_critical = deviation_threshold_critical
        self.zero_flow_threshold = zero_flow_threshold
        self.reverse_flow_threshold = reverse_flow_threshold
        self.pump_curve_provider = pump_curve_provider

    def analyze(
        self,
        station_id: int,
        pump_flows: Dict[int, float],
        pump_rated_flows: Optional[Dict[int, float]] = None,
        system_head: Optional[float] = None,
        pump_frequencies: Optional[Dict[int, float]] = None,
    ) -> FlowBalanceResult:
        """分析流量平衡

        Args:
            station_id: 泵站ID
            pump_flows: 各泵实际流量 {pump_id: flow}
            pump_rated_flows: 各泵额定流量 {pump_id: rated_flow}
            system_head: 系统扬程 (m)，用于计算理论流量
            pump_frequencies: 各泵运行频率 {pump_id: freq_Hz}

        Returns:
            FlowBalanceResult: 分析结果
        """
        pump_ids = list(pump_flows.keys())
        n_pumps = len(pump_ids)

        result = FlowBalanceResult(
            station_id=station_id,
            pump_combination=pump_ids,
            total_flow=sum(pump_flows.values()),
        )

        if n_pumps < 2:
            logger.info(f"单泵运行，无需流量平衡分析")
            return result

        # 计算各泵期望流量
        expected_flows = self._calculate_expected_flows(
            pump_ids=pump_ids,
            pump_rated_flows=pump_rated_flows,
            pump_frequencies=pump_frequencies,
            system_head=system_head,
        )

        # 分析各泵流量状态
        pump_statuses = []
        max_deviation = 0.0

        for pump_id in pump_ids:
            actual = pump_flows.get(pump_id, 0.0)
            expected = expected_flows.get(pump_id, actual)

            if expected > 0:
                ratio = actual / expected
                deviation = abs(ratio - 1.0) * 100
            else:
                ratio = float('inf') if actual > 0 else 0
                deviation = 100.0

            status = PumpFlowStatus(
                pump_id=pump_id,
                actual_flow=actual,
                expected_flow=expected,
                flow_ratio=ratio,
                deviation=deviation,
                is_zero_flow=actual <= self.zero_flow_threshold,
                is_reverse=actual < self.reverse_flow_threshold,
            )

            # 判断抢流/被抢
            if ratio > 1.2:  # 流量超出20%以上
                status.is_dominant = True
            elif ratio < 0.8:  # 流量不足20%以上
                status.is_starved = True

            pump_statuses.append(status)
            max_deviation = max(max_deviation, deviation)

        result.pump_statuses = pump_statuses
        result.max_deviation = max_deviation

        # 识别抢流泵对
        result.snatching_pairs = self._identify_snatching_pairs(pump_statuses)
        result.has_flow_snatching = len(result.snatching_pairs) > 0

        # 计算不平衡等级
        result.imbalance_level = self._determine_imbalance_level(
            pump_statuses, max_deviation)

        # 计算干涉系数
        result.interference_coefficient = self._calculate_interference_coefficient(
            pump_statuses, expected_flows
        )

        # 评估运行稳定性
        result.stability_score, result.stability_issues = self._assess_stability(
            pump_statuses)

        # 计算总体评分
        result.overall_score = self._calculate_overall_score(result)

        # 生成建议
        result.recommendations = self._generate_recommendations(
            result, pump_frequencies)

        return result

    def _calculate_expected_flows(
        self,
        pump_ids: List[int],
        pump_rated_flows: Optional[Dict[int, float]],
        pump_frequencies: Optional[Dict[int, float]],
        system_head: Optional[float],
    ) -> Dict[int, float]:
        """计算各泵期望流量

        Args:
            pump_ids: 泵ID列表
            pump_rated_flows: 额定流量
            pump_frequencies: 运行频率
            system_head: 系统扬程

        Returns:
            Dict[int, float]: 各泵期望流量
        """
        expected = {}

        if pump_rated_flows is None:
            # 无额定流量数据，假设等分
            avg_flow = 100.0  # 默认值
            for pump_id in pump_ids:
                expected[pump_id] = avg_flow
            return expected

        for pump_id in pump_ids:
            rated = pump_rated_flows.get(pump_id, 100.0)

            # 根据频率调整（相似定律）
            if pump_frequencies:
                freq = pump_frequencies.get(pump_id, 50.0)
                freq_ratio = freq / 50.0
                rated = rated * freq_ratio

            expected[pump_id] = rated

        # 如果有系统扬程和泵曲线，可以更精确计算
        if system_head and self.pump_curve_provider:
            for pump_id in pump_ids:
                curve = self.pump_curve_provider(pump_id)
                if curve:
                    # 从曲线反查流量
                    flow = self._get_flow_from_curve(curve, system_head)
                    if flow is not None:
                        expected[pump_id] = flow

        return expected

    def _get_flow_from_curve(
        self,
        curve: Dict[str, Any],
        head: float,
    ) -> Optional[float]:
        """从曲线反查流量

        Args:
            curve: 泵曲线数据
            head: 目标扬程

        Returns:
            Optional[float]: 对应流量，无法计算返回None
        """
        coeffs = curve.get('coefficients')
        if not coeffs:
            return None

        # 假设二次曲线 H = a*Q² + b*Q + c
        # 解方程 a*Q² + b*Q + (c - H) = 0
        a = coeffs.get('a', 0)
        b = coeffs.get('b', 0)
        c = coeffs.get('c', 0)

        if abs(a) < 1e-10:
            # 线性曲线
            if abs(b) < 1e-10:
                return None
            return (head - c) / b

        # 二次曲线
        discriminant = b ** 2 - 4 * a * (c - head)
        if discriminant < 0:
            return None

        sqrt_d = math.sqrt(discriminant)
        q1 = (-b + sqrt_d) / (2 * a)
        q2 = (-b - sqrt_d) / (2 * a)

        # 取正值
        if q1 > 0:
            return q1
        elif q2 > 0:
            return q2
        return None

    def _identify_snatching_pairs(
        self,
        statuses: List[PumpFlowStatus],
    ) -> List[Tuple[int, int]]:
        """识别抢流泵对

        Args:
            statuses: 各泵流量状态

        Returns:
            List[Tuple[int, int]]: 抢流泵对列表 (抢流方, 被抢方)
        """
        pairs = []

        dominants = [s for s in statuses if s.is_dominant]
        starved = [s for s in statuses if s.is_starved]

        for d in dominants:
            for s in starved:
                # 抢流方流量多出的部分 ≈ 被抢方流量缺失的部分
                excess = d.actual_flow - d.expected_flow
                deficit = s.expected_flow - s.actual_flow

                if excess > 0 and deficit > 0:
                    # 检查是否存在抢流关系
                    if abs(excess - deficit) < max(excess, deficit) * 0.5:
                        pairs.append((d.pump_id, s.pump_id))

        return pairs

    def _determine_imbalance_level(
        self,
        statuses: List[PumpFlowStatus],
        max_deviation: float,
    ) -> FlowImbalanceLevel:
        """判定不平衡等级

        Args:
            statuses: 各泵流量状态
            max_deviation: 最大偏差

        Returns:
            FlowImbalanceLevel: 不平衡等级
        """
        # 如果存在零流量或逆流，直接判定为危急
        for s in statuses:
            if s.is_reverse or s.is_zero_flow:
                return FlowImbalanceLevel.CRITICAL

        # 根据最大偏差判定
        if max_deviation >= self.deviation_critical:
            return FlowImbalanceLevel.CRITICAL
        elif max_deviation >= self.deviation_severe:
            return FlowImbalanceLevel.SEVERE
        elif max_deviation >= self.deviation_moderate:
            return FlowImbalanceLevel.MODERATE
        elif max_deviation >= self.deviation_slight:
            return FlowImbalanceLevel.SLIGHT
        else:
            return FlowImbalanceLevel.NORMAL

    def _calculate_interference_coefficient(
        self,
        statuses: List[PumpFlowStatus],
        expected_flows: Dict[int, float],
    ) -> float:
        """计算并联干涉系数

        干涉系数 = 理论总流量 / 实际总流量
        - 理想无干涉时 = 1.0
        - 有干涉（抢流）时 > 1.0
        - 正向协同时 < 1.0（罕见）

        Args:
            statuses: 各泵流量状态
            expected_flows: 期望流量

        Returns:
            float: 干涉系数
        """
        actual_total = sum(s.actual_flow for s in statuses)
        expected_total = sum(expected_flows.values())

        if actual_total > 0:
            return expected_total / actual_total
        return 1.0

    def _assess_stability(
        self,
        statuses: List[PumpFlowStatus],
    ) -> Tuple[float, List[str]]:
        """评估运行稳定性

        Args:
            statuses: 各泵流量状态

        Returns:
            Tuple[float, List[str]]: (稳定性评分, 问题列表)
        """
        score = 100.0
        issues = []

        for s in statuses:
            if s.is_reverse:
                score -= 40
                issues.append(f"泵{s.pump_id}存在逆流，运行极不稳定")
            elif s.is_zero_flow:
                score -= 30
                issues.append(f"泵{s.pump_id}零流量，可能空转")
            elif s.is_starved:
                score -= 15
                issues.append(f"泵{s.pump_id}流量不足，被抢流")
            elif s.is_dominant:
                score -= 10
                issues.append(f"泵{s.pump_id}流量过大，正在抢流")

        # 流量分布不均会导致不稳定
        deviations = [s.deviation for s in statuses]
        avg_deviation = sum(deviations) / len(deviations) if deviations else 0
        if avg_deviation > 20:
            score -= 10
            issues.append(f"流量分配不均匀，平均偏差{avg_deviation:.1f}%")

        return max(0, score), issues

    def _calculate_overall_score(
        self,
        result: FlowBalanceResult,
    ) -> float:
        """计算总体评分

        Args:
            result: 分析结果

        Returns:
            float: 总体评分 (0-100)
        """
        score = 100.0

        # 根据不平衡等级扣分
        level_penalties = {
            FlowImbalanceLevel.NORMAL: 0,
            FlowImbalanceLevel.SLIGHT: 10,
            FlowImbalanceLevel.MODERATE: 25,
            FlowImbalanceLevel.SEVERE: 45,
            FlowImbalanceLevel.CRITICAL: 70,
        }
        score -= level_penalties.get(result.imbalance_level, 0)

        # 干涉系数惩罚
        if result.interference_coefficient > 1.2:
            score -= (result.interference_coefficient - 1.0) * 20

        # 稳定性问题
        score = min(score, result.stability_score)

        return max(0, score)

    def _generate_recommendations(
        self,
        result: FlowBalanceResult,
        pump_frequencies: Optional[Dict[int, float]],
    ) -> List[str]:
        """生成优化建议

        Args:
            result: 分析结果
            pump_frequencies: 泵运行频率

        Returns:
            List[str]: 建议列表
        """
        recommendations = []

        if result.imbalance_level == FlowImbalanceLevel.NORMAL:
            recommendations.append("流量分配均衡，运行状态良好")
            return recommendations

        # 根据问题类型生成建议
        for status in result.pump_statuses:
            if status.is_reverse:
                recommendations.append(
                    f"泵{status.pump_id}存在逆流风险，建议：\n"
                    f"  1. 检查止回阀是否正常\n"
                    f"  2. 降低该泵频率或停止该泵\n"
                    f"  3. 检查泵曲线是否严重退化"
                )
            elif status.is_zero_flow:
                recommendations.append(
                    f"泵{status.pump_id}处于零流量状态，建议：\n"
                    f"  1. 检查出口阀门是否全开\n"
                    f"  2. 适当提高该泵频率\n"
                    f"  3. 考虑退出该泵，减少能耗"
                )
            elif status.is_starved:
                if pump_frequencies:
                    freq = pump_frequencies.get(status.pump_id, 50.0)
                    recommendations.append(
                        f"泵{status.pump_id}被抢流（当前频率{freq}Hz），建议提高频率至{min(freq+5, 50)}Hz"
                    )
                else:
                    recommendations.append(
                        f"泵{status.pump_id}被抢流，建议提高运行频率或检查泵性能"
                    )

        # 抢流对建议
        for (dominant, starved) in result.snatching_pairs:
            recommendations.append(
                f"泵{dominant}正在抢泵{starved}的流量，建议：\n"
                f"  1. 降低泵{dominant}频率 或 提高泵{starved}频率\n"
                f"  2. 调整两泵的出口阀门开度\n"
                f"  3. 长期方案：重新匹配泵组曲线"
            )

        # 干涉系数高
        if result.interference_coefficient > 1.15:
            recommendations.append(
                f"并联干涉系数过高（{result.interference_coefficient:.2f}），建议：\n"
                f"  1. 检查各泵曲线是否匹配\n"
                f"  2. 考虑采用同型号泵并联\n"
                f"  3. 采用等效率协调控制策略"
            )

        return recommendations

    def analyze_time_series(
        self,
        station_id: int,
        time_series: List[Dict[str, Any]],
        pump_rated_flows: Optional[Dict[int, float]] = None,
    ) -> Dict[str, Any]:
        """分析时序流量平衡数据

        Args:
            station_id: 泵站ID
            time_series: 时序数据列表 [{'timestamp': ..., 'pump_flows': {...}}, ...]
            pump_rated_flows: 各泵额定流量

        Returns:
            Dict[str, Any]: 时序分析结果
        """
        results = []

        for point in time_series:
            pump_flows = point.get('pump_flows', {})
            system_head = point.get('system_head')
            pump_frequencies = point.get('pump_frequencies')

            result = self.analyze(
                station_id=station_id,
                pump_flows=pump_flows,
                pump_rated_flows=pump_rated_flows,
                system_head=system_head,
                pump_frequencies=pump_frequencies,
            )

            results.append({
                'timestamp': point.get('timestamp'),
                'imbalance_level': result.imbalance_level.value,
                'max_deviation': result.max_deviation,
                'has_flow_snatching': result.has_flow_snatching,
                'interference_coefficient': result.interference_coefficient,
                'overall_score': result.overall_score,
            })

        # 统计分析
        if results:
            avg_score = sum(r['overall_score'] for r in results) / len(results)
            max_deviation = max(r['max_deviation'] for r in results)
            snatching_count = sum(
                1 for r in results if r['has_flow_snatching'])
            snatching_ratio = snatching_count / len(results) * 100

            level_counts = {}
            for r in results:
                level = r['imbalance_level']
                level_counts[level] = level_counts.get(level, 0) + 1

            return {
                'total_points': len(results),
                'average_score': avg_score,
                'max_deviation': max_deviation,
                'snatching_ratio': snatching_ratio,
                'level_distribution': level_counts,
                'details': results,
            }

        return {'total_points': 0, 'details': []}

    def recommend_pump_combination(
        self,
        available_pumps: List[int],
        pump_curves: Dict[int, Dict[str, Any]],
        target_flow: float,
        target_head: float,
    ) -> Dict[str, Any]:
        """推荐抗抢流的泵组合

        选择曲线相近的泵并联，减少抢流现象。

        Args:
            available_pumps: 可用泵ID列表
            pump_curves: 各泵曲线数据
            target_flow: 目标流量
            target_head: 目标扬程

        Returns:
            Dict[str, Any]: 推荐结果
        """
        from itertools import combinations

        best_combination = None
        best_score = 0

        # 遍历所有可能的组合（2-4台泵）
        for n in range(2, min(5, len(available_pumps) + 1)):
            for combo in combinations(available_pumps, n):
                score = self._evaluate_combination(
                    list(combo), pump_curves, target_flow, target_head
                )
                if score > best_score:
                    best_score = score
                    best_combination = list(combo)

        if best_combination:
            return {
                'recommended_pumps': best_combination,
                'score': best_score,
                'reason': self._get_combination_reason(
                    best_combination, pump_curves
                ),
            }

        return {
            'recommended_pumps': available_pumps[:2],
            'score': 50,
            'reason': '无法确定最优组合，默认选择前两台泵',
        }

    def _evaluate_combination(
        self,
        pump_ids: List[int],
        pump_curves: Dict[int, Dict[str, Any]],
        target_flow: float,
        target_head: float,
    ) -> float:
        """评估泵组合的抗抢流能力

        Args:
            pump_ids: 泵ID列表
            pump_curves: 各泵曲线
            target_flow: 目标流量
            target_head: 目标扬程

        Returns:
            float: 评分 (0-100)
        """
        if len(pump_ids) < 2:
            return 0

        # 计算各泵在目标扬程下的流量
        flows = []
        for pump_id in pump_ids:
            curve = pump_curves.get(pump_id)
            if curve:
                flow = self._get_flow_from_curve(curve, target_head)
                if flow:
                    flows.append(flow)

        if len(flows) < 2:
            return 50  # 无法计算，给中等分

        # 评估流量均匀性
        avg_flow = sum(flows) / len(flows)
        max_deviation = max(abs(f - avg_flow) / avg_flow * 100 for f in flows)

        # 偏差越小，分数越高
        if max_deviation < 5:
            return 100
        elif max_deviation < 10:
            return 90
        elif max_deviation < 20:
            return 70
        elif max_deviation < 30:
            return 50
        else:
            return 30

    def _get_combination_reason(
        self,
        pump_ids: List[int],
        pump_curves: Dict[int, Dict[str, Any]],
    ) -> str:
        """获取组合推荐原因

        Args:
            pump_ids: 泵ID列表
            pump_curves: 各泵曲线

        Returns:
            str: 推荐原因
        """
        # 简单实现：检查曲线相似性
        if len(pump_ids) == 2:
            curve1 = pump_curves.get(pump_ids[0], {})
            curve2 = pump_curves.get(pump_ids[1], {})

            h01 = curve1.get('coefficients', {}).get('c', 0)
            h02 = curve2.get('coefficients', {}).get('c', 0)

            if abs(h01 - h02) < 2:
                return f"泵{pump_ids[0]}和泵{pump_ids[1]}额定扬程接近，抢流风险低"

        return f"泵组合{pump_ids}曲线匹配度较好"
