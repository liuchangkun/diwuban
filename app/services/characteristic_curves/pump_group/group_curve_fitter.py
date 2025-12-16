"""
泵组曲线拟合器 (app.services.characteristic_curves.pump_group.group_curve_fitter)

支持多种拟合方法的泵组曲线拟合器，完全复用单泵的MethodRegistry架构。

核心功能：
- 按泵组合分组拟合（fit_by_combination）
- 拟合单个泵组合（fit_single_combination / fit_with_method）
- 自动选择方法拟合（fit_auto）
- 多方法对比拟合（fit_multi_methods）
- 交叉验证（cross_validate）
- 向后兼容原有多项式接口（fit_polynomial）

版本: v2.1
创建日期: 2025-12-13
更新日期: 2025-12-14
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.services.characteristic_curves.methods.method_registry import MethodRegistry
from app.services.characteristic_curves.core.data_structures import (
    GroupOperatingPoint,
    DirectFitResult
)
from .group_method_adapter import GroupMethodAdapter
from .group_method_selector import GroupMethodSelector


logger = logging.getLogger(__name__)


class GroupCurveFitter:
    """泵组曲线拟合器（扩展版）

    支持多种拟合方法：
    - 传统多项式（向后兼容）
    - MethodRegistry注册的所有方法
    - 自动方法选择

    设计理念：完全复用单泵的MethodRegistry+BaseMethod架构
    """

    def __init__(self):
        """初始化"""
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}")

        # 核心组件
        self._registry = MethodRegistry()
        self._adapter = GroupMethodAdapter(self._registry)
        self._selector = GroupMethodSelector()

        self._logger.info("[泵组拟合器] 初始化完成")

    # ==================== 新增接口（推荐使用）====================

    def fit_with_method(
        self,
        station_id: int,
        pump_combination: List[int],
        points: List[GroupOperatingPoint],
        curve_type: str = "qh",
        method_id: str = "math_poly_2",
        **kwargs: Any
    ) -> DirectFitResult:
        """使用指定方法拟合（新增接口）

        Args:
            station_id: 泵站ID
            pump_combination: 泵组合（如[1, 2, 3]）
            points: 泵组工况点列表
            curve_type: 曲线类型（qh/qp/qeta）
            method_id: 方法ID，支持所有MethodRegistry中已注册的方法：
                数学方法:
                  - math_poly_2: 2阶多项式
                  - math_poly_3: 3阶多项式
                  - math_spline_cubic: 三次样条
                机器学习:
                  - ml_gradient_boost: 梯度提升树（推荐大数据集>500点）
                  - ml_gaussian_process: 高斯过程回归
                物理模型:
                  - physics_pump_char: 泵特性方程
            **kwargs: 传递给拟合方法的额外参数

        Returns:
            DirectFitResult: 拟合结果

        示例:
            >>> fitter = GroupCurveFitter()
            >>> result = fitter.fit_with_method(
            ...     station_id=1,
            ...     pump_combination=[1, 2],
            ...     points=operating_points,
            ...     method_id="ml_gradient_boost"
            ... )
            >>> print(f"R²={result.r_squared:.4f}")
        """
        return self._adapter.fit_with_method(
            station_id=station_id,
            pump_combination=pump_combination,
            points=points,
            curve_type=curve_type,
            method_id=method_id,
            **kwargs
        )

    def fit_auto(
        self,
        station_id: int,
        pump_combination: List[int],
        points: List[GroupOperatingPoint],
        curve_type: str = "qh",
        **kwargs: Any
    ) -> DirectFitResult:
        """自动选择最优方法拟合（新增接口）

        根据数据特征自动选择：
        - 数据量 > 500: 优先机器学习方法（ml_gradient_boost）
        - 数据量 100-500: 优先多项式方法（math_poly_2/3）
        - 数据量 < 100: 使用简单多项式（math_poly_2）

        Args:
            station_id: 泵站ID
            pump_combination: 泵组合
            points: 泵组工况点列表
            curve_type: 曲线类型
            **kwargs: 额外参数

        Returns:
            DirectFitResult: 拟合结果（包含选中的method_id）

        示例:
            >>> result = fitter.fit_auto(
            ...     station_id=1,
            ...     pump_combination=[1, 2],
            ...     points=operating_points
            ... )
            >>> print(f"自动选中: {result.method_name}")
        """
        # 使用GroupMethodSelector选择方法
        best_method_id = self._selector.select_best(
            curve_type=curve_type,
            data_points=len(points)
        )

        self._logger.info(
            f"[泵组拟合] 自动选择方法: {best_method_id}",
            extra={"extra_data": {
                "station_id": station_id,
                "data_points": len(points),
                "selected_method": best_method_id
            }}
        )

        return self.fit_with_method(
            station_id=station_id,
            pump_combination=pump_combination,
            points=points,
            curve_type=curve_type,
            method_id=best_method_id,
            **kwargs
        )

    def fit_multi_methods(
        self,
        station_id: int,
        pump_combination: List[int],
        points: List[GroupOperatingPoint],
        curve_type: str = "qh",
        method_ids: Optional[List[str]] = None
    ) -> Dict[str, DirectFitResult]:
        """使用多种方法拟合并对比（新增接口）

        Args:
            station_id: 泵站ID
            pump_combination: 泵组合
            points: 泵组工况点列表
            curve_type: 曲线类型
            method_ids: 方法ID列表，None则使用默认候选集

        Returns:
            Dict[method_id, DirectFitResult]: 各方法拟合结果

        示例:
            >>> results = fitter.fit_multi_methods(
            ...     station_id=1,
            ...     pump_combination=[1, 2],
            ...     points=operating_points,
            ...     method_ids=["math_poly_2", "ml_gradient_boost"]
            ... )
            >>> best = max(results.items(), key=lambda x: x[1].r_squared)
            >>> print(f"最优方法: {best[0]}, R²={best[1].r_squared:.4f}")
        """
        if method_ids is None:
            # 默认候选：使用GroupMethodSelector获取推荐方法
            method_ids = self._selector.select(
                curve_type=curve_type,
                data_points=len(points)
            )

        results = {}
        for method_id in method_ids:
            try:
                result = self.fit_with_method(
                    station_id=station_id,
                    pump_combination=pump_combination,
                    points=points,
                    curve_type=curve_type,
                    method_id=method_id
                )
                results[method_id] = result

                self._logger.info(
                    f"[泵组拟合] {method_id}: R²={result.r_squared:.4f}",
                    extra={"extra_data": {
                        "method_id": method_id,
                        "r_squared": result.r_squared,
                        "rmse": result.rmse
                    }}
                )
            except Exception as e:
                self._logger.warning(
                    f"[泵组拟合] {method_id} 失败: {e}",
                    extra={"extra_data": {
                        "method_id": method_id,
                        "error": str(e)
                    }}
                )

        return results

    # ==================== 文档定义接口（08文档）====================

    def fit_by_combination(
        self,
        station_id: int,
        points_by_combination: Dict[str, List[GroupOperatingPoint]],
        curve_type: str = "qh",
        polynomial_degree: int = 2
    ) -> Dict[str, DirectFitResult]:
        """按泵组合分组拟合（08文档定义接口）

        为每个泵组合独立拟合曲线。

        Args:
            station_id: 泵站ID
            points_by_combination: 按泵组合分组的工况点
                格式: {"1,2": [point1, point2, ...], "1,2,3": [...]}
            curve_type: 曲线类型（qh/qp/qeta）
            polynomial_degree: 多项式阶数

        Returns:
            Dict[combination_key, DirectFitResult]: 各泵组合的拟合结果

        示例:
            >>> extractor = GroupDataExtractor()
            >>> points = extractor.extract_group_operating_points(station_id=1, ...)
            >>> grouped = extractor.group_by_pump_combination(points)
            >>> results = fitter.fit_by_combination(
            ...     station_id=1,
            ...     points_by_combination=grouped,
            ...     curve_type="qh"
            ... )
            >>> for key, result in results.items():
            ...     print(f"{key}: R²={result.r_squared:.4f}")
        """
        results: Dict[str, DirectFitResult] = {}

        for combination_key, points in points_by_combination.items():
            if len(points) < 10:
                self._logger.warning(
                    f"[泵组拟合] 组合 {combination_key} 数据点不足({len(points)}<10)，跳过"
                )
                continue

            try:
                result = self.fit_single_combination(
                    station_id=station_id,
                    combination_key=combination_key,
                    points=points,
                    curve_type=curve_type,
                    polynomial_degree=polynomial_degree
                )
                results[combination_key] = result

                self._logger.info(
                    f"[泵组拟合] 组合 {combination_key}: "
                    f"R²={result.r_squared:.4f}, 数据点={result.data_points_used}"
                )
            except Exception as e:
                self._logger.error(
                    f"[泵组拟合] 组合 {combination_key} 拟合失败: {e}"
                )

        self._logger.info(
            f"[泵组拟合] 完成 {len(results)}/{len(points_by_combination)} 个组合"
        )

        return results

    def fit_single_combination(
        self,
        station_id: int,
        combination_key: str,
        points: List[GroupOperatingPoint],
        curve_type: str = "qh",
        polynomial_degree: int = 2
    ) -> DirectFitResult:
        """拟合单个泵组合（08文档定义接口）

        Args:
            station_id: 泵站ID
            combination_key: 泵组合标识（如"1,2,3"）
            points: 泵组工况点列表
            curve_type: 曲线类型
            polynomial_degree: 多项式阶数

        Returns:
            DirectFitResult: 拟合结果
        """
        # 解析泵组合
        pump_combination = [int(x) for x in combination_key.split(",")]

        # 根据阶数选择方法
        method_id = f"math_poly_{polynomial_degree}"
        if polynomial_degree > 3:
            method_id = "math_poly_3"  # 回退到3阶

        return self.fit_with_method(
            station_id=station_id,
            pump_combination=pump_combination,
            points=points,
            curve_type=curve_type,
            method_id=method_id
        )

    def cross_validate(
        self,
        points: List[GroupOperatingPoint],
        n_folds: int = 5,
        curve_type: str = "qh",
        method_id: str = "math_poly_2"
    ) -> Dict[str, float]:
        """交叉验证（08文档定义接口）

        使用K折交叉验证评估拟合方法的泛化能力。

        Args:
            points: 泵组工况点列表
            n_folds: 折数（默认5折）
            curve_type: 曲线类型
            method_id: 拟合方法ID

        Returns:
            Dict[str, float]: 交叉验证结果
                - r2_mean: 平均R²
                - r2_std: R²标准差
                - rmse_mean: 平均RMSE
                - rmse_std: RMSE标准差
                - n_folds: 折数

        示例:
            >>> cv_results = fitter.cross_validate(
            ...     points=operating_points,
            ...     n_folds=5,
            ...     method_id="math_poly_2"
            ... )
            >>> print(f"CV R²: {cv_results['r2_mean']:.4f} ± {cv_results['r2_std']:.4f}")
        """
        if len(points) < n_folds * 10:
            self._logger.warning(
                f"[交叉验证] 数据点不足({len(points)})，减少折数"
            )
            n_folds = max(2, len(points) // 10)

        # 提取数据
        X = np.array([p.Q_total for p in points])
        if curve_type == "qh":
            y = np.array([p.H_system for p in points])
        elif curve_type == "qp":
            y = np.array([p.P_total for p in points])
        elif curve_type == "qeta":
            y = np.array([p.eta_total for p in points])
        else:
            y = np.array([p.H_system for p in points])

        # 随机打乱索引
        indices = np.arange(len(points))
        np.random.shuffle(indices)

        # 分折
        fold_size = len(points) // n_folds
        r2_scores = []
        rmse_scores = []

        for fold in range(n_folds):
            # 划分训练集和验证集
            val_start = fold * fold_size
            val_end = val_start + \
                fold_size if fold < n_folds - 1 else len(points)
            val_indices = indices[val_start:val_end]
            train_indices = np.concatenate(
                [indices[:val_start], indices[val_end:]])

            train_points = [points[i] for i in train_indices]
            val_X = X[val_indices]
            val_y = y[val_indices]

            try:
                # 在训练集上拟合
                if len(train_points) > 0 and train_points[0].running_pump_ids:
                    pump_combination = list(train_points[0].running_pump_ids)
                else:
                    pump_combination = [1]

                result = self.fit_with_method(
                    station_id=train_points[0].station_id if train_points else 0,
                    pump_combination=pump_combination,
                    points=train_points,
                    curve_type=curve_type,
                    method_id=method_id
                )

                # 在验证集上评估
                y_pred = np.array([result.predict(q) for q in val_X])

                # 计算R²
                ss_res = np.sum((val_y - y_pred) ** 2)
                ss_tot = np.sum((val_y - np.mean(val_y)) ** 2)
                r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

                # 计算RMSE
                rmse = np.sqrt(np.mean((val_y - y_pred) ** 2))

                r2_scores.append(r2)
                rmse_scores.append(rmse)

            except Exception as e:
                self._logger.warning(f"[交叉验证] 第{fold+1}折失败: {e}")

        if not r2_scores:
            return {
                "r2_mean": 0.0,
                "r2_std": 0.0,
                "rmse_mean": 0.0,
                "rmse_std": 0.0,
                "n_folds": n_folds,
                "success_folds": 0
            }

        result = {
            "r2_mean": float(np.mean(r2_scores)),
            "r2_std": float(np.std(r2_scores)),
            "rmse_mean": float(np.mean(rmse_scores)),
            "rmse_std": float(np.std(rmse_scores)),
            "n_folds": n_folds,
            "success_folds": len(r2_scores)
        }

        self._logger.info(
            f"[交叉验证] {n_folds}折CV完成: "
            f"R²={result['r2_mean']:.4f}±{result['r2_std']:.4f}, "
            f"RMSE={result['rmse_mean']:.2f}±{result['rmse_std']:.2f}"
        )

        return result

    # ==================== 原有接口（向后兼容）====================

    def fit_polynomial(
        self,
        station_id: int,
        pump_combination: List[int],
        points: List[GroupOperatingPoint],
        curve_type: str = "qh",
        degree: int = 2
    ) -> DirectFitResult:
        """多项式拟合（原有方法，保持向后兼容）

        内部实现改为调用fit_with_method，复用MethodRegistry

        Args:
            station_id: 泵站ID
            pump_combination: 泵组合
            points: 泵组工况点列表
            curve_type: 曲线类型
            degree: 多项式阶数（2/3/4）

        Returns:
            DirectFitResult: 拟合结果

        注意：此接口保持向后兼容，推荐使用fit_with_method
        """
        # 根据degree映射到method_id
        method_id_map = {
            2: "math_poly_2",
            3: "math_poly_3",
            # 4阶需要在MethodRegistry注册math_poly_4
        }

        method_id = method_id_map.get(degree, "math_poly_2")

        self._logger.info(
            f"[泵组拟合] 使用向后兼容接口fit_polynomial(degree={degree})",
            extra={"extra_data": {
                "degree": degree,
                "mapped_method_id": method_id
            }}
        )

        return self.fit_with_method(
            station_id=station_id,
            pump_combination=pump_combination,
            points=points,
            curve_type=curve_type,
            method_id=method_id
        )

    # ==================== 辅助方法 ====================

    def get_available_methods(self, curve_type: str = "qh") -> List[Dict[str, Any]]:
        """获取可用的拟合方法列表

        Args:
            curve_type: 曲线类型

        Returns:
            List[Dict]: 方法列表，每个元素包含method_id, method_name, priority等
        """
        try:
            return self._registry.list_methods(curve_type=curve_type)
        except Exception as e:
            self._logger.error(
                f"[泵组拟合] 获取可用方法失败: {e}",
                extra={"extra_data": {"error": str(e)}}
            )
            return []

    def get_recommended_methods(
        self,
        curve_type: str,
        data_points: int
    ) -> List[str]:
        """获取推荐方法列表

        Args:
            curve_type: 曲线类型
            data_points: 数据点数量

        Returns:
            List[str]: 推荐方法ID列表
        """
        return self._selector.select(
            curve_type=curve_type,
            data_points=data_points
        )
