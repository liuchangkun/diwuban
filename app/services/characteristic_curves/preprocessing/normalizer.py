"""
归一化器 (app.services.characteristic_curves.preprocessing.normalizer)

提供数据归一化和标准化功能。

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/03_核心模块/05_预处理层.md 第2节
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional, Tuple

import numpy as np


@dataclass
class NormalizationParams:
    """归一化参数

    Attributes:
        method: 归一化方法
        min_val: 最小值 (Min-Max)
        max_val: 最大值 (Min-Max)
        mean: 均值 (Z-Score)
        std: 标准差 (Z-Score)
    """

    method: str
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    mean: Optional[float] = None
    std: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "method": self.method,
            "min_val": self.min_val,
            "max_val": self.max_val,
            "mean": self.mean,
            "std": self.std,
        }


class Normalizer:
    """归一化器

    支持的归一化方法:
        - minmax: Min-Max归一化到 [0, 1]
        - zscore: Z-Score标准化 (均值0, 标准差1)
        - robust: 鲁棒标准化 (使用中位数和IQR)

    Attributes:
        method: 归一化方法
        params: 归一化参数（fit后保存）
    """

    def __init__(
        self, method: Literal["minmax", "zscore", "robust"] = "minmax"
    ) -> None:
        """初始化归一化器

        Args:
            method: 归一化方法
        """
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.method = method
        self.params: Optional[NormalizationParams] = None

    def fit(self, values: np.ndarray) -> "Normalizer":
        """拟合归一化参数

        Args:
            values: 输入数据

        Returns:
            self: 返回自身以支持链式调用
        """
        if self.method == "minmax":
            self.params = NormalizationParams(
                method="minmax",
                min_val=float(np.min(values)),
                max_val=float(np.max(values)),
            )
        elif self.method == "zscore":
            self.params = NormalizationParams(
                method="zscore",
                mean=float(np.mean(values)),
                std=float(np.std(values)),
            )
        elif self.method == "robust":
            q1 = float(np.percentile(values, 25))
            q3 = float(np.percentile(values, 75))
            self.params = NormalizationParams(
                method="robust",
                mean=float(np.median(values)),  # 使用中位数
                std=q3 - q1,  # 使用IQR
            )
        else:
            raise ValueError(f"不支持的归一化方法: {self.method}")

        return self

    def transform(self, values: np.ndarray) -> np.ndarray:
        """执行归一化变换

        Args:
            values: 输入数据

        Returns:
            np.ndarray: 归一化后的数据
        """
        if self.params is None:
            raise ValueError("请先调用 fit() 方法")

        if self.method == "minmax":
            range_val = self.params.max_val - self.params.min_val
            if range_val == 0:
                return np.zeros_like(values)
            return (values - self.params.min_val) / range_val

        elif self.method == "zscore":
            if self.params.std == 0:
                return np.zeros_like(values)
            return (values - self.params.mean) / self.params.std

        elif self.method == "robust":
            if self.params.std == 0:
                return np.zeros_like(values)
            return (values - self.params.mean) / self.params.std

        else:
            raise ValueError(f"不支持的归一化方法: {self.method}")

    def fit_transform(self, values: np.ndarray) -> np.ndarray:
        """拟合并变换

        Args:
            values: 输入数据

        Returns:
            np.ndarray: 归一化后的数据
        """
        return self.fit(values).transform(values)

    def inverse_transform(self, values: np.ndarray) -> np.ndarray:
        """逆变换（还原原始数据）

        Args:
            values: 归一化后的数据

        Returns:
            np.ndarray: 还原后的数据
        """
        if self.params is None:
            raise ValueError("请先调用 fit() 方法")

        if self.method == "minmax":
            range_val = self.params.max_val - self.params.min_val
            return values * range_val + self.params.min_val

        elif self.method in ("zscore", "robust"):
            return values * self.params.std + self.params.mean

        else:
            raise ValueError(f"不支持的归一化方法: {self.method}")

    def get_params(self) -> Optional[NormalizationParams]:
        """获取归一化参数"""
        return self.params

    def set_params(self, params: NormalizationParams) -> None:
        """设置归一化参数（用于加载已保存的参数）"""
        self.params = params
        self.method = params.method

