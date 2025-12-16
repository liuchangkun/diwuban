"""
泵组方法适配器 (app.services.characteristic_curves.pump_group.group_method_adapter)

将泵组工况点适配到BaseMethod的标准输入格式，实现泵组与单泵方法的无缝对接。

设计模式：适配器模式
核心职责：
- 将GroupOperatingPoint转换为X-y数组
- 调用MethodRegistry获取方法实例
- 将MethodResult转换为DirectFitResult

版本: v1.0
创建日期: 2025-12-13
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

from app.services.characteristic_curves.methods.method_registry import MethodRegistry
from app.services.characteristic_curves.methods.base_method import BaseMethod
from app.services.characteristic_curves.core.data_structures import (
    MethodResult,
    GroupOperatingPoint,
    DirectFitResult,
)


logger = logging.getLogger(__name__)


class GroupMethodAdapter:
    """泵组方法适配器

    将泵组工况点转换为标准的X-y格式，调用单泵方法拟合，
    并将结果转换为泵组DirectFitResult。

    设计模式：适配器模式
    复用对象：MethodRegistry（单泵的方法注册表）
    """

    def __init__(self, method_registry: Optional[MethodRegistry] = None):
        """初始化

        Args:
            method_registry: 方法注册表（默认使用单例）
        """
        self._registry = method_registry or MethodRegistry()
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}")

    def fit_with_method(
        self,
        station_id: int,
        pump_combination: List[int],
        points: List[GroupOperatingPoint],
        curve_type: str = "qh",
        method_id: str = "math_poly_2",
        **kwargs: Any
    ) -> DirectFitResult:
        """使用指定方法拟合泵组曲线

        Args:
            station_id: 泵站ID
            pump_combination: 泵组合
            points: 泵组工况点列表
            curve_type: 曲线类型（qh/qp/qeta）
            method_id: 方法ID（从MethodRegistry获取）
                支持的方法ID:
                - math_poly_2: 2阶多项式
                - math_poly_3: 3阶多项式
                - ml_gradient_boost: 梯度提升树
                - ml_gaussian_process: 高斯过程
                - physics_pump_char: 泵特性方程
            **kwargs: 传递给拟合方法的额外参数

        Returns:
            DirectFitResult: 泵组拟合结果

        Raises:
            ValueError: 方法不存在或数据不足
        """
        # 步骤1: 数据验证
        if len(points) < 50:
            raise ValueError(f"数据点不足: {len(points)} < 50")

        # 步骤2: 提取Q-H数组
        Q_total = np.array([p.Q_total for p in points])
        H_system = np.array([p.H_system for p in points])

        # 步骤3: 从注册表获取方法实例
        try:
            method = self._registry.get_method(
                curve_type=curve_type,
                method_id=method_id
            )
        except Exception as e:
            self._logger.error(
                f"[泵组拟合] 获取方法失败: {method_id}",
                extra={"extra_data": {
                    "curve_type": curve_type,
                    "method_id": method_id,
                    "error": str(e)
                }}
            )
            raise

        self._logger.info(
            f"[泵组拟合] 使用方法: {method.method_name}",
            extra={"extra_data": {
                "station_id": station_id,
                "pump_combination": pump_combination,
                "method_id": method_id,
                "data_points": len(points)
            }}
        )

        # 步骤4: 执行拟合
        try:
            method_result = method.fit(X=Q_total, y=H_system, **kwargs)
        except Exception as e:
            self._logger.error(
                f"[泵组拟合] 拟合失败: {method.method_name}",
                extra={"extra_data": {
                    "method_id": method_id,
                    "error": str(e)
                }},
                exc_info=True
            )
            raise

        # 步骤5: 转换为DirectFitResult
        direct_result = self._convert_to_direct_result(
            station_id=station_id,
            pump_combination=pump_combination,
            points=points,
            curve_type=curve_type,
            method=method,
            method_result=method_result
        )

        self._logger.info(
            f"[泵组拟合] 拟合成功: R²={direct_result.r_squared:.4f}",
            extra={"extra_data": {
                "method_id": method_id,
                "r_squared": direct_result.r_squared,
                "rmse": direct_result.rmse
            }}
        )

        return direct_result

    def fit_auto(
        self,
        station_id: int,
        pump_combination: List[int],
        points: List[GroupOperatingPoint],
        curve_type: str = "qh",
        **kwargs: Any
    ) -> DirectFitResult:
        """自动选择最优方法并拟合

        使用MethodRegistry的select_best_method自动选择

        Args:
            station_id: 泵站ID
            pump_combination: 泵组合
            points: 泵组工况点列表
            curve_type: 曲线类型
            **kwargs: 额外参数

        Returns:
            DirectFitResult: 拟合结果
        """
        # 步骤1: 提取数据构建DataFrame
        Q_total = np.array([p.Q_total for p in points])
        H_system = np.array([p.H_system for p in points])

        import pandas as pd
        data_df = pd.DataFrame({'Q': Q_total, 'H': H_system})

        # 步骤2: 使用MethodRegistry自动选择
        try:
            best_method_id = self._registry.select_best_method(
                device_id=station_id,  # 使用station_id代替device_id
                curve_type=curve_type,
                data=data_df,
                available_columns=['Q', 'H']
            )
        except Exception as e:
            self._logger.warning(
                f"[泵组拟合] 自动选择方法失败，使用默认方法: {e}",
                extra={"extra_data": {"error": str(e)}}
            )
            best_method_id = "math_poly_2"  # 回退到默认方法

        self._logger.info(
            f"[泵组拟合] 自动选择方法: {best_method_id}",
            extra={"extra_data": {
                "station_id": station_id,
                "data_points": len(points),
                "selected_method": best_method_id
            }}
        )

        # 步骤3: 使用选中的方法拟合
        return self.fit_with_method(
            station_id=station_id,
            pump_combination=pump_combination,
            points=points,
            curve_type=curve_type,
            method_id=best_method_id,
            **kwargs
        )

    def _convert_to_direct_result(
        self,
        station_id: int,
        pump_combination: List[int],
        points: List[GroupOperatingPoint],
        curve_type: str,
        method: BaseMethod,
        method_result: MethodResult
    ) -> DirectFitResult:
        """将MethodResult转换为DirectFitResult

        Args:
            station_id: 泵站ID
            pump_combination: 泵组合
            points: 原始工况点
            curve_type: 曲线类型
            method: 方法实例
            method_result: 方法拟合结果

        Returns:
            DirectFitResult: 转换后的泵组结果
        """
        Q_total = np.array([p.Q_total for p in points])
        H_system = np.array([p.H_system for p in points])

        # 提取多项式阶数（如果有）
        polynomial_degree = method_result.metadata.get('degree')

        # 转换系数为列表
        coefficients = list(method_result.coefficients.values())

        return DirectFitResult(
            station_id=station_id,
            n_pumps=len(pump_combination),
            pump_combination_key=",".join(map(str, sorted(pump_combination))),
            curve_type=curve_type,
            fit_method="direct_fit",

            # 从MethodResult转换
            coefficients=coefficients,
            polynomial_degree=polynomial_degree,
            r_squared=method_result.r_squared,
            rmse=method_result.rmse,
            mae=method_result.mae,
            mape=method_result.mape,

            # 数据信息
            data_points_used=len(points),
            valid_q_range=(float(Q_total.min()), float(Q_total.max())),
            valid_h_range=(float(H_system.min()), float(H_system.max())),

            # 元数据
            fitted_at=datetime.now(),
            method_id=method.method_id,
            method_name=method.method_name,

            # 预测函数
            _predict_func=method_result.predict_func
        )
