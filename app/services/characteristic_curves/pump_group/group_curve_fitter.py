"""
泵组曲线拟合器

本模块负责对泵组运行数据进行曲线拟合：
- 多项式拟合（2-4阶）
- 交叉验证
- 评估指标计算
- 拟合质量验证

版本: v1.0
创建日期: 2025-12-09
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import PolynomialFeatures

from app.services.characteristic_curves.pump_group.models import (
    DirectFitResult,
    GroupOperatingPoint,
)
from app.services.characteristic_curves.shared.exceptions import CurveFittingError


class GroupCurveFitter:
    """泵组曲线拟合器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化拟合器

        Args:
            config: 配置字典（可选）
        """
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._config = config or self._load_default_config()

    def fit_polynomial(
        self,
        station_id: int,
        pump_combination: List[int],
        points: List[GroupOperatingPoint],
        curve_type: str = "qh",
        degree: Optional[int] = None,
        group_type: Optional[str] = None,
    ) -> DirectFitResult:
        """
        多项式拟合

        Args:
            station_id: 泵站ID
            pump_combination: 泵组合
            points: 工况点列表
            curve_type: 曲线类型
            degree: 多项式阶数（None表示自动选择）
            group_type: 泵组类型

        Returns:
            DirectFitResult: 拟合结果

        Raises:
            CurveFittingError: 拟合失败或质量不达标
        """
        if len(points) < self._config["min_data_points"]:
            raise CurveFittingError(
                f"数据点不足：实际{len(points)}个，要求至少{self._config['min_data_points']}个"
            )

        # 提取数据
        Q = np.array([p.Q_total for p in points])
        H = np.array([p.H_system for p in points])

        # 自动选择阶数（如果未指定）
        if degree is None:
            degree = self._select_best_degree(Q, H)

        # 多项式拟合
        poly_features = PolynomialFeatures(degree=degree, include_bias=True)
        Q_poly = poly_features.fit_transform(Q.reshape(-1, 1))

        # 使用Ridge回归（带正则化）
        model = Ridge(alpha=self._config["regularization_alpha"])
        model.fit(Q_poly, H)

        # 预测
        H_pred = model.predict(Q_poly)

        # 计算评估指标
        metrics = self._calculate_metrics(H, H_pred)

        # 验证拟合质量
        self._validate_fit_quality(
            metrics["r_squared"], self._config["min_r_squared"]
        )

        # 交叉验证
        cv_scores = cross_val_score(
            model, Q_poly, H, cv=self._config["cv_folds"], scoring="r2"
        )

        # 提取系数（从高阶到低阶）
        coefficients = model.coef_.tolist()
        coefficients.insert(0, model.intercept_)  # 添加截距

        # 构建预测函数
        def forward_func(Q_input: np.ndarray) -> np.ndarray:
            """正向预测函数 H = f(Q)"""
            Q_poly_input = poly_features.transform(Q_input.reshape(-1, 1))
            return model.predict(Q_poly_input)

        # 构建结果
        result = DirectFitResult(
            station_id=station_id,
            pump_combination=pump_combination,
            curve_type=curve_type,
            coefficients=coefficients,
            polynomial_degree=degree,
            r_squared=metrics["r_squared"],
            rmse=metrics["rmse"],
            mae=metrics["mae"],
            mape=metrics["mape"],
            cv_mean_r2=float(np.mean(cv_scores)),
            cv_std_r2=float(np.std(cv_scores)),
            cv_fold_scores=cv_scores.tolist(),
            data_points_used=len(points),
            valid_q_range=(float(Q.min()), float(Q.max())),
            valid_h_range=(float(H.min()), float(H.max())),
            fitted_at=datetime.now(),
            group_type=group_type,
            Q_data=Q,  # 保存原始数据用于绘图
            H_data=H,  # 保存原始数据用于绘图
            forward_func=forward_func,  # 保存预测函数用于绘图
        )

        self._logger.info(
            f"[曲线拟合] 拟合成功: degree={degree}, R²={metrics['r_squared']:.4f}, "
            f"RMSE={metrics['rmse']:.4f}, CV_R²={result.cv_mean_r2:.4f}±{result.cv_std_r2:.4f}"
        )

        return result

    def _select_best_degree(self, Q: np.ndarray, H: np.ndarray) -> int:
        """
        自动选择最佳多项式阶数（2-4阶）

        Args:
            Q: 流量数组
            H: 扬程数组

        Returns:
            int: 最佳阶数
        """
        best_degree = 2
        best_score = -np.inf

        for degree in range(2, 5):  # 2, 3, 4阶
            poly_features = PolynomialFeatures(degree=degree, include_bias=True)
            Q_poly = poly_features.fit_transform(Q.reshape(-1, 1))

            model = Ridge(alpha=self._config["regularization_alpha"])
            scores = cross_val_score(
                model, Q_poly, H, cv=self._config["cv_folds"], scoring="r2"
            )
            mean_score = np.mean(scores)

            if mean_score > best_score:
                best_score = mean_score
                best_degree = degree

        self._logger.info(
            f"[阶数选择] 最佳阶数: {best_degree} (CV_R²={best_score:.4f})"
        )

        return best_degree

    def _calculate_metrics(
        self, y_true: np.ndarray, y_pred: np.ndarray
    ) -> Dict[str, float]:
        """
        计算评估指标

        Args:
            y_true: 真实值
            y_pred: 预测值

        Returns:
            Dict: {'r_squared': float, 'rmse': float, 'mae': float, 'mape': float}
        """
        # R²
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        # RMSE
        rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))

        # MAE
        mae = np.mean(np.abs(y_true - y_pred))

        # MAPE
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100 if np.all(y_true != 0) else 0.0

        return {
            "r_squared": float(r_squared),
            "rmse": float(rmse),
            "mae": float(mae),
            "mape": float(mape),
        }

    def _validate_fit_quality(self, r_squared: float, threshold: float) -> None:
        """
        验证拟合质量

        Args:
            r_squared: R²值
            threshold: 阈值

        Raises:
            CurveFittingError: R²低于阈值
        """
        if r_squared < threshold:
            raise CurveFittingError(
                f"拟合质量不达标：R²={r_squared:.4f} < {threshold:.4f}"
            )

    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "min_data_points": 100,  # 最小数据点数
            "min_r_squared": 0.85,  # 最小R²阈值
            "regularization_alpha": 1.0,  # Ridge正则化系数
            "cv_folds": 5,  # 交叉验证折数
        }

