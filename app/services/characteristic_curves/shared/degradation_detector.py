"""
性能衰减检测器 (app.services.characteristic_curves.shared.degradation_detector)

检测泵性能衰减趋势。

版本: v1.0
更新日期: 2025-12-08
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class DegradationResult:
    """衰减检测结果

    Attributes:
        is_degraded: 是否存在衰减
        degradation_rate: 衰减率 (%/年)
        trend_direction: 趋势方向 ('stable', 'declining', 'improving')
        confidence: 置信度
        details: 详细信息
    """

    is_degraded: bool
    degradation_rate: float
    trend_direction: str
    confidence: float
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "is_degraded": self.is_degraded,
            "degradation_rate": self.degradation_rate,
            "trend_direction": self.trend_direction,
            "confidence": self.confidence,
            "details": self.details,
        }


class DegradationDetector:
    """性能衰减检测器

    通过比较历史曲线检测泵性能衰减。

    Attributes:
        threshold: 衰减阈值 (%/年)
        min_confidence: 最小置信度
    """

    def __init__(self, threshold: float = 2.0, min_confidence: float = 0.8) -> None:
        """初始化衰减检测器

        Args:
            threshold: 衰减阈值 (%/年)
            min_confidence: 最小置信度
        """
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.threshold = threshold
        self.min_confidence = min_confidence

    def detect(
        self,
        current_values: np.ndarray,
        baseline_values: np.ndarray,
        time_delta_years: float = 1.0,
    ) -> DegradationResult:
        """检测性能衰减

        Args:
            current_values: 当前性能值
            baseline_values: 基线性能值
            time_delta_years: 时间间隔（年）

        Returns:
            DegradationResult: 衰减检测结果
        """
        if len(current_values) != len(baseline_values):
            raise ValueError("当前值和基线值长度必须相同")

        if time_delta_years <= 0:
            raise ValueError("时间间隔必须为正数")

        # 计算相对变化
        with np.errstate(divide="ignore", invalid="ignore"):
            relative_change = (current_values - baseline_values) / np.abs(baseline_values) * 100
            relative_change = np.nan_to_num(relative_change, 0)

        # 计算年均衰减率
        mean_change = float(np.mean(relative_change))
        annual_rate = mean_change / time_delta_years

        # 确定趋势方向
        if abs(annual_rate) < 0.5:
            direction = "stable"
        elif annual_rate < 0:
            direction = "declining"
        else:
            direction = "improving"

        # 计算置信度（基于变化的一致性）
        std_change = float(np.std(relative_change))
        confidence = max(0.0, 1.0 - std_change / 20.0)  # 标准差越小，置信度越高

        # 判断是否存在衰减
        is_degraded = direction == "declining" and abs(annual_rate) >= self.threshold and confidence >= self.min_confidence

        return DegradationResult(
            is_degraded=is_degraded,
            degradation_rate=abs(annual_rate) if direction == "declining" else 0.0,
            trend_direction=direction,
            confidence=confidence,
            details={
                "mean_change_percent": mean_change,
                "std_change_percent": std_change,
                "annual_rate": annual_rate,
                "threshold": self.threshold,
            },
        )

    def detect_from_series(
        self,
        values_series: List[np.ndarray],
        time_points_years: List[float],
    ) -> DegradationResult:
        """从时间序列检测衰减

        Args:
            values_series: 性能值序列列表
            time_points_years: 时间点列表（年）

        Returns:
            DegradationResult: 衰减检测结果
        """
        if len(values_series) < 2:
            return DegradationResult(
                is_degraded=False, degradation_rate=0.0,
                trend_direction="stable", confidence=0.0,
                details={"error": "需要至少2个时间点"},
            )

        # 使用第一个时间点作为基线，最后一个作为当前值
        baseline = values_series[0]
        current = values_series[-1]
        time_delta = time_points_years[-1] - time_points_years[0]

        return self.detect(current, baseline, time_delta)

