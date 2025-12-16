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

from app.services.characteristic_curves.core.data_structures import FitResult


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


# FitResult 已移至 app.services.characteristic_curves.models
# 请从该模块导入使用


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

    def __init__(
        self,
        # v3.0更新: 依赖注入参数（符合文档规范）
        storage: 'ResultStorage',
        cache: 'CacheManager',
        batch_processor: 'BatchProcessor',
        parameter_optimizer: 'ParameterOptimizer',
        historical_evaluator: 'HistoricalDataEvaluator',
    ) -> None:
        """初始化曲线基类

        v3.0 依赖注入重构说明:
        - 所有共用层组件为必需参数（符合文档要求）
        - 类型注解使用具体类型而非Any
        - 子类应在调用super().__init__()时传入这些组件

        文档依据: 04_曲线模块/00_曲线基类.md 行59-86

        Args:
            storage: 结果存储器实例（必需）
            cache: 缓存管理器实例（必需）
            batch_processor: 批处理器实例（必需）
            parameter_optimizer: 参数优化器实例（必需）
            historical_evaluator: 历史数据评估器实例（必需）

        Raises:
            TypeError: 必需参数未提供时抛出
        """
        # 必需参数检查
        if storage is None:
            raise TypeError("storage是必需参数，不能为None")
        if cache is None:
            raise TypeError("cache是必需参数，不能为None")
        if batch_processor is None:
            raise TypeError("batch_processor是必需参数，不能为None")
        if parameter_optimizer is None:
            raise TypeError("parameter_optimizer是必需参数，不能为None")
        if historical_evaluator is None:
            raise TypeError("historical_evaluator是必需参数，不能为None")
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}")

        # v3.0: 保存共用层组件（必需参数）
        self._storage = storage
        self._cache = cache
        self._batch_processor = batch_processor
        self._parameter_optimizer = parameter_optimizer
        self._historical_evaluator = historical_evaluator

        # 初始化子模块
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
        device_id: int,
        start_time: datetime,
        end_time: datetime,
        methods: Optional[List[str]] = None,
        device_params: Optional[Dict[str, Any]] = None
    ) -> FitResult:
        """执行拟合（模板方法）

        Args:
            device_id: 设备ID
            start_time: 开始时间
            end_time: 结束时间
            methods: 指定方法列表（可选）
            device_params: 设备参数（可选）

        Returns:
            FitResult: 拟合结果
        """
        self._logger.info(
            f"开始拟合: device_id={device_id}, curve_type={self.curve_type}",
            extra={"extra_data": {
                "设备ID": device_id,
                "曲线类型": self.curve_type.value if self.curve_type else None,
                "开始时间": str(start_time),
                "结束时间": str(end_time)
            }}
        )

        # 简化阶段1: 数据提取 (对应权威阶段3)
        raw_data = self.extract_data(device_id, start_time, end_time)

        # 简化阶段2: 数据预处理 (对应权威阶段4)
        clean_data = self.preprocess(raw_data)

        # 简化阶段3: 计算约束参数 (对应权威阶段6)
        constraints = self.calculate_constraints(
            clean_data, device_params or {})

        # 简化阶段4: 归一化 (对应权威阶段8)
        if not hasattr(self, '_normalizer') or self._normalizer is None:
            self._logger.warning("缺少归一化器，跳过归一化阶段")
            normalized_data = clean_data
            norm_params = {}
        else:
            normalized_data = self._normalizer.fit_transform(clean_data)
            norm_params = self._normalizer.get_params()

        # 简化阶段5: 方法选择 (对应权威阶段9)
        if methods:
            selected_methods = methods
        elif hasattr(self, '_method_selector') and self._method_selector is not None:
            selected_method = self._method_selector.select_method(
                device_id=device_id,
                data=normalized_data,
                available_columns=list(normalized_data.columns),
                constraints=constraints
            )
            selected_methods = [selected_method]
        else:
            # 使用推荐方法
            selected_methods = self.recommended_methods if self.recommended_methods else [
                'math_poly_3']

        self._logger.info(f"选中方法: {selected_methods}")

        # 简化阶段6: 拟合 (对应权威阶段10)
        if not hasattr(self, '_fitter') or self._fitter is None:
            self._logger.warning("缺少拟合器，使用_do_fit()回退")
            # 回退到旧逻辑
            x_values = normalized_data.iloc[:, 0].values
            y_values = normalized_data.iloc[:, 1].values
            fit_result = self._do_fit(x_values, y_values, selected_methods[0])
        else:
            fit_result = self._fitter.fit(
                data=normalized_data,
                method_id=selected_methods[0],
                constraints=constraints
            )

        # 简化阶段7: 验证 (对应权威阶段11)
        if hasattr(self, '_validator') and self._validator is not None:
            # 构建拟合后数据用于验证
            fitted_df = normalized_data.copy()
            fitted_df['H_pred'] = fit_result.y_fitted if hasattr(
                fit_result, 'y_fitted') else []

            validation_result = self._validator.validate(
                fitted_data=fitted_df,
                constraints=constraints,
                tolerance=0.05
            )
            self._logger.info(f"验证结果: {validation_result['valid']}")
        else:
            self._logger.warning("缺少验证器，跳过验证阶段")
            validation_result = {'valid': True}

        # 简化阶段8: 历史评估 (对应权威阶段12)
        if self._historical_evaluator is not None:
            evaluation = self._historical_evaluator.evaluate(
                device_id=device_id,
                curve_type=self.curve_type.value if self.curve_type else None,
                current_result=fit_result
            )
            self._logger.info(f"历史评估完成")
        else:
            self._logger.info("未配置历史评估器，跳过阶段8")
            evaluation = {}

        # 简化阶段9: 存储 (对应权威阶段13)
        if self._storage is not None:
            version = self._storage.save(
                device_id=device_id,
                curve_type=self.curve_type.value if self.curve_type else None,
                fit_result=fit_result,
                validation_result=validation_result,
                evaluation=evaluation
            )
            self._logger.info(f"存储完成: version={version}")
        else:
            self._logger.warning("未配置存储器，跳过阶段9")

        return fit_result

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
