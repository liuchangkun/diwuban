"""
趋势分析器 (app.services.characteristic_curves.shared.trend_analyzer)

分析曲线参数的变化趋势。

版本: v1.0
更新日期: 2025-12-08
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class TrendResult:
    """趋势分析结果

    Attributes:
        trend_type: 趋势类型 ('increasing', 'decreasing', 'stable', 'fluctuating')
        slope: 斜率
        r_squared: R²值
        forecast: 预测值列表
        confidence: 置信度
        details: 详细信息
    """

    trend_type: str
    slope: float
    r_squared: float
    forecast: List[float] = field(default_factory=list)
    confidence: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "trend_type": self.trend_type,
            "slope": self.slope,
            "r_squared": self.r_squared,
            "forecast": self.forecast,
            "confidence": self.confidence,
            "details": self.details,
        }


class TrendAnalyzer:
    """趋势分析器

    分析时间序列数据的趋势。

    Attributes:
        slope_threshold: 斜率阈值（判断稳定的阈值）
        min_r_squared: 最小R²值（判断趋势显著性）
    """

    def __init__(
        self, slope_threshold: float = 0.01, min_r_squared: float = 0.5
    ) -> None:
        """初始化趋势分析器

        Args:
            slope_threshold: 斜率阈值
            min_r_squared: 最小R²值
        """
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.slope_threshold = slope_threshold
        self.min_r_squared = min_r_squared

    def analyze(
        self, values: np.ndarray, time_points: Optional[np.ndarray] = None
    ) -> TrendResult:
        """分析趋势

        Args:
            values: 数据值序列
            time_points: 时间点序列（如果为None，使用索引）

        Returns:
            TrendResult: 趋势分析结果
        """
        if len(values) < 2:
            return TrendResult(
                trend_type="stable", slope=0.0, r_squared=0.0,
                details={"error": "数据点不足"},
            )

        n = len(values)
        x = time_points if time_points is not None else np.arange(n)

        # 线性回归
        x_mean = np.mean(x)
        y_mean = np.mean(values)

        numerator = np.sum((x - x_mean) * (values - y_mean))
        denominator = np.sum((x - x_mean) ** 2)

        if denominator == 0:
            slope = 0.0
            intercept = y_mean
        else:
            slope = float(numerator / denominator)
            intercept = float(y_mean - slope * x_mean)

        # 计算R²
        y_pred = slope * x + intercept
        ss_res = np.sum((values - y_pred) ** 2)
        ss_tot = np.sum((values - y_mean) ** 2)
        r_squared = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0

        # 标准化斜率（相对于均值的变化率）
        normalized_slope = slope / abs(y_mean) if y_mean != 0 else slope

        # 确定趋势类型
        if r_squared < self.min_r_squared:
            trend_type = "fluctuating"
        elif abs(normalized_slope) < self.slope_threshold:
            trend_type = "stable"
        elif slope > 0:
            trend_type = "increasing"
        else:
            trend_type = "decreasing"

        # 计算置信度
        confidence = r_squared if trend_type != "fluctuating" else 1.0 - r_squared

        return TrendResult(
            trend_type=trend_type,
            slope=slope,
            r_squared=r_squared,
            confidence=confidence,
            details={
                "intercept": intercept,
                "normalized_slope": normalized_slope,
                "data_points": n,
            },
        )

    def forecast(
        self, values: np.ndarray, steps: int = 5
    ) -> TrendResult:
        """预测未来值

        Args:
            values: 历史数据
            steps: 预测步数

        Returns:
            TrendResult: 包含预测值的结果
        """
        result = self.analyze(values)

        if result.trend_type == "fluctuating":
            # 波动趋势使用均值预测
            forecast = [float(np.mean(values))] * steps
        else:
            # 使用线性外推
            intercept = result.details.get("intercept", 0)
            n = len(values)
            forecast = [
                result.slope * (n + i) + intercept
                for i in range(steps)
            ]

        result.forecast = forecast
        return result

