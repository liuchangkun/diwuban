"""
参数优化器 (app.services.characteristic_curves.shared.parameter_optimizer)

本模块提供拟合参数的优化和调优功能：
- 交叉验证：K折交叉验证评估参数
- 网格搜索：搜索最优参数组合
- 约束优化：基于历史数据优化约束参数

使用方式：
    from app.services.characteristic_curves.shared import ParameterOptimizer
    
    optimizer = ParameterOptimizer(n_folds=5, random_state=42)
    cv_result = optimizer.cross_validate(X, y, fit_func, params)
"""

import logging
import time
from itertools import product
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold


class ParameterOptimizer:
    """参数优化器
    
    提供交叉验证、网格搜索和约束优化功能。
    """

    def __init__(self, n_folds: int = 5, random_state: int = 42):
        """初始化参数优化器
        
        Args:
            n_folds: 交叉验证折数，默认5
            random_state: 随机种子，默认42
        """
        self._n_folds = n_folds
        self._random_state = random_state
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        self._logger.info(
            "[参数优化] 初始化",
            extra={"extra_data": {
                "组件": "ParameterOptimizer",
                "折数": n_folds,
                "随机种子": random_state
            }}
        )

    def cross_validate(
        self,
        X: np.ndarray,
        y: np.ndarray,
        fit_func: Callable[[np.ndarray, np.ndarray, Dict[str, Any]], Callable],
        params: Dict[str, Any],
        n_folds: Optional[int] = None
    ) -> Dict[str, Any]:
        """交叉验证评估参数
        
        Args:
            X: 特征数组
            y: 目标数组
            fit_func: 拟合函数，接收(X_train, y_train, params)，返回预测函数
            params: 拟合参数
            n_folds: 折数（可选，不指定则使用默认值）
            
        Returns:
            Dict: 包含以下键：
                - mean_r2: 平均R²
                - std_r2: R²标准差
                - fold_scores: 各折的R²分数列表
                - mean_rmse: 平均RMSE
                - std_rmse: RMSE标准差
        """
        start_time = time.time()
        n_folds = n_folds or self._n_folds
        
        if len(X) < n_folds:
            self._logger.warning(
                f"[参数优化] 数据量({len(X)})小于折数({n_folds})，调整折数"
            )
            n_folds = max(2, len(X))
        
        kf = KFold(n_splits=n_folds, shuffle=True, random_state=self._random_state)
        
        r2_scores = []
        rmse_scores = []
        
        for fold_idx, (train_idx, val_idx) in enumerate(kf.split(X), 1):
            X_train, X_val = X[train_idx], X[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]
            
            # 拟合模型
            predict_func = fit_func(X_train, y_train, params)
            
            # 预测验证集
            y_pred = predict_func(X_val)
            
            # 计算R²
            ss_res = np.sum((y_val - y_pred) ** 2)
            ss_tot = np.sum((y_val - np.mean(y_val)) ** 2)
            r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
            r2_scores.append(r2)
            
            # 计算RMSE
            rmse = np.sqrt(np.mean((y_val - y_pred) ** 2))
            rmse_scores.append(rmse)
        
        result = {
            'mean_r2': float(np.mean(r2_scores)),
            'std_r2': float(np.std(r2_scores)),
            'fold_scores': r2_scores,
            'mean_rmse': float(np.mean(rmse_scores)),
            'std_rmse': float(np.std(rmse_scores)),
            'n_folds': n_folds,
            'params': params
        }
        
        duration = (time.time() - start_time) * 1000
        self._logger.info(
            "[参数优化] 交叉验证完成",
            extra={"extra_data": {
                "折数": n_folds,
                "平均R²": round(result['mean_r2'], 4),
                "R²标准差": round(result['std_r2'], 4),
                "耗时ms": round(duration, 2)
            }}
        )
        
        return result

    def grid_search(
        self,
        X: np.ndarray,
        y: np.ndarray,
        fit_func: Callable[[np.ndarray, np.ndarray, Dict[str, Any]], Callable],
        param_grid: Dict[str, List[Any]]
    ) -> Dict[str, Any]:
        """网格搜索最优参数
        
        Args:
            X: 特征数组
            y: 目标数组
            fit_func: 拟合函数
            param_grid: 参数网格，如 {'degree': [2, 3, 4]}
            
        Returns:
            Dict: 包含以下键：
                - best_params: 最优参数
                - best_score: 最优分数(R²)
                - all_results: 所有参数组合的结果列表
        """
        start_time = time.time()
        
        # 生成所有参数组合
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        all_combinations = list(product(*param_values))
        
        self._logger.info(
            "[参数优化] 开始网格搜索",
            extra={"extra_data": {
                "参数名": param_names,
                "组合数": len(all_combinations)
            }}
        )
        
        all_results = []
        best_score = -np.inf
        best_params = None

        for combo in all_combinations:
            params = dict(zip(param_names, combo))

            try:
                cv_result = self.cross_validate(X, y, fit_func, params)
                score = cv_result['mean_r2']

                all_results.append({
                    'params': params,
                    'mean_r2': score,
                    'std_r2': cv_result['std_r2'],
                    'mean_rmse': cv_result['mean_rmse']
                })

                if score > best_score:
                    best_score = score
                    best_params = params.copy()

            except Exception as e:
                self._logger.warning(
                    f"[参数优化] 参数组合失败: {params}",
                    extra={"extra_data": {"错误": str(e)}}
                )
                all_results.append({
                    'params': params,
                    'error': str(e)
                })

        # 按分数排序
        all_results.sort(
            key=lambda x: x.get('mean_r2', -np.inf),
            reverse=True
        )

        result = {
            'best_params': best_params,
            'best_score': float(best_score) if best_score > -np.inf else None,
            'all_results': all_results,
            'total_combinations': len(all_combinations)
        }

        duration = (time.time() - start_time) * 1000
        self._logger.info(
            "[参数优化] 网格搜索完成",
            extra={"extra_data": {
                "最优参数": best_params,
                "最优R²": round(best_score, 4) if best_score > -np.inf else None,
                "组合数": len(all_combinations),
                "耗时ms": round(duration, 2)
            }}
        )

        return result

    def optimize_constraints(
        self,
        device_id: int,
        curve_type: str,
        historical_data: pd.DataFrame
    ) -> Dict[str, float]:
        """基于历史数据优化约束参数

        根据设备的历史运行数据，自动推断合理的约束边界。

        Args:
            device_id: 设备ID
            curve_type: 曲线类型 ('qh', 'qp', 'qeta')
            historical_data: 历史数据，包含 Q、H、P、η 等列

        Returns:
            Dict[str, float]: 优化后的约束参数，如：
                - q_min, q_max: 流量范围
                - h_min, h_max: 扬程范围
                - monotonic_threshold: 单调性阈值
        """
        start_time = time.time()

        constraints = {}

        # 根据曲线类型确定X/Y列
        column_mapping = {
            'qh': {'x': 'pump_flow_rate', 'y': 'pump_head'},
            'qp': {'x': 'pump_flow_rate', 'y': 'pump_active_power'},
            'qeta': {'x': 'pump_flow_rate', 'y': 'pump_efficiency'}
        }

        if curve_type not in column_mapping:
            self._logger.warning(f"[参数优化] 未知曲线类型: {curve_type}")
            return constraints

        x_col = column_mapping[curve_type]['x']
        y_col = column_mapping[curve_type]['y']

        # 检查列是否存在
        if x_col not in historical_data.columns or y_col not in historical_data.columns:
            self._logger.warning(
                f"[参数优化] 缺少必要列",
                extra={"extra_data": {"需要": [x_col, y_col], "实际": list(historical_data.columns)}}
            )
            return constraints

        # 过滤有效数据
        valid_data = historical_data[[x_col, y_col]].dropna()

        if len(valid_data) < 10:
            self._logger.warning(f"[参数优化] 有效数据点不足: {len(valid_data)}")
            return constraints

        X = valid_data[x_col].values
        Y = valid_data[y_col].values

        # 计算流量范围（使用1%和99%分位数，避免异常值影响）
        constraints['q_min'] = float(np.percentile(X, 1))
        constraints['q_max'] = float(np.percentile(X, 99))

        # 计算Y值范围
        y_key = 'h' if curve_type == 'qh' else ('p' if curve_type == 'qp' else 'eta')
        constraints[f'{y_key}_min'] = float(np.percentile(Y, 1))
        constraints[f'{y_key}_max'] = float(np.percentile(Y, 99))

        # 计算单调性阈值（基于数据噪声水平）
        # 使用相邻点差值的标准差作为噪声估计
        sorted_indices = np.argsort(X)
        X_sorted = X[sorted_indices]
        Y_sorted = Y[sorted_indices]

        if len(Y_sorted) > 1:
            diffs = np.diff(Y_sorted)
            noise_level = np.std(diffs)
            constraints['monotonic_threshold'] = float(noise_level * 0.5)
        else:
            constraints['monotonic_threshold'] = 0.01

        duration = (time.time() - start_time) * 1000
        self._logger.info(
            "[参数优化] 约束优化完成",
            extra={"extra_data": {
                "设备ID": device_id,
                "曲线类型": curve_type,
                "数据点数": len(valid_data),
                "约束参数": constraints,
                "耗时ms": round(duration, 2)
            }}
        )

        return constraints

    @property
    def n_folds(self) -> int:
        """获取交叉验证折数"""
        return self._n_folds

    @n_folds.setter
    def n_folds(self, value: int) -> None:
        """设置交叉验证折数"""
        if value < 2:
            raise ValueError("折数必须大于等于2")
        self._n_folds = value

    @property
    def random_state(self) -> int:
        """获取随机种子"""
        return self._random_state

