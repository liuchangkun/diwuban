"""
约束优化器 (app.services.characteristic_curves.constraints.constraint_optimizer)

本模块提供约束优化功能:
- 在满足物理约束的前提下优化拟合结果
- 强制单调性修正
- 多目标优化

使用方式:
    from app.services.characteristic_curves.constraints import ConstraintOptimizer
    
    optimizer = ConstraintOptimizer()
    result = optimizer.optimize(
        initial_params={'a': 1.0, 'b': -0.5},
        objective_func=lambda params: rmse(params),
        constraints=[{'type': 'ineq', 'fun': lambda p: p['a']}]
    )

版本: v1.0
参考: 设计文档 3.8.5节
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
from scipy.optimize import minimize


class ConstraintOptimizer:
    """约束优化器

    在满足物理约束的前提下优化拟合结果。

    核心功能:
    1. 约束优化(scipy.optimize)
    2. 强制单调性
    3. 强制边界条件
    4. 多目标优化
    """

    def __init__(self):
        """初始化约束优化器"""
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}")
        self._logger.info(
            "[约束优化] 初始化",
            extra={"extra_data": {
                "组件": "ConstraintOptimizer",
                "优化方法": "scipy.optimize"
            }}
        )

    def optimize(
        self,
        initial_params: Dict[str, float],
        objective_func: Callable,
        constraints: List[Dict[str, Any]],
        bounds: Optional[Dict[str, Tuple[float, float]]] = None,
        method: str = 'SLSQP'
    ) -> Dict[str, Any]:
        """执行约束优化

        Args:
            initial_params: 初始参数字典
            objective_func: 目标函数(最小化),接受参数字典,返回float
            constraints: 约束条件列表,scipy.optimize格式
            bounds: 参数边界字典 {param_name: (min, max)}
            method: 优化方法 ('SLSQP', 'trust-constr', 'COBYLA')

        Returns:
            Dict: {
                'optimized_params': Dict[str, float],  # 优化后的参数
                'success': bool,                       # 是否成功
                'iterations': int,                     # 迭代次数
                'final_cost': float,                   # 最终代价
                'message': str                         # 优化信息
            }

        Raises:
            ValueError: 参数或约束格式错误
        """
        self._logger.info(
            "[约束优化] 开始优化",
            extra={"extra_data": {
                "初始参数": initial_params,
                "约束数量": len(constraints),
                "优化方法": method
            }}
        )

        # 验证输入
        if not initial_params:
            raise ValueError("初始参数不能为空")

        # 将字典参数转换为数组
        param_names = list(initial_params.keys())
        x0 = np.array([initial_params[name] for name in param_names])

        # 包装目标函数(接受数组参数)
        def objective_array(x: np.ndarray) -> float:
            params_dict = {name: x[i] for i, name in enumerate(param_names)}
            return objective_func(params_dict)

        # 转换边界格式
        scipy_bounds = None
        if bounds:
            scipy_bounds = [bounds.get(name, (None, None))
                            for name in param_names]

        # 执行优化
        try:
            result = minimize(
                objective_array,
                x0,
                method=method,
                constraints=constraints,
                bounds=scipy_bounds,
                options={'maxiter': 1000, 'disp': False}
            )

            # 转换结果回字典
            optimized_params = {
                name: float(result.x[i]) for i, name in enumerate(param_names)
            }

            self._logger.info(
                "[约束优化] 优化完成",
                extra={"extra_data": {
                    "成功": result.success,
                    "迭代次数": result.nit,
                    "最终代价": float(result.fun),
                    "优化参数": optimized_params
                }}
            )

            return {
                'optimized_params': optimized_params,
                'success': result.success,
                'iterations': result.nit,
                'final_cost': float(result.fun),
                'message': result.message
            }

        except Exception as e:
            self._logger.error(
                f"[约束优化] 优化失败: {e}",
                extra={"extra_data": {"错误": str(e)}}
            )
            return {
                'optimized_params': initial_params,
                'success': False,
                'iterations': 0,
                'final_cost': float('inf'),
                'message': str(e)
            }

    def enforce_monotonicity(
        self,
        x_values: np.ndarray,
        y_values: np.ndarray,
        direction: str = 'decreasing'
    ) -> np.ndarray:
        """强制单调性

        算法:
        - increasing: 确保后值≥前值,否则调整为前值
        - decreasing: 确保后值≤前值,否则调整为前值

        Args:
            x_values: X轴值(用于排序)
            y_values: Y轴值(待修正)
            direction: 单调方向 ('increasing', 'decreasing')

        Returns:
            np.ndarray: 修正后的Y值
        """
        if len(y_values) == 0:
            return y_values

        # 按X排序
        sorted_indices = np.argsort(x_values)
        y_sorted = y_values[sorted_indices].copy()

        # 强制单调性
        if direction == 'increasing':
            for i in range(1, len(y_sorted)):
                if y_sorted[i] < y_sorted[i-1]:
                    y_sorted[i] = y_sorted[i-1]
        elif direction == 'decreasing':
            for i in range(1, len(y_sorted)):
                if y_sorted[i] > y_sorted[i-1]:
                    y_sorted[i] = y_sorted[i-1]
        else:
            raise ValueError(f"不支持的单调方向: {direction}")

        # 恢复原顺序
        y_result = np.empty_like(y_sorted)
        y_result[sorted_indices] = y_sorted

        modified_count = int(np.sum(y_result != y_values))
        self._logger.info(
            f"[约束优化] 强制{direction}单调性: 修正{modified_count}个点",
            extra={"extra_data": {
                "方向": direction,
                "修正点数": modified_count,
                "总点数": len(y_values)
            }}
        )

        return y_result

    def multi_objective_optimize(
        self,
        initial_params: Dict[str, float],
        objectives: List[Callable],
        weights: List[float],
        constraints: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """多目标优化

        使用加权求和法将多个目标函数合并为单目标。

        Args:
            initial_params: 初始参数
            objectives: 目标函数列表
            weights: 权重列表(需归一化,和为1.0)
            constraints: 约束条件

        Returns:
            Dict: 优化结果,同optimize()
        """
        # 验证权重
        if len(objectives) != len(weights):
            raise ValueError("目标函数数量与权重数量不匹配")

        weight_sum = sum(weights)
        if abs(weight_sum - 1.0) > 1e-6:
            self._logger.warning(
                f"[约束优化] 权重和{weight_sum}不为1.0,自动归一化",
                extra={"extra_data": {"原始权重": weights}}
            )
            weights = [w / weight_sum for w in weights]

        # 组合目标函数
        def combined_objective(params: Dict[str, float]) -> float:
            total = 0.0
            for obj_func, weight in zip(objectives, weights):
                total += weight * obj_func(params)
            return total

        self._logger.info(
            "[约束优化] 多目标优化",
            extra={"extra_data": {
                "目标数量": len(objectives),
                "权重": weights
            }}
        )

        return self.optimize(
            initial_params=initial_params,
            objective_func=combined_objective,
            constraints=constraints
        )
