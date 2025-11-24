"""
曲线基类 (app.services.characteristic_curves.curves.base_curve)

所有曲线模块的抽象基类，定义统一的拟合流程。

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/04_曲线模块/00_曲线基类.md
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


class CurveType(str, Enum):
    """曲线类型枚举"""

    QH = "qh"  # 流量-扬程曲线
    QP = "qp"  # 流量-功率曲线
    QETA = "qeta"  # 流量-效率曲线
    HETA = "heta"  # 扬程-效率曲线
    PETA = "peta"  # 功率-效率曲线
    QNPSH = "qnpsh"  # 流量-汽蚀余量曲线


class MonotonicityType(str, Enum):
    """单调性类型"""

    INCREASING = "increasing"  # 单调递增
    DECREASING = "decreasing"  # 单调递减
    UNIMODAL = "unimodal"  # 单峰


@dataclass
class FitResult:
    """拟合结果

    Attributes:
        success: 是否成功
        curve_type: 曲线类型
        method_id: 使用的方法ID
        coefficients: 拟合系数
        formula: 拟合公式
        r_squared: R²值
        rmse: RMSE值
        quality_grade: 质量等级
        x_values: X轴值
        y_fitted: 拟合Y值
        constraints_satisfied: 约束是否满足
        metadata: 元数据
    """

    success: bool
    curve_type: str
    method_id: str
    coefficients: List[float] = field(default_factory=list)
    formula: str = ""
    r_squared: float = 0.0
    rmse: float = 0.0
    quality_grade: str = "poor"
    x_values: Optional[np.ndarray] = None
    y_fitted: Optional[np.ndarray] = None
    constraints_satisfied: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "curve_type": self.curve_type,
            "method_id": self.method_id,
            "coefficients": self.coefficients,
            "formula": self.formula,
            "r_squared": self.r_squared,
            "rmse": self.rmse,
            "quality_grade": self.quality_grade,
            "constraints_satisfied": self.constraints_satisfied,
            "metadata": self.metadata,
        }


class BaseCurve(ABC):
    """曲线基类 - 所有曲线模块的抽象基类

    使用模板方法模式定义统一的拟合流程。

    Attributes:
        curve_type: 曲线类型
        monotonicity: 单调性类型
        recommended_methods: 推荐的拟合方法列表
    """

    # 子类必须定义的属性
    curve_type: CurveType = None
    monotonicity: MonotonicityType = None
    recommended_methods: List[str] = []

    def __init__(self) -> None:
        """初始化曲线基类"""
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._init_submodules()

    @abstractmethod
    def _init_submodules(self) -> None:
        """初始化子模块（由子类实现）"""
        pass

    @abstractmethod
    def extract_data(
        self, device_id: int, start_time: datetime, end_time: datetime
    ) -> pd.DataFrame:
        """提取数据（由子类实现）"""
        pass

    @abstractmethod
    def preprocess(self, data: pd.DataFrame) -> pd.DataFrame:
        """预处理数据（由子类实现）"""
        pass

    @abstractmethod
    def calculate_constraints(
        self, data: pd.DataFrame, device_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """计算物理约束参数（由子类实现）"""
        pass

    def get_default_constraints(self) -> Dict[str, Any]:
        """获取默认约束配置"""
        return {
            "curve_type": self.curve_type.value if self.curve_type else None,
            "monotonicity": self.monotonicity.value if self.monotonicity else None,
        }

    def fit(
        self,
        x_values: np.ndarray,
        y_values: np.ndarray,
        method_id: Optional[str] = None,
        **kwargs: Any,
    ) -> FitResult:
        """执行拟合（模板方法）- 简化版本"""
        self._logger.info(f"开始拟合: curve_type={self.curve_type}")

        # 选择方法
        selected_method = method_id or (
            self.recommended_methods[0] if self.recommended_methods else "polynomial"
        )

        # 由子类实现具体拟合逻辑
        return self._do_fit(x_values, y_values, selected_method, **kwargs)

    @abstractmethod
    def _do_fit(
        self, x_values: np.ndarray, y_values: np.ndarray, method_id: str, **kwargs: Any
    ) -> FitResult:
        """执行具体拟合（由子类实现）"""
        pass

    def predict(self, x_values: np.ndarray, fit_result: FitResult) -> np.ndarray:
        """根据拟合结果预测Y值（由子类可覆盖）"""
        raise NotImplementedError("子类需实现predict方法")

    def validate(self, fit_result: FitResult, original_data: pd.DataFrame) -> bool:
        """验证拟合结果（由子类可覆盖）"""
        return fit_result.r_squared >= 0.9 and fit_result.constraints_satisfied

