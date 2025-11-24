"""
系统修正模型 (app.services.characteristic_curves.pump_group.system_correction_model)

本模块提供泵组曲线修正功能：
- 从历史数据学习修正系数
- 预测给定(N, Q_total)下的修正系数
- 应用修正系数到理论扬程

修正原理：
    H_actual = H_theoretical × α(N, Q_total)

    其中：
    - H_actual: 实际扬程
    - H_theoretical: 理论合成扬程
    - α: 修正系数（依赖台数N和流量Q_total）

模型类型：
    - linear: α = a₀ + a₁N + a₂Q
    - polynomial: α = a₀ + a₁N + a₂Q + a₃N² + a₄Q² + a₅NQ
    - xgboost: XGBoost回归

版本: v1.0
更新日期: 2025-12-09
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple
import logging

import numpy as np
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import Ridge

from app.services.characteristic_curves.shared.exceptions import (
    CorrectionModelTrainingError,
)


@dataclass
class CorrectionModelConfig:
    """修正模型配置"""

    model_type: Literal["linear", "polynomial", "xgboost"] = "polynomial"
    polynomial_degree: int = 2
    regularization_alpha: float = 1.0
    min_training_points: int = 100
    validation_ratio: float = 0.2


class SystemCorrectionModel:
    """
    系统修正系数模型

    职责：
    1. 从历史数据学习修正系数
    2. 预测给定(N, Q_total)下的修正系数
    3. 应用修正系数到理论扬程
    """

    # MIXED_HETEROGENEOUS场景的训练数据要求
    MIN_POINTS_PER_COMBINATION = 50  # 每种组合最少50条记录
    MIN_TOTAL_POINTS = 500  # 总数据量最少500条
    RECOMMENDED_POINTS = 1000  # 推荐数据量

    def __init__(self, config: Optional[CorrectionModelConfig] = None):
        self._config = config or CorrectionModelConfig()
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # 模型状态
        self._is_fitted = False
        self._model = None
        self._poly_features = None
        self._training_info: Dict[str, Any] = {}
        self._coefficients: Dict[str, Any] = {}
        self._valid_range: Dict[str, Tuple[float, float]] = {}
        self._extra_features: Optional[Dict[str, Any]] = None  # v2.5新增

    @property
    def is_fitted(self) -> bool:
        """模型是否已训练"""
        return self._is_fitted

    @property
    def training_info(self) -> Dict[str, Any]:
        """训练信息"""
        return self._training_info.copy()

    @property
    def valid_range(self) -> Dict[str, Tuple[float, float]]:
        """有效范围"""
        return self._valid_range.copy()

    def set_model_type(
        self, model_type: Literal["linear", "polynomial", "xgboost"]
    ) -> None:
        """
        动态设置模型类型（v2.5新增，解决问题#10）

        Args:
            model_type: 模型类型 ('linear' | 'polynomial' | 'xgboost')

        Note:
            允许在运行时切换模型类型，用于混合泵组场景需要使用XGBoost的情况。
            调用此方法会重置模型状态。
        """
        if model_type not in ("linear", "polynomial", "xgboost"):
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
        extra_features: Optional[Dict[str, Any]] = None,
    ) -> "SystemCorrectionModel":
        """
        训练修正模型（v2.0: 不使用默认值，直接抛异常；v2.5: 新增extra_features参数）

        Args:
            station_id: 泵站ID
            pump_ids: 泵ID列表
            training_data: 训练数据 [N, Q_total, H_theoretical, H_actual]
            extra_features: 扩展特征字典（v2.5新增，解决问题#11）
                用于MIXED_HETEROGENEOUS场景，传入功率权重、频率差异等特征

        Returns:
            self: 支持链式调用

        Raises:
            CorrectionModelTrainingError: 训练数据不足或训练失败时抛出

        Note:
            ✅ v2.0修复问题#12: 不使用默认α=1.0，直接抛异常
            ✅ v2.5修复问题#11: 添加extra_features参数支持
        """
        # 存储扩展特征用于后续分析
        self._extra_features = extra_features

        # ✅ v2.0: 无数据直接抛异常
        if training_data is None or len(training_data) == 0:
            error = CorrectionModelTrainingError(
                message="修正模型训练失败：无训练数据",
                station_id=station_id,
                pump_ids=pump_ids,
                reason="no_training_data",
                actual_points=0,
                min_points=self._config.min_training_points,
            )
            self._logger.error(error.to_log_format())
            raise error

        # ✅ v2.0: 数据不足直接抛异常（不使用警告+继续）
        if len(training_data) < self._config.min_training_points:
            error = CorrectionModelTrainingError(
                message="修正模型训练失败：数据不足",
                station_id=station_id,
                pump_ids=pump_ids,
                reason="insufficient_data",
                actual_points=len(training_data),
                min_points=self._config.min_training_points,
            )
            self._logger.error(error.to_log_format())
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

        if self._config.model_type == "linear":
            # 线性回归
            from sklearn.linear_model import LinearRegression

            self._model = LinearRegression()
            self._model.fit(X, alpha)
            self._coefficients = {
                "intercept": float(self._model.intercept_),
                "coef": self._model.coef_.tolist(),
            }

        elif self._config.model_type == "polynomial":
            self._poly_features = PolynomialFeatures(
                degree=self._config.polynomial_degree, include_bias=True
            )
            X_poly = self._poly_features.fit_transform(X)

            # 岭回归
            self._model = Ridge(alpha=self._config.regularization_alpha)
            self._model.fit(X_poly, alpha)

            self._coefficients = {
                "intercept": float(self._model.intercept_),
                "coef": self._model.coef_.tolist(),
            }

        elif self._config.model_type == "xgboost":
            # XGBoost回归
            try:
                import xgboost as xgb

                self._model = xgb.XGBRegressor(
                    n_estimators=100,
                    max_depth=5,
                    learning_rate=0.1,
                    random_state=42,
                )
                self._model.fit(X, alpha)
                self._coefficients = {"type": "xgboost", "n_estimators": 100}
            except ImportError:
                self._logger.warning(
                    "[修正模型] XGBoost未安装，回退到polynomial模型"
                )
                self._config.model_type = "polynomial"
                return self.fit(station_id, pump_ids, training_data, extra_features)

        # 记录训练信息
        self._valid_range = {
            "N_min": int(N.min()),
            "N_max": int(N.max()),
            "Q_min": float(Q.min()),
            "Q_max": float(Q.max()),
        }

        alpha_pred = self.predict(N, Q)
        r2 = 1 - np.sum((alpha - alpha_pred) ** 2) / np.sum(
            (alpha - alpha.mean()) ** 2
        )

        self._training_info = {
            "data_points": len(training_data),
            "train_r2": float(r2),
            "trained_at": str(np.datetime64("now")),
            "station_id": station_id,
            "pump_ids": pump_ids,
        }

        self._is_fitted = True
        self._logger.info(
            f"[修正模型] 训练完成，R²={r2:.4f}, "
            f"数据点={len(training_data)}, 模型类型={self._config.model_type}"
        )
        return self

    def predict(self, N: np.ndarray, Q: np.ndarray) -> np.ndarray:
        """
        预测修正系数

        Args:
            N: 运行台数数组
            Q: 总流量数组

        Returns:
            alpha: 修正系数数组
        """
        if not self._is_fitted:
            return np.ones_like(N, dtype=float)

        # 确保输入是numpy数组
        N = np.atleast_1d(np.asarray(N))
        Q = np.atleast_1d(np.asarray(Q))

        X = np.column_stack([N, Q])

        if self._config.model_type == "polynomial" and self._poly_features:
            X_poly = self._poly_features.transform(X)
            return self._model.predict(X_poly)

        elif self._config.model_type in ("linear", "xgboost") and self._model:
            return self._model.predict(X)

        # 默认返回1.0
        return np.ones_like(N, dtype=float)

    def apply_correction(
        self, H_theoretical: float, N: int, Q_total: float
    ) -> float:
        """
        应用修正系数

        Args:
            H_theoretical: 理论扬程
            N: 运行台数
            Q_total: 总流量

        Returns:
            H_actual: 修正后扬程
        """
        alpha = self.predict(np.array([N]), np.array([Q_total]))[0]
        H_corrected = H_theoretical * alpha

        self._logger.debug(
            f"[修正] H_theo={H_theoretical:.2f}m, N={N}, Q={Q_total:.1f}m³/h "
            f"→ α={alpha:.4f} → H_actual={H_corrected:.2f}m"
        )
        return H_corrected

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
                "validation_ratio": self._config.validation_ratio,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SystemCorrectionModel":
        """从字典恢复模型（用于从数据库加载）"""
        config = CorrectionModelConfig(
            model_type=data.get("config", {}).get("model_type", "polynomial"),
            polynomial_degree=data.get("config", {}).get("polynomial_degree", 2),
            regularization_alpha=data.get("config", {}).get(
                "regularization_alpha", 1.0
            ),
            min_training_points=data.get("config", {}).get("min_training_points", 100),
            validation_ratio=data.get("config", {}).get("validation_ratio", 0.2),
        )

        instance = cls(config)
        instance._is_fitted = data.get("is_fitted", False)
        instance._training_info = data.get("training_info", {})
        instance._coefficients = data.get("coefficients", {})
        instance._valid_range = data.get("valid_range", {})

        return instance

    def validate_training_data_coverage(
        self, pump_ids: List[int], training_data: np.ndarray
    ) -> Dict[str, Any]:
        """
        验证训练数据覆盖率（用于MIXED_HETEROGENEOUS场景）

        Args:
            pump_ids: 泵ID列表
            training_data: 训练数据数组

        Returns:
            Dict: {
                'is_valid': bool,
                'coverage_ratio': float,
                'missing_combinations': List[Set[int]],
                'low_count_combinations': List[Tuple[Set[int], int]]
            }
        """
        from itertools import combinations

        # 生成所有可能的组合
        all_combinations = []
        for r in range(1, len(pump_ids) + 1):
            all_combinations.extend(combinations(pump_ids, r))

        # 如果training_data中包含运行泵列表信息（假设第5列）
        # 这里简化处理：仅基于泵数量N进行覆盖检查
        if training_data.shape[1] > 4:
            # 有running_pumps信息
            # TODO: 实现详细的组合覆盖检查
            pass

        # 简化版本：仅检查不同N值的数据量
        N_values = training_data[:, 0].astype(int)
        n_counts = {}
        for n in range(1, len(pump_ids) + 1):
            n_counts[n] = np.sum(N_values == n)

        # 检查覆盖率
        covered = sum(
            1 for c in n_counts.values() if c >= self.MIN_POINTS_PER_COMBINATION
        )
        coverage_ratio = covered / len(pump_ids) if len(pump_ids) > 0 else 0.0

        missing = [n for n, cnt in n_counts.items() if cnt == 0]
        low_count = [
            (n, cnt)
            for n, cnt in n_counts.items()
            if 0 < cnt < self.MIN_POINTS_PER_COMBINATION
        ]

        is_valid = coverage_ratio >= 0.8 and len(missing) == 0

        self._logger.info(
            f"[覆盖检查] pump_ids={pump_ids}, "
            f"覆盖率={coverage_ratio:.1%}, "
            f"缺失={missing}, 不足={low_count}"
        )

        return {
            "is_valid": is_valid,
            "coverage_ratio": coverage_ratio,
            "missing_n_values": missing,
            "low_count_n_values": low_count,
            "n_counts": n_counts,
        }

    def fit_with_coverage_validation(
        self,
        station_id: int,
        pump_ids: List[int],
        training_data: np.ndarray,
        extra_features: Optional[Dict[str, Any]] = None,
    ) -> "SystemCorrectionModel":
        """
        带覆盖验证的训练方法（用于MIXED_HETEROGENEOUS场景）

        Args:
            station_id: 泵站ID
            pump_ids: 泵ID列表
            training_data: 训练数据
            extra_features: 扩展特征

        Returns:
            self: 支持链式调用

        Raises:
            CorrectionModelTrainingError: 训练数据覆盖不足时抛出
        """
        coverage = self.validate_training_data_coverage(pump_ids, training_data)

        if not coverage["is_valid"]:
            raise CorrectionModelTrainingError(
                message="训练数据覆盖不足",
                station_id=station_id,
                pump_ids=pump_ids,
                reason="insufficient_coverage",
                actual_points=len(training_data),
                min_points=self.MIN_TOTAL_POINTS,
                details={
                    "coverage_ratio": coverage["coverage_ratio"],
                    "missing_n_values": coverage["missing_n_values"],
                    "low_count_n_values": coverage["low_count_n_values"],
                },
            )

        return self.fit(station_id, pump_ids, training_data, extra_features)


def prepare_features_mixed_heterogeneous(
    pump_infos: List[Dict[str, Any]],
    frequencies: Dict[int, float],
    Q_total: float,
) -> Dict[str, float]:
    """
    为MIXED_HETEROGENEOUS场景准备XGBoost特征（v2.4新增）

    解决问题#6：扩展特征以捕捉功率差异对修正系数的影响

    Args:
        pump_infos: 泵信息列表 [{'pump_id', 'rated_power', 'control_type'}, ...]
        frequencies: 各泵运行频率 {pump_id: freq}
        Q_total: 总流量

    Returns:
        Dict[str, float]: 特征字典
    """
    powers = [p["rated_power"] for p in pump_infos]
    vfd_infos = [p for p in pump_infos if p.get("control_type") == "VFD"]
    ss_infos = [p for p in pump_infos if p.get("control_type") == "SS"]

    # 基础特征
    features: Dict[str, float] = {
        "n_pumps": float(len(pump_infos)),
        "Q_total": Q_total,
        "vfd_count": float(len(vfd_infos)),
        "ss_count": float(len(ss_infos)),
    }

    # ✅ 功率差异特征（问题#6核心）
    if powers:
        features.update(
            {
                "power_max": max(powers),
                "power_min": min(powers),
                "power_ratio": max(powers) / min(powers) if min(powers) > 0 else 1.0,
                "power_std": float(np.std(powers)) if len(powers) > 1 else 0.0,
                "power_range": max(powers) - min(powers),
            }
        )
    else:
        features.update(
            {
                "power_max": 0.0,
                "power_min": 0.0,
                "power_ratio": 1.0,
                "power_std": 0.0,
                "power_range": 0.0,
            }
        )

    # ✅ VFD频率特征
    if vfd_infos:
        vfd_freqs = [frequencies.get(p["pump_id"], 50.0) for p in vfd_infos]
        features.update(
            {
                "vfd_freq_mean": float(np.mean(vfd_freqs)),
                "vfd_freq_std": float(np.std(vfd_freqs)) if len(vfd_freqs) > 1 else 0.0,
                "vfd_freq_range": (
                    max(vfd_freqs) - min(vfd_freqs) if len(vfd_freqs) > 1 else 0.0
                ),
                "vfd_freq_min": min(vfd_freqs),
                "vfd_freq_max": max(vfd_freqs),
            }
        )
    else:
        features.update(
            {
                "vfd_freq_mean": 50.0,
                "vfd_freq_std": 0.0,
                "vfd_freq_range": 0.0,
                "vfd_freq_min": 50.0,
                "vfd_freq_max": 50.0,
            }
        )

    # ✅ VFD功率特征（问题#3相关）
    if len(vfd_infos) > 1:
        vfd_powers = [p["rated_power"] for p in vfd_infos]
        features.update(
            {
                "vfd_power_ratio": (
                    max(vfd_powers) / min(vfd_powers) if min(vfd_powers) > 0 else 1.0
                ),
                "vfd_power_std": float(np.std(vfd_powers)),
            }
        )
    else:
        features.update(
            {
                "vfd_power_ratio": 1.0,
                "vfd_power_std": 0.0,
            }
        )

    # ✅ 交互特征
    features["power_freq_interaction"] = features["power_ratio"] * features.get(
        "vfd_freq_range", 0.0
    )

    return features

