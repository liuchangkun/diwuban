"""
拟合方法基类 (app.services.characteristic_curves.methods.base_method)

本模块定义所有拟合方法的抽象基类，提供统一接口和通用功能。

设计模式：模板方法模式
依赖：numpy, pandas

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/03_核心模块/02_方法层.md
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from app.services.characteristic_curves.models import MethodResult, ValidationResult

# ==================== 配置常量 ====================
# 数据点数量要求（权威定义见02_架构设计/03_术语和规范.md）
MIN_DATA_POINTS: int = 50  # 拟合最小数据点数
MIN_EXTRACTION_POINTS: int = 100  # 数据提取建议点数
MIN_VALIDATION_POINTS: int = 50  # 验收标准最小点数

# 质量阈值
R2_EXCELLENT_THRESHOLD: float = 0.99  # 优秀质量阈值
R2_GOOD_THRESHOLD: float = 0.95  # 良好质量阈值
R2_FAIR_THRESHOLD: float = 0.90  # 合格质量阈值


class BaseMethod(ABC):
    """拟合方法抽象基类

    所有拟合方法必须继承此类并实现 fit() 和 predict() 抽象方法。
    提供通用的指标计算、数据验证和质量评估功能。

    Attributes:
        method_name: 方法显示名称（中文）
        method_id: 方法唯一标识
        default_params: 默认参数字典
    """

    def __init__(self, method_name: str, method_id: str) -> None:
        """初始化方法基类

        Args:
            method_name: 方法显示名称（中文）
            method_id: 方法唯一标识
        """
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.method_name = method_name
        self.method_id = method_id
        self.default_params: Dict[str, Any] = {}

    @abstractmethod
    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        constraints: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> MethodResult:
        """执行拟合（抽象方法，子类必须实现）

        Args:
            X: 自变量数组（流量Q）
            y: 因变量数组（扬程H/功率P/效率η）
            constraints: 物理约束参数
            **kwargs: 其他参数

        Returns:
            MethodResult: 拟合结果
        """
        pass

    @abstractmethod
    def predict(self, X: np.ndarray, params: Dict[str, float]) -> np.ndarray:
        """使用拟合参数进行预测（抽象方法，子类必须实现）

        Args:
            X: 自变量数组
            params: 拟合参数

        Returns:
            np.ndarray: 预测值数组
        """
        pass

    def _calculate_metrics(
        self, y_true: np.ndarray, y_pred: np.ndarray
    ) -> Dict[str, float]:
        """计算评估指标

        Args:
            y_true: 真实值数组
            y_pred: 预测值数组

        Returns:
            Dict: 包含 r_squared, rmse, mae, mape 的字典
        """
        # R²
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        # RMSE
        rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

        # MAE
        mae = float(np.mean(np.abs(y_true - y_pred)))

        # MAPE
        non_zero_mask = y_true != 0
        if np.any(non_zero_mask):
            mape = float(
                np.mean(
                    np.abs(
                        (y_true[non_zero_mask] - y_pred[non_zero_mask])
                        / y_true[non_zero_mask]
                    )
                )
            )
        else:
            mape = 0.0

        return {
            "r_squared": float(r_squared),
            "rmse": rmse,
            "mae": mae,
            "mape": mape,
        }

    def _validate_input(
        self, data: pd.DataFrame, params: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """验证输入数据

        Args:
            data: 输入数据
            params: 输入参数

        Returns:
            ValidationResult: 验证结果
        """
        errors: list[str] = []
        checks: list[Dict[str, Any]] = []

        # 检查数据非空
        if data is None or len(data) == 0:
            errors.append("输入数据为空")
            checks.append({"name": "数据非空", "passed": False})
        else:
            checks.append({"name": "数据非空", "passed": True})

        # 检查数据量（使用配置常量）
        if data is not None and len(data) < MIN_DATA_POINTS:
            errors.append(
                f"数据量不足：需要至少{MIN_DATA_POINTS}个点，当前{len(data)}个"
            )
            checks.append({"name": "数据量充足", "passed": False})
        elif data is not None:
            checks.append({"name": "数据量充足", "passed": True})

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            checks=checks,
            passed_checks=[c["name"] for c in checks if c["passed"]],
            failed_checks=[c["name"] for c in checks if not c["passed"]],
        )

    def _get_quality_grade(self, r_squared: float) -> str:
        """根据R²返回质量等级

        Args:
            r_squared: R²值

        Returns:
            str: 质量等级 ('excellent', 'good', 'fair', 'poor')
        """
        if r_squared >= R2_EXCELLENT_THRESHOLD:
            return "excellent"
        elif r_squared >= R2_GOOD_THRESHOLD:
            return "good"
        elif r_squared >= R2_FAIR_THRESHOLD:
            return "fair"
        else:
            return "poor"

    def _estimate_initial_params(
        self, X: np.ndarray, y: np.ndarray
    ) -> Dict[str, float]:
        """基于数据特征估计初始参数（子类可重写）

        此方法提供默认的初始参数估计逻辑，子类可根据具体
        拟合方法的特点重写此方法。

        Args:
            X: 自变量数组
            y: 因变量数组

        Returns:
            Dict[str, float]: 估计的初始参数
        """
        # 基本统计特征
        x_min, x_max = float(np.min(X)), float(np.max(X))
        y_min, y_max = float(np.min(y)), float(np.max(y))
        x_range = x_max - x_min if x_max > x_min else 1.0
        y_range = y_max - y_min if y_max > y_min else 1.0

        # 估计斜率和截距（线性近似）
        slope = -y_range / x_range if x_range > 0 else 0.0
        intercept = y_max

        return {
            "slope_estimate": slope,
            "intercept_estimate": intercept,
            "x_min": x_min,
            "x_max": x_max,
            "y_min": y_min,
            "y_max": y_max,
        }

