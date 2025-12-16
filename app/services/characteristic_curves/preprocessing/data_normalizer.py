"""
数据归一化器 (app.services.characteristic_curves.preprocessing.data_normalizer)

Pipeline阶段8专用：对拟合数据进行归一化处理。

版本: v1.0
创建日期: 2025-12-11
参考文档: 特性曲线开发/开发文档/03_核心模块/05_预处理层.md 第3节
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class NormalizationParams:
    """归一化参数

    Attributes:
        x_min: X轴最小值
        x_max: X轴最大值
        y_min: Y轴最小值
        y_max: Y轴最大值
        x_mean: X轴均值
        x_std: X轴标准差
        y_mean: Y轴均值
        y_std: Y轴标准差
    """
    x_min: float = 0.0
    x_max: float = 1.0
    y_min: float = 0.0
    y_max: float = 1.0
    x_mean: float = 0.0
    x_std: float = 1.0
    y_mean: float = 0.0
    y_std: float = 1.0


class DataNormalizer:
    """数据归一化器（阶段8专用）

    用于Pipeline阶段8的数据归一化处理。
    支持Min-Max归一化和Z-Score标准化。

    使用方式:
        normalizer = DataNormalizer(method='minmax')
        normalized_data, params = normalizer.normalize(data, x_col='Q', y_col='H')
        denormalized_data = normalizer.denormalize(normalized_data, params, x_col='Q', y_col='H')
    """

    def __init__(self, method: str = 'minmax', config: Optional[Dict] = None):
        """初始化归一化器

        Args:
            method: 归一化方法 ('minmax' 或 'zscore')
            config: 额外配置参数
        """
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}")
        self._method = method
        self._config = config or {}

        self._logger.info(
            "[数据归一化器] 初始化",
            extra={"extra_data": {
                "组件": "DataNormalizer",
                "方法": method
            }}
        )

    def normalize(
        self,
        data: pd.DataFrame,
        x_col: str = 'Q',
        y_col: str = 'H'
    ) -> Tuple[pd.DataFrame, NormalizationParams]:
        """归一化数据

        Args:
            data: 原始数据DataFrame
            x_col: X列名
            y_col: Y列名

        Returns:
            Tuple[pd.DataFrame, NormalizationParams]:
                - 归一化后的数据
                - 归一化参数（用于反归一化）
        """
        normalized_data = data.copy()

        if self._method == 'minmax':
            # Min-Max归一化到[0, 1]
            x_min = float(data[x_col].min())
            x_max = float(data[x_col].max())
            y_min = float(data[y_col].min())
            y_max = float(data[y_col].max())

            # 归一化
            if x_max - x_min > 0:
                normalized_data[x_col] = (
                    data[x_col] - x_min) / (x_max - x_min)
            else:
                normalized_data[x_col] = 0.0

            if y_max - y_min > 0:
                normalized_data[y_col] = (
                    data[y_col] - y_min) / (y_max - y_min)
            else:
                normalized_data[y_col] = 0.0

            params = NormalizationParams(
                x_min=x_min, x_max=x_max,
                y_min=y_min, y_max=y_max
            )

        elif self._method == 'zscore':
            # Z-Score标准化
            x_mean = float(data[x_col].mean())
            x_std = float(data[x_col].std())
            y_mean = float(data[y_col].mean())
            y_std = float(data[y_col].std())

            # 标准化
            if x_std > 0:
                normalized_data[x_col] = (data[x_col] - x_mean) / x_std
            else:
                normalized_data[x_col] = 0.0

            if y_std > 0:
                normalized_data[y_col] = (data[y_col] - y_mean) / y_std
            else:
                normalized_data[y_col] = 0.0

            params = NormalizationParams(
                x_mean=x_mean, x_std=x_std,
                y_mean=y_mean, y_std=y_std
            )

        else:
            raise ValueError(f"不支持的归一化方法: {self._method}")

        self._logger.info(
            f"[数据归一化] 完成归一化, 方法={self._method}, "
            f"数据点数={len(data)}"
        )

        return normalized_data, params

    def denormalize(
        self,
        data: pd.DataFrame,
        params: NormalizationParams,
        x_col: str = 'Q',
        y_col: str = 'H'
    ) -> pd.DataFrame:
        """反归一化数据

        Args:
            data: 归一化后的数据
            params: 归一化参数
            x_col: X列名
            y_col: Y列名

        Returns:
            pd.DataFrame: 反归一化后的数据
        """
        denormalized_data = data.copy()

        if self._method == 'minmax':
            # Min-Max反归一化
            denormalized_data[x_col] = data[x_col] * \
                (params.x_max - params.x_min) + params.x_min
            denormalized_data[y_col] = data[y_col] * \
                (params.y_max - params.y_min) + params.y_min

        elif self._method == 'zscore':
            # Z-Score反标准化
            denormalized_data[x_col] = data[x_col] * \
                params.x_std + params.x_mean
            denormalized_data[y_col] = data[y_col] * \
                params.y_std + params.y_mean

        else:
            raise ValueError(f"不支持的归一化方法: {self._method}")

        self._logger.info(
            f"[数据反归一化] 完成反归一化, 方法={self._method}, "
            f"数据点数={len(data)}"
        )

        return denormalized_data

    def fit(
        self,
        x_values: np.ndarray,
        y_values: np.ndarray
    ) -> NormalizationParams:
        """拟合归一化参数（用于单独使用）

        Args:
            x_values: X轴数据
            y_values: Y轴数据

        Returns:
            NormalizationParams: 归一化参数
        """
        if self._method == 'minmax':
            return NormalizationParams(
                x_min=float(x_values.min()),
                x_max=float(x_values.max()),
                y_min=float(y_values.min()),
                y_max=float(y_values.max())
            )
        elif self._method == 'zscore':
            return NormalizationParams(
                x_mean=float(x_values.mean()),
                x_std=float(x_values.std()),
                y_mean=float(y_values.mean()),
                y_std=float(y_values.std())
            )
        else:
            raise ValueError(f"不支持的归一化方法: {self._method}")

    def transform_x(
        self,
        x_values: np.ndarray,
        params: NormalizationParams
    ) -> np.ndarray:
        """归一化X值（单独使用）

        Args:
            x_values: X轴数据
            params: 归一化参数

        Returns:
            np.ndarray: 归一化后的X值
        """
        if self._method == 'minmax':
            if params.x_max - params.x_min > 0:
                return (x_values - params.x_min) / (params.x_max - params.x_min)
            else:
                return np.zeros_like(x_values)
        elif self._method == 'zscore':
            if params.x_std > 0:
                return (x_values - params.x_mean) / params.x_std
            else:
                return np.zeros_like(x_values)
        else:
            raise ValueError(f"不支持的归一化方法: {self._method}")

    def transform_y(
        self,
        y_values: np.ndarray,
        params: NormalizationParams
    ) -> np.ndarray:
        """归一化Y值（单独使用）

        Args:
            y_values: Y轴数据
            params: 归一化参数

        Returns:
            np.ndarray: 归一化后的Y值
        """
        if self._method == 'minmax':
            if params.y_max - params.y_min > 0:
                return (y_values - params.y_min) / (params.y_max - params.y_min)
            else:
                return np.zeros_like(y_values)
        elif self._method == 'zscore':
            if params.y_std > 0:
                return (y_values - params.y_mean) / params.y_std
            else:
                return np.zeros_like(y_values)
        else:
            raise ValueError(f"不支持的归一化方法: {self._method}")

    def inverse_transform_y(
        self,
        y_values: np.ndarray,
        params: NormalizationParams
    ) -> np.ndarray:
        """反归一化Y值（用于拟合结果）

        Args:
            y_values: 归一化后的Y值
            params: 归一化参数

        Returns:
            np.ndarray: 反归一化后的Y值
        """
        if self._method == 'minmax':
            return y_values * (params.y_max - params.y_min) + params.y_min
        elif self._method == 'zscore':
            return y_values * params.y_std + params.y_mean
        else:
            raise ValueError(f"不支持的归一化方法: {self._method}")
