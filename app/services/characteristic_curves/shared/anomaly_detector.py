"""
异常检测器 (app.services.characteristic_curves.shared.anomaly_detector)

检测曲线数据中的异常点。

版本: v1.0
更新日期: 2025-12-08
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np


class AnomalyMethod(str, Enum):
    """异常检测方法"""

    ZSCORE = "zscore"
    IQR = "iqr"
    MAD = "mad"  # Median Absolute Deviation


@dataclass
class AnomalyResult:
    """异常检测结果

    Attributes:
        has_anomalies: 是否存在异常
        anomaly_indices: 异常点索引
        anomaly_count: 异常点数量
        anomaly_ratio: 异常比例
        method: 检测方法
        details: 详细信息
    """

    has_anomalies: bool
    anomaly_indices: List[int]
    anomaly_count: int
    anomaly_ratio: float
    method: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "has_anomalies": self.has_anomalies,
            "anomaly_indices": self.anomaly_indices,
            "anomaly_count": self.anomaly_count,
            "anomaly_ratio": self.anomaly_ratio,
            "method": self.method,
            "details": self.details,
        }


class AnomalyDetector:
    """异常检测器

    支持多种异常检测方法。

    Attributes:
        method: 检测方法
        threshold: 异常阈值
    """

    def __init__(
        self, method: str = "zscore", threshold: float = 3.0
    ) -> None:
        """初始化异常检测器

        Args:
            method: 检测方法 ('zscore', 'iqr', 'mad')
            threshold: 异常阈值
        """
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.method = method
        self.threshold = threshold

    def detect(self, values: np.ndarray) -> AnomalyResult:
        """检测异常点

        Args:
            values: 数据数组

        Returns:
            AnomalyResult: 异常检测结果
        """
        if len(values) < 3:
            return AnomalyResult(
                has_anomalies=False, anomaly_indices=[], anomaly_count=0,
                anomaly_ratio=0.0, method=self.method,
                details={"error": "数据点不足"},
            )

        if self.method == "zscore":
            anomaly_mask, details = self._detect_zscore(values)
        elif self.method == "iqr":
            anomaly_mask, details = self._detect_iqr(values)
        elif self.method == "mad":
            anomaly_mask, details = self._detect_mad(values)
        else:
            raise ValueError(f"不支持的检测方法: {self.method}")

        anomaly_indices = np.where(anomaly_mask)[0].tolist()
        anomaly_count = len(anomaly_indices)
        anomaly_ratio = anomaly_count / len(values)

        return AnomalyResult(
            has_anomalies=anomaly_count > 0,
            anomaly_indices=anomaly_indices,
            anomaly_count=anomaly_count,
            anomaly_ratio=anomaly_ratio,
            method=self.method,
            details=details,
        )

    def _detect_zscore(self, values: np.ndarray) -> tuple:
        """Z-Score方法检测"""
        mean = np.mean(values)
        std = np.std(values)
        if std == 0:
            return np.zeros(len(values), dtype=bool), {"mean": mean, "std": 0}
        z_scores = np.abs((values - mean) / std)
        mask = z_scores > self.threshold
        return mask, {"mean": float(mean), "std": float(std), "threshold": self.threshold}

    def _detect_iqr(self, values: np.ndarray) -> tuple:
        """IQR方法检测"""
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        lower = q1 - self.threshold * iqr
        upper = q3 + self.threshold * iqr
        mask = (values < lower) | (values > upper)
        return mask, {"q1": float(q1), "q3": float(q3), "iqr": float(iqr), "lower": float(lower), "upper": float(upper)}

    def _detect_mad(self, values: np.ndarray) -> tuple:
        """MAD方法检测"""
        median = np.median(values)
        mad = np.median(np.abs(values - median))
        if mad == 0:
            return np.zeros(len(values), dtype=bool), {"median": median, "mad": 0}
        # Modified Z-score
        modified_z = 0.6745 * (values - median) / mad
        mask = np.abs(modified_z) > self.threshold
        return mask, {"median": float(median), "mad": float(mad), "threshold": self.threshold}

    def remove_anomalies(self, values: np.ndarray) -> np.ndarray:
        """移除异常点，返回清洗后的数据"""
        result = self.detect(values)
        if not result.has_anomalies:
            return values
        mask = np.ones(len(values), dtype=bool)
        mask[result.anomaly_indices] = False
        return values[mask]

