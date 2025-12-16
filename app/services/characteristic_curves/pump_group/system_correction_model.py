"""系统修正模型 (app.services.characteristic_curves.pump_group.system_correction_model)

从历史数据学习修正系数，应用于理论曲线修正。

核心功能：
- 从历史数据学习修正系数 α = H_actual / H_theoretical
- 支持多种模型类型（linear, polynomial, xgboost）
- 应用修正系数到理论扬程

修正公式：H_actual = H_theoretical × α(N, Q_total)

版本: v1.0
创建日期: 2025-12-14
参考文档: 07_泵组处理层.md 第4节
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Tuple

import numpy as np

from app.services.characteristic_curves.shared.exceptions import (
    CorrectionModelTrainingError,
)


logger = logging.getLogger(__name__)


@dataclass
class CorrectionModelConfig:
    """修正模型配置"""
    model_type: Literal['linear', 'polynomial', 'xgboost'] = 'polynomial'
    polynomial_degree: int = 2
    regularization_alpha: float = 1.0
    min_training_points: int = 100
    validation_ratio: float = 0.2


class SystemCorrectionModel:
    """系统修正系数模型

    职责：
    1. 从历史数据学习修正系数
    2. 预测给定(N, Q_total)下的修正系数
    3. 应用修正系数到理论扬程

    物理常数：
        RHO = 1000  # 水密度 kg/m³
        G = 9.81    # 重力加速度 m/s²
    """

    def __init__(self, config: Optional[CorrectionModelConfig] = None):
        """初始化修正模型

        Args:
            config: 模型配置，默认使用polynomial模型
        """
        self._config = config or CorrectionModelConfig()
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}")

        # 模型状态
        self._is_fitted = False
        self._model = None
        self._poly_features = None
        self._training_info: Dict[str, Any] = {}
        self._coefficients: Dict[str, Any] = {}
        self._valid_range: Dict[str, Tuple[float, float]] = {}
        self._extra_features: Optional[Dict[str, Any]] = None

        self._logger.info(
            f"[修正模型] 初始化完成，模型类型={self._config.model_type}"
        )

    def set_model_type(
        self,
        model_type: Literal['linear', 'polynomial', 'xgboost']
    ) -> None:
        """动态设置模型类型

        Args:
            model_type: 模型类型 ('linear' | 'polynomial' | 'xgboost')

        Note:
            允许在运行时切换模型类型，用于混合泵组场景需要使用XGBoost的情况。
            调用此方法会重置模型状态。
        """
        if model_type not in ('linear', 'polynomial', 'xgboost'):
            raise ValueError(f"不支持的模型类型: {model_type}")

        self._config.model_type = model_type
        self._is_fitted = False
        self._model = None
        self._poly_features = None
        self._logger.info(f"[修正模型] 模型类型切换为: {model_type}")

    def fit(
        self,
        station_id: int,
        pump_ids: List[int],
        training_data: Optional[np.ndarray] = None,
        extra_features: Optional[Dict[str, Any]] = None
    ) -> 'SystemCorrectionModel':
        """训练修正模型

        Args:
            station_id: 泵站ID
            pump_ids: 泵ID列表
            training_data: 训练数据 [N, Q_total, H_theoretical, H_actual]
            extra_features: 扩展特征字典（用于MIXED_HETEROGENEOUS场景）

        Returns:
            self: 支持链式调用

        Raises:
            CorrectionModelTrainingError: 训练数据不足或训练失败时抛出
        """
        # 存储扩展特征用于后续分析
        self._extra_features = extra_features

        # 无数据直接抛异常
        if training_data is None or len(training_data) == 0:
            error = CorrectionModelTrainingError(
                message=f"修正模型训练失败：无训练数据",
                station_id=station_id,
                pump_ids=pump_ids,
                reason="no_training_data",
                actual_points=0,
                min_points=self._config.min_training_points
            )
            self._logger.error(f"[修正模型] {error.message}")
            raise error

        # 数据不足直接抛异常
        if len(training_data) < self._config.min_training_points:
            error = CorrectionModelTrainingError(
                message=f"修正模型训练失败：数据不足",
                station_id=station_id,
                pump_ids=pump_ids,
                reason="insufficient_data",
                actual_points=len(training_data),
                min_points=self._config.min_training_points
            )
            self._logger.error(f"[修正模型] {error.message}")
            raise error

        # 提取特征和目标
        N = training_data[:, 0]
        Q = training_data[:, 1]
        H_theo = training_data[:, 2]
        H_actual = training_data[:, 3]

        # 计算修正系数 α = H_actual / H_theoretical
        alpha = H_actual / np.maximum(H_theo, 1e-6)

        # 构建特征矩阵
        X = np.column_stack([N, Q])

        if self._config.model_type == 'polynomial':
            self._fit_polynomial(X, alpha)
        elif self._config.model_type == 'linear':
            self._fit_linear(X, alpha)
        elif self._config.model_type == 'xgboost':
            self._fit_xgboost(X, alpha, extra_features)

        # 记录有效范围
        self._valid_range = {
            "N_min": int(N.min()),
            "N_max": int(N.max()),
            "Q_min": float(Q.min()),
            "Q_max": float(Q.max())
        }

        # 计算训练集R²
        alpha_pred = self.predict(N, Q)
        ss_res = np.sum((alpha - alpha_pred) ** 2)
        ss_tot = np.sum((alpha - alpha.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

        self._training_info = {
            "station_id": station_id,
            "pump_ids": pump_ids,
            "data_points": len(training_data),
            "train_r2": float(r2),
            "trained_at": datetime.now().isoformat(),
            "model_type": self._config.model_type
        }

        self._is_fitted = True
        self._logger.info(
            f"[修正模型] 训练完成，R²={r2:.4f}，数据点={len(training_data)}"
        )
        return self

    def _fit_polynomial(self, X: np.ndarray, y: np.ndarray) -> None:
        """使用多项式模型拟合"""
        from sklearn.linear_model import Ridge
        from sklearn.preprocessing import PolynomialFeatures

        self._poly_features = PolynomialFeatures(
            degree=self._config.polynomial_degree,
            include_bias=True
        )
        X_poly = self._poly_features.fit_transform(X)

        # 岭回归
        self._model = Ridge(alpha=self._config.regularization_alpha)
        self._model.fit(X_poly, y)

        self._coefficients = {
            "intercept": float(self._model.intercept_),
            "coef": self._model.coef_.tolist(),
            "degree": self._config.polynomial_degree
        }

    def _fit_linear(self, X: np.ndarray, y: np.ndarray) -> None:
        """使用线性模型拟合"""
        from sklearn.linear_model import Ridge

        self._model = Ridge(alpha=self._config.regularization_alpha)
        self._model.fit(X, y)

        self._coefficients = {
            "intercept": float(self._model.intercept_),
            "coef": self._model.coef_.tolist()
        }

    def _fit_xgboost(
        self,
        X: np.ndarray,
        y: np.ndarray,
        extra_features: Optional[Dict[str, Any]] = None
    ) -> None:
        """使用XGBoost模型拟合"""
        try:
            from xgboost import XGBRegressor
        except ImportError:
            self._logger.warning(
                "[修正模型] XGBoost未安装，回退到polynomial模型"
            )
            self._fit_polynomial(X, y)
            return

        # XGBoost配置
        xgb_config = {
            'n_estimators': 100,
            'max_depth': 5,
            'learning_rate': 0.1,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'min_child_weight': 3,
            'random_state': 42,
            'verbosity': 0
        }

        # MIXED_HETEROGENEOUS场景使用更复杂配置
        if extra_features and extra_features.get('power_ratio', 1.0) > 1.1:
            xgb_config.update({
                'n_estimators': 150,
                'max_depth': 6,
            })

        self._model = XGBRegressor(**xgb_config)
        self._model.fit(X, y)

        self._coefficients = {
            "model_type": "xgboost",
            "n_estimators": xgb_config['n_estimators'],
            "max_depth": xgb_config['max_depth']
        }

    def predict(self, N: np.ndarray, Q: np.ndarray) -> np.ndarray:
        """预测修正系数

        Args:
            N: 运行台数数组
            Q: 总流量数组

        Returns:
            alpha: 修正系数数组
        """
        if not self._is_fitted:
            return np.ones_like(N, dtype=float)

        # 确保输入是数组
        N = np.atleast_1d(N)
        Q = np.atleast_1d(Q)
        X = np.column_stack([N, Q])

        if self._config.model_type == 'polynomial' and self._poly_features:
            X_poly = self._poly_features.transform(X)
            return self._model.predict(X_poly)
        elif self._model is not None:
            return self._model.predict(X)

        # 默认返回1.0
        return np.ones_like(N, dtype=float)

    def apply_correction(
        self,
        H_theoretical: float,
        N: int,
        Q_total: float
    ) -> float:
        """应用修正系数

        Args:
            H_theoretical: 理论扬程
            N: 运行台数
            Q_total: 总流量

        Returns:
            H_actual: 修正后扬程
        """
        alpha = self.predict(np.array([N]), np.array([Q_total]))[0]
        return H_theoretical * alpha

    def get_correction_coefficient(self, N: int, Q_total: float) -> float:
        """获取修正系数

        Args:
            N: 运行台数
            Q_total: 总流量

        Returns:
            float: 修正系数 α
        """
        return self.predict(np.array([N]), np.array([Q_total]))[0]

    @property
    def is_fitted(self) -> bool:
        """模型是否已训练"""
        return self._is_fitted

    @property
    def training_info(self) -> Dict[str, Any]:
        """获取训练信息"""
        return self._training_info.copy()

    @property
    def valid_range(self) -> Dict[str, Any]:
        """获取有效范围"""
        return self._valid_range.copy()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于数据库存储）"""
        return {
            "model_type": self._config.model_type,
            "is_fitted": self._is_fitted,
            "training_info": self._training_info,
            "coefficients": self._coefficients,
            "valid_range": self._valid_range,
            "config": {
                "polynomial_degree": self._config.polynomial_degree,
                "regularization_alpha": self._config.regularization_alpha,
                "min_training_points": self._config.min_training_points,
                "validation_ratio": self._config.validation_ratio
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemCorrectionModel':
        """从字典恢复模型

        Args:
            data: 模型字典

        Returns:
            SystemCorrectionModel: 恢复的模型实例
        """
        config_data = data.get('config', {})
        config = CorrectionModelConfig(
            model_type=data.get('model_type', 'polynomial'),
            polynomial_degree=config_data.get('polynomial_degree', 2),
            regularization_alpha=config_data.get('regularization_alpha', 1.0),
            min_training_points=config_data.get('min_training_points', 100),
            validation_ratio=config_data.get('validation_ratio', 0.2)
        )

        model = cls(config)
        model._is_fitted = data.get('is_fitted', False)
        model._training_info = data.get('training_info', {})
        model._coefficients = data.get('coefficients', {})
        model._valid_range = data.get('valid_range', {})

        return model

    def __repr__(self) -> str:
        status = "trained" if self._is_fitted else "untrained"
        return (
            f"SystemCorrectionModel("
            f"type={self._config.model_type}, "
            f"status={status})"
        )
