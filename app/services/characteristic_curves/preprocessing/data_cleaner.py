"""
数据清洗器 (app.services.characteristic_curves.preprocessing.data_cleaner)

清洗原始数据，处理缺失值和异常值。

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/03_核心模块/05_预处理层.md 第1节
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class CleaningResult:
    """清洗结果

    Attributes:
        cleaned_data: 清洗后的数据
        removed_count: 移除的数据点数
        outlier_indices: 异常值索引
        missing_indices: 缺失值索引
        duplicate_indices: 重复值索引
        stats: 统计信息
    """

    cleaned_data: pd.DataFrame
    removed_count: int = 0
    outlier_indices: List[int] = field(default_factory=list)
    missing_indices: List[int] = field(default_factory=list)
    duplicate_indices: List[int] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)


class DataCleaner:
    """数据清洗器

    支持的异常值检测方法:
        - iqr: 四分位距法
        - zscore: Z-Score法
        - physics: 物理约束法（需要额定参数）

    Attributes:
        outlier_method: 异常值检测方法
        outlier_threshold: 异常值阈值
    """

    def __init__(
        self,
        outlier_method: Literal["iqr", "zscore", "physics"] = "iqr",
        outlier_threshold: float = 1.5,
        rated_params: Optional[Dict[str, float]] = None,
    ) -> None:
        """初始化数据清洗器

        Args:
            outlier_method: 异常值检测方法
            outlier_threshold: 异常值阈值 (IQR倍数或Z-Score阈值)
            rated_params: 设备额定参数（physics方法需要）
        """
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.outlier_method = outlier_method
        self.outlier_threshold = outlier_threshold
        self.rated_params = rated_params or {}

    def clean(
        self,
        data: pd.DataFrame,
        x_col: str = "Q",
        y_col: str = "H",
        remove_outliers: bool = True,
        handle_missing: bool = True,
        remove_duplicates: bool = True,
    ) -> CleaningResult:
        """执行数据清洗

        Args:
            data: 原始数据
            x_col: X列名
            y_col: Y列名
            remove_outliers: 是否移除异常值
            handle_missing: 是否处理缺失值
            remove_duplicates: 是否移除重复值

        Returns:
            CleaningResult: 清洗结果
        """
        df = data.copy()
        original_count = len(df)
        outlier_indices: List[int] = []
        missing_indices: List[int] = []
        duplicate_indices: List[int] = []

        # 处理缺失值
        if handle_missing:
            missing_mask = df[[x_col, y_col]].isna().any(axis=1)
            missing_indices = df[missing_mask].index.tolist()
            df = df.dropna(subset=[x_col, y_col])

        # 移除重复值
        if remove_duplicates:
            dup_mask = df.duplicated(subset=[x_col], keep="first")
            duplicate_indices = df[dup_mask].index.tolist()
            df = df[~dup_mask]

        # 检测并移除异常值
        if remove_outliers and len(df) > 0:
            outlier_mask = self.detect_outliers(df[y_col].values)
            outlier_indices = df[outlier_mask].index.tolist()
            df = df[~outlier_mask]

        removed_count = original_count - len(df)

        return CleaningResult(
            cleaned_data=df.reset_index(drop=True),
            removed_count=removed_count,
            outlier_indices=outlier_indices,
            missing_indices=missing_indices,
            duplicate_indices=duplicate_indices,
            stats={
                "original_count": original_count,
                "final_count": len(df),
                "removed_ratio": removed_count / original_count if original_count > 0 else 0,
            },
        )

    def detect_outliers(self, values: np.ndarray) -> np.ndarray:
        """检测异常值

        Args:
            values: 数据数组

        Returns:
            np.ndarray: 布尔掩码，True表示异常值
        """
        if self.outlier_method == "iqr":
            return self._detect_outliers_iqr(values)
        elif self.outlier_method == "zscore":
            return self._detect_outliers_zscore(values)
        elif self.outlier_method == "physics":
            return self._detect_outliers_physics(values)
        else:
            raise ValueError(f"不支持的异常值检测方法: {self.outlier_method}")

    def _detect_outliers_iqr(self, values: np.ndarray) -> np.ndarray:
        """IQR法检测异常值"""
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        lower = q1 - self.outlier_threshold * iqr
        upper = q3 + self.outlier_threshold * iqr
        return (values < lower) | (values > upper)

    def _detect_outliers_zscore(self, values: np.ndarray) -> np.ndarray:
        """Z-Score法检测异常值"""
        mean = np.mean(values)
        std = np.std(values)
        if std == 0:
            return np.zeros(len(values), dtype=bool)
        z_scores = np.abs((values - mean) / std)
        return z_scores > self.outlier_threshold

    def _detect_outliers_physics(self, values: np.ndarray) -> np.ndarray:
        """物理约束法检测异常值（需要额定参数）"""
        # 使用额定参数定义物理边界
        rated_value = self.rated_params.get("rated_head") or self.rated_params.get(
            "rated_power"
        )
        if rated_value:
            lower = 0
            upper = 1.5 * rated_value
            return (values < lower) | (values > upper)
        # 如果没有额定参数，回退到IQR
        return self._detect_outliers_iqr(values)

    def handle_missing(
        self, data: pd.DataFrame, method: Literal["drop", "interpolate", "fill"] = "drop"
    ) -> pd.DataFrame:
        """处理缺失值"""
        if method == "drop":
            return data.dropna()
        elif method == "interpolate":
            return data.interpolate(method="linear")
        elif method == "fill":
            return data.fillna(method="ffill").fillna(method="bfill")
        else:
            raise ValueError(f"不支持的缺失值处理方法: {method}")

    def remove_duplicates(
        self, data: pd.DataFrame, subset: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """移除重复值"""
        return data.drop_duplicates(subset=subset, keep="first")

