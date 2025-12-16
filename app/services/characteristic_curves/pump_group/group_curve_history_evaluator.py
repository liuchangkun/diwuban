"""
泵组曲线历史评估器 (app.services.characteristic_curves.pump_group.group_curve_history_evaluator)

评估当前拟合曲线与历史曲线的变化趋势，检测性能退化。

核心功能：
- 曲线变化趋势分析（当前vs历史偏差）
- 性能退化检测（H0下降、效率下降）
- 版本一致性检查（异常跳变检测）
- 生成历史评估报告

版本: v1.0
创建日期: 2025-12-14
参考文档: 08_泵组直接拟合.md 第13.2节
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class HistoryEvaluation:
    """历史评估结果"""
    # 基本信息
    station_id: int
    pump_combination: List[int]
    curve_type: str
    evaluated_at: datetime = field(default_factory=datetime.now)

    # 评估结果
    has_degradation: bool = False  # 是否存在性能退化
    degradation_severity: str = "none"  # none/mild/moderate/severe
    trend_direction: str = "stable"  # improving/stable/degrading

    # 变化指标
    h0_change_percent: float = 0.0  # 零流量扬程变化百分比
    efficiency_change_percent: float = 0.0  # 效率变化百分比
    curve_shift_percent: float = 0.0  # 曲线整体偏移百分比

    # 版本一致性
    version_consistency: bool = True  # 版本间是否一致
    anomaly_versions: List[str] = field(default_factory=list)  # 异常版本列表

    # 详细信息
    comparison_points: int = 0  # 对比点数
    history_versions_used: int = 0  # 使用的历史版本数
    details: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "station_id": self.station_id,
            "pump_combination": self.pump_combination,
            "curve_type": self.curve_type,
            "evaluated_at": self.evaluated_at.isoformat(),
            "has_degradation": self.has_degradation,
            "degradation_severity": self.degradation_severity,
            "trend_direction": self.trend_direction,
            "h0_change_percent": self.h0_change_percent,
            "efficiency_change_percent": self.efficiency_change_percent,
            "curve_shift_percent": self.curve_shift_percent,
            "version_consistency": self.version_consistency,
            "anomaly_versions": self.anomaly_versions,
            "comparison_points": self.comparison_points,
            "history_versions_used": self.history_versions_used,
            "details": self.details,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
        }


class GroupCurveHistoryEvaluator:
    """泵组曲线历史评估器

    职责：
    1. 对比当前曲线与历史曲线的变化
    2. 检测性能退化（扬程下降、效率降低）
    3. 检查版本间一致性，发现异常跳变
    4. 生成评估报告和建议

    物理背景：
    - 泵性能随运行时间会逐渐退化
    - 叶轮磨损导致H0下降
    - 密封磨损导致效率下降
    - 正常退化应是渐进的，突变通常意味着异常
    """

    def __init__(
        self,
        storage=None,
        degradation_threshold: float = 0.05,
        anomaly_threshold: float = 0.10,
        min_history_versions: int = 3
    ):
        """初始化

        Args:
            storage: GroupCurveStorage实例（可选，用于加载历史数据）
            degradation_threshold: 退化判定阈值（5%）
            anomaly_threshold: 异常跳变阈值（10%）
            min_history_versions: 趋势分析所需最少历史版本数
        """
        self._storage = storage
        self._degradation_threshold = degradation_threshold
        self._anomaly_threshold = anomaly_threshold
        self._min_history_versions = min_history_versions
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}")

    def evaluate(
        self,
        current_result: Any,
        station_id: int,
        pump_combination: List[int],
        history_results: Optional[List[Any]] = None
    ) -> HistoryEvaluation:
        """评估当前曲线与历史曲线的变化

        Args:
            current_result: 当前拟合结果（DirectFitResult或GroupFitResult）
            station_id: 泵站ID
            pump_combination: 泵组合
            history_results: 历史拟合结果列表（可选，按时间排序）

        Returns:
            HistoryEvaluation: 历史评估结果
        """
        curve_type = getattr(current_result, 'curve_type', 'qh')

        evaluation = HistoryEvaluation(
            station_id=station_id,
            pump_combination=pump_combination,
            curve_type=curve_type,
        )

        # 如果没有提供历史数据且有storage，尝试加载
        if history_results is None and self._storage is not None:
            history_results = self._load_history(
                station_id, pump_combination, curve_type)

        if not history_results:
            evaluation.warnings.append("无历史数据可供对比")
            self._logger.warning(
                f"[历史评估] station={station_id}, 泵组合={pump_combination}: 无历史数据"
            )
            return evaluation

        evaluation.history_versions_used = len(history_results)

        # 1. 曲线变化趋势分析
        self._analyze_trend(current_result, history_results, evaluation)

        # 2. 性能退化检测
        self._detect_degradation(current_result, history_results, evaluation)

        # 3. 版本一致性检查
        self._check_version_consistency(
            current_result, history_results, evaluation)

        # 4. 生成建议
        self._generate_recommendations(evaluation)

        self._logger.info(
            f"[历史评估] station={station_id}, 泵组合={pump_combination}, "
            f"退化={evaluation.has_degradation}, 趋势={evaluation.trend_direction}"
        )

        return evaluation

    def _load_history(
        self,
        station_id: int,
        pump_combination: List[int],
        curve_type: str
    ) -> List[Any]:
        """从存储加载历史数据"""
        if self._storage is None:
            return []

        try:
            # 假设storage有list_versions方法
            combination_key = ",".join(map(str, sorted(pump_combination)))
            # 这里需要根据实际storage接口调整
            return []
        except Exception as e:
            self._logger.warning(f"[历史评估] 加载历史数据失败: {e}")
            return []

    def _analyze_trend(
        self,
        current: Any,
        history: List[Any],
        evaluation: HistoryEvaluation
    ) -> None:
        """分析曲线变化趋势"""
        if len(history) < 2:
            evaluation.trend_direction = "unknown"
            return

        # 提取H0（零流量扬程）历史值
        h0_values = []
        for result in history:
            h0 = self._extract_h0(result)
            if h0 is not None:
                h0_values.append(h0)

        current_h0 = self._extract_h0(current)
        if current_h0 is not None:
            h0_values.append(current_h0)

        if len(h0_values) < 2:
            return

        # 计算变化趋势（线性回归斜率）
        n = len(h0_values)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(h0_values) / n

        numerator = sum((x[i] - x_mean) * (h0_values[i] - y_mean)
                        for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator > 0:
            slope = numerator / denominator
            relative_slope = slope / y_mean if y_mean > 0 else 0

            if relative_slope < -0.01:  # 每版本下降超过1%
                evaluation.trend_direction = "degrading"
            elif relative_slope > 0.01:
                evaluation.trend_direction = "improving"
            else:
                evaluation.trend_direction = "stable"

            evaluation.details["h0_trend_slope"] = slope
            evaluation.details["h0_relative_slope"] = relative_slope

    def _detect_degradation(
        self,
        current: Any,
        history: List[Any],
        evaluation: HistoryEvaluation
    ) -> None:
        """检测性能退化"""
        if not history:
            return

        # 与最近的历史版本对比
        latest_history = history[-1]

        # 1. H0变化检测
        current_h0 = self._extract_h0(current)
        history_h0 = self._extract_h0(latest_history)

        if current_h0 is not None and history_h0 is not None and history_h0 > 0:
            h0_change = (current_h0 - history_h0) / history_h0
            evaluation.h0_change_percent = h0_change * 100

            if h0_change < -self._degradation_threshold:
                evaluation.has_degradation = True
                evaluation.warnings.append(
                    f"H0下降{abs(h0_change)*100:.1f}%（阈值{self._degradation_threshold*100:.0f}%）"
                )

        # 2. 效率变化检测（如果有效率数据）
        current_eta = self._extract_efficiency(current)
        history_eta = self._extract_efficiency(latest_history)

        if current_eta is not None and history_eta is not None and history_eta > 0:
            eta_change = (current_eta - history_eta) / history_eta
            evaluation.efficiency_change_percent = eta_change * 100

            if eta_change < -self._degradation_threshold:
                evaluation.has_degradation = True
                evaluation.warnings.append(
                    f"效率下降{abs(eta_change)*100:.1f}%"
                )

        # 3. 曲线整体偏移检测
        shift = self._calculate_curve_shift(current, latest_history)
        evaluation.curve_shift_percent = shift * 100

        if shift > self._degradation_threshold:
            evaluation.has_degradation = True
            evaluation.warnings.append(f"曲线整体偏移{shift*100:.1f}%")

        # 4. 判定退化严重程度
        if evaluation.has_degradation:
            max_change = max(
                abs(evaluation.h0_change_percent),
                abs(evaluation.efficiency_change_percent),
                evaluation.curve_shift_percent
            )
            if max_change > 15:
                evaluation.degradation_severity = "severe"
            elif max_change > 10:
                evaluation.degradation_severity = "moderate"
            else:
                evaluation.degradation_severity = "mild"

    def _check_version_consistency(
        self,
        current: Any,
        history: List[Any],
        evaluation: HistoryEvaluation
    ) -> None:
        """检查版本间一致性，发现异常跳变"""
        all_versions = history + [current]

        if len(all_versions) < 2:
            return

        evaluation.version_consistency = True
        evaluation.comparison_points = len(all_versions) - 1

        for i in range(1, len(all_versions)):
            prev = all_versions[i - 1]
            curr = all_versions[i]

            # 计算相邻版本间的变化
            prev_h0 = self._extract_h0(prev)
            curr_h0 = self._extract_h0(curr)

            if prev_h0 is not None and curr_h0 is not None and prev_h0 > 0:
                change = abs(curr_h0 - prev_h0) / prev_h0

                if change > self._anomaly_threshold:
                    evaluation.version_consistency = False
                    version_id = getattr(curr, 'version', f"v{i}")
                    evaluation.anomaly_versions.append(str(version_id))
                    evaluation.warnings.append(
                        f"版本{version_id}存在异常跳变（变化{change*100:.1f}%）"
                    )

    def _generate_recommendations(self, evaluation: HistoryEvaluation) -> None:
        """生成评估建议"""
        if evaluation.has_degradation:
            if evaluation.degradation_severity == "severe":
                evaluation.recommendations.append("建议立即检查泵组运行状态")
                evaluation.recommendations.append("可能需要维护或更换叶轮")
            elif evaluation.degradation_severity == "moderate":
                evaluation.recommendations.append("建议安排计划性维护")
                evaluation.recommendations.append("持续监控性能变化趋势")
            else:
                evaluation.recommendations.append("轻度退化属正常范围，继续监控")

        if not evaluation.version_consistency:
            evaluation.recommendations.append("检查异常版本的数据质量")
            evaluation.recommendations.append("确认是否存在运行工况突变")

        if evaluation.trend_direction == "degrading":
            evaluation.recommendations.append("性能呈下降趋势，建议增加监控频率")
        elif evaluation.trend_direction == "improving":
            evaluation.recommendations.append("性能改善，可能是维护后的正常现象")

    def _extract_h0(self, result: Any) -> Optional[float]:
        """从结果中提取H0（零流量扬程）"""
        # DirectFitResult: 从coefficients提取
        if hasattr(result, 'coefficients'):
            coeffs = result.coefficients
            if isinstance(coeffs, list) and len(coeffs) > 0:
                return coeffs[0]  # 多项式常数项即H0
            elif isinstance(coeffs, dict):
                return coeffs.get('H0') or coeffs.get('c0') or coeffs.get('a')

        # 尝试其他字段
        if hasattr(result, 'h0'):
            return result.h0

        return None

    def _extract_efficiency(self, result: Any) -> Optional[float]:
        """从结果中提取效率"""
        if hasattr(result, 'eta_total'):
            return result.eta_total
        if hasattr(result, 'efficiency'):
            return result.efficiency
        if hasattr(result, 'metadata'):
            return result.metadata.get('eta_bep')
        return None

    def _calculate_curve_shift(self, current: Any, reference: Any) -> float:
        """计算曲线整体偏移（相对值）"""
        # 简化实现：比较R²或RMSE的变化
        current_r2 = getattr(current, 'r_squared', 0)
        ref_r2 = getattr(reference, 'r_squared', 0)

        if ref_r2 > 0:
            return abs(current_r2 - ref_r2) / ref_r2

        return 0.0

    def compare_with_baseline(
        self,
        current_result: Any,
        baseline_result: Any,
        Q_points: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """与基准曲线对比

        Args:
            current_result: 当前曲线结果
            baseline_result: 基准曲线结果
            Q_points: 对比流量点列表

        Returns:
            Dict: 对比结果
        """
        if Q_points is None:
            Q_points = [100, 200, 300, 400, 500, 600, 700, 800]

        comparison = {
            "Q_points": Q_points,
            "H_current": [],
            "H_baseline": [],
            "H_diff": [],
            "H_diff_percent": [],
        }

        for Q in Q_points:
            try:
                H_curr = self._predict_at_Q(current_result, Q)
                H_base = self._predict_at_Q(baseline_result, Q)

                if H_curr is not None and H_base is not None:
                    comparison["H_current"].append(H_curr)
                    comparison["H_baseline"].append(H_base)
                    comparison["H_diff"].append(H_curr - H_base)
                    if H_base > 0:
                        comparison["H_diff_percent"].append(
                            (H_curr - H_base) / H_base * 100
                        )
                    else:
                        comparison["H_diff_percent"].append(0)
            except Exception:
                continue

        # 计算统计指标
        if comparison["H_diff_percent"]:
            comparison["mean_diff_percent"] = (
                sum(comparison["H_diff_percent"]) /
                len(comparison["H_diff_percent"])
            )
            comparison["max_diff_percent"] = max(
                abs(d) for d in comparison["H_diff_percent"]
            )

        return comparison

    def _predict_at_Q(self, result: Any, Q: float) -> Optional[float]:
        """在给定流量点预测扬程"""
        # 尝试使用predict方法
        if hasattr(result, 'predict'):
            try:
                return result.predict(Q)
            except Exception:
                pass

        # 尝试使用coefficients计算多项式
        if hasattr(result, 'coefficients'):
            coeffs = result.coefficients
            if isinstance(coeffs, list):
                return sum(c * (Q ** i) for i, c in enumerate(coeffs))

        return None
