"""
特征工程 (app.services.characteristic_curves.preprocessing.feature_engineer)

生成多项式特征和交互特征。

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/03_核心模块/05_预处理层.md 第3节
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class FeatureInfo:
    """特征信息

    Attributes:
        name: 特征名称
        degree: 多项式阶数
        importance: 重要性评分
        source_columns: 来源列
    """

    name: str
    degree: int = 1
    importance: float = 0.0
    source_columns: List[str] = field(default_factory=list)


class FeatureEngineer:
    """特征工程器

    支持的特征类型:
        - 多项式特征: x, x², x³, ...
        - 交互特征: x1*x2, x1*x3, ...
        - 比率特征: x1/x2
        - 对数特征: log(x)

    Attributes:
        max_degree: 最大多项式阶数
        include_interaction: 是否包含交互特征
        feature_names: 生成的特征名称列表
    """

    def __init__(
        self,
        max_degree: int = 3,
        include_interaction: bool = True,
        include_log: bool = False,
    ) -> None:
        """初始化特征工程器

        Args:
            max_degree: 最大多项式阶数
            include_interaction: 是否包含交互特征
            include_log: 是否包含对数特征
        """
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.max_degree = max_degree
        self.include_interaction = include_interaction
        self.include_log = include_log
        self.feature_names: List[str] = []
        self._feature_info: List[FeatureInfo] = []

    def generate_features(
        self, X: np.ndarray, column_names: Optional[List[str]] = None
    ) -> np.ndarray:
        """生成多项式特征

        Args:
            X: 输入特征数组 (n_samples, n_features)
            column_names: 列名列表

        Returns:
            np.ndarray: 扩展后的特征数组
        """
        if X.ndim == 1:
            X = X.reshape(-1, 1)

        n_samples, n_features = X.shape
        column_names = column_names or [f"x{i}" for i in range(n_features)]

        features = [X]  # 原始特征
        self.feature_names = list(column_names)
        self._feature_info = [
            FeatureInfo(name=name, degree=1, source_columns=[name])
            for name in column_names
        ]

        # 多项式特征
        for degree in range(2, self.max_degree + 1):
            for i, name in enumerate(column_names):
                power_feature = X[:, i : i + 1] ** degree
                features.append(power_feature)
                feature_name = f"{name}^{degree}"
                self.feature_names.append(feature_name)
                self._feature_info.append(
                    FeatureInfo(name=feature_name, degree=degree, source_columns=[name])
                )

        # 交互特征 (仅一阶交互)
        if self.include_interaction and n_features > 1:
            for i in range(n_features):
                for j in range(i + 1, n_features):
                    interaction = (X[:, i] * X[:, j]).reshape(-1, 1)
                    features.append(interaction)
                    feature_name = f"{column_names[i]}*{column_names[j]}"
                    self.feature_names.append(feature_name)
                    self._feature_info.append(
                        FeatureInfo(
                            name=feature_name,
                            degree=2,
                            source_columns=[column_names[i], column_names[j]],
                        )
                    )

        # 对数特征
        if self.include_log:
            for i, name in enumerate(column_names):
                # 避免log(0)
                log_feature = np.log1p(np.abs(X[:, i : i + 1]))
                features.append(log_feature)
                feature_name = f"log({name})"
                self.feature_names.append(feature_name)
                self._feature_info.append(
                    FeatureInfo(name=feature_name, degree=1, source_columns=[name])
                )

        return np.hstack(features)

    def select_features(
        self,
        X: np.ndarray,
        y: np.ndarray,
        n_features: int = 5,
        method: str = "correlation",
    ) -> tuple:
        """特征选择

        Args:
            X: 特征数组
            y: 目标数组
            n_features: 选择的特征数量
            method: 选择方法 ('correlation', 'variance')

        Returns:
            tuple: (选择的特征索引, 特征重要性)
        """
        if method == "correlation":
            correlations = np.abs([np.corrcoef(X[:, i], y)[0, 1] for i in range(X.shape[1])])
            correlations = np.nan_to_num(correlations, 0)
            indices = np.argsort(correlations)[::-1][:n_features]
            return indices, correlations[indices]

        elif method == "variance":
            variances = np.var(X, axis=0)
            indices = np.argsort(variances)[::-1][:n_features]
            return indices, variances[indices]

        else:
            raise ValueError(f"不支持的特征选择方法: {method}")

    def get_feature_names(self) -> List[str]:
        """获取特征名称列表"""
        return self.feature_names

    def get_feature_info(self) -> List[Dict[str, Any]]:
        """获取特征详细信息"""
        return [
            {"name": f.name, "degree": f.degree, "source_columns": f.source_columns}
            for f in self._feature_info
        ]

