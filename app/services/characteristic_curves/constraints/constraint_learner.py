"""
约束学习器 (app.services.characteristic_curves.constraints.constraint_learner)

本模块提供从历史成功拟合中学习约束参数的功能：
- 从历史拟合结果学习参数范围
- 支持多种学习方法（3sigma、quantile、rated_based）
- 与ResultStorage集成

使用方式：
    from app.services.characteristic_curves.constraints import ConstraintLearner
    
    learner = ConstraintLearner()
    params = learner.learn_from_history(device_id, curve_type)
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

from app.services.characteristic_curves.shared import ResultStorage


class ConstraintLearner:
    """约束学习器 - 从历史成功拟合中学习约束参数

    支持的学习方法：
    - 3sigma: 3σ原则，适用于正态分布数据
    - quantile: 分位数方法，适用于非正态分布
    - rated_based: 基于额定值，有额定参数时使用
    """

    def __init__(
        self,
        storage: Optional[ResultStorage] = None,
        method: str = "3sigma"
    ):
        """初始化约束学习器

        Args:
            storage: 结果存储器（可选，默认创建新实例）
            method: 学习方法 ('3sigma', 'quantile', 'rated_based')
        """
        self._storage = storage or ResultStorage()
        self._method = method
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}")

        self._logger.info(
            "[约束学习] 初始化",
            extra={"extra_data": {"组件": "ConstraintLearner", "学习方法": method}}
        )

    def learn_from_history(
        self,
        device_id: int,
        curve_type: str,
        min_samples: int = 20
    ) -> Dict[str, Any]:
        """从历史成功拟合中学习约束参数

        Args:
            device_id: 设备ID
            curve_type: 曲线类型 ('qh', 'qp', 'qeta')
            min_samples: 最小样本数

        Returns:
            Dict: {
                'learned_params': Dict,  # 学习到的参数范围
                'confidence': float,     # 置信度 (0-1)
                'sample_count': int,     # 样本数量
                'method': str            # 使用的学习方法
            }
        """
        # 获取历史拟合结果
        history = self._get_successful_fits(
            device_id, curve_type, min_samples * 2)

        if len(history) < min_samples:
            self._logger.warning(
                f"[约束学习] 样本不足: {len(history)} < {min_samples}",
                extra={"extra_data": {"设备ID": device_id, "曲线类型": curve_type}}
            )
            return {
                'learned_params': {},
                'confidence': 0.0,
                'sample_count': len(history),
                'method': self._method,
                'error': f'样本不足: {len(history)} < {min_samples}'
            }

        # 根据方法学习参数
        if self._method == "3sigma":
            learned_params = self._learn_3sigma(history)
        elif self._method == "quantile":
            learned_params = self._learn_quantile(history)
        elif self._method == "rated_based":
            learned_params = self._learn_rated_based(history, device_id)
        else:
            learned_params = self._learn_3sigma(history)

        # 计算置信度
        confidence = min(1.0, len(history) / (min_samples * 5))

        result = {
            'learned_params': learned_params,
            'confidence': confidence,
            'sample_count': len(history),
            'method': self._method
        }

        self._logger.info(
            "[约束学习] 学习完成",
            extra={"extra_data": {
                "设备ID": device_id,
                "曲线类型": curve_type,
                "样本数": len(history),
                "置信度": f"{confidence:.2%}",
                "参数数": len(learned_params)
            }}
        )

        return result

    def _get_successful_fits(
        self,
        device_id: int,
        curve_type: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取历史成功拟合结果

        从数据库直接查询历史拟合记录

        表结构说明：
        - curve_fit_results: 主表，包含 id, device_id, curve_type, version, method_name, data_point_count
        - curve_fit_metrics: 指标表，通过 result_id 关联，包含 r_squared, rmse, mae, mape
        - curve_fit_params: 参数表，通过 result_id 关联，包含 param_category, param_key, param_value
        """
        try:
            from app.adapters.db import get_connection
            import json

            # 查询拟合结果和指标
            sql = """
                SELECT
                    r.id,
                    r.version,
                    r.method_name,
                    m.r_squared,
                    m.rmse,
                    r.data_point_count
                FROM curve_fit_results r
                LEFT JOIN curve_fit_metrics m ON r.id = m.result_id
                WHERE r.device_id = %s
                  AND r.curve_type = %s
                  AND m.r_squared > 0.9
                ORDER BY r.created_at DESC
                LIMIT %s
            """

            results = []
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (device_id, curve_type, limit))
                    rows = cur.fetchall()

                    for row in rows:
                        result_id = row[0]

                        # 查询该结果的拟合系数参数（param_category = 'fit'）
                        coefficients = {}
                        cur.execute(
                            """
                            SELECT param_key, param_value
                            FROM curve_fit_params
                            WHERE result_id = %s AND param_category = 'fit'
                            """,
                            (result_id,)
                        )
                        param_rows = cur.fetchall()
                        for param_row in param_rows:
                            coefficients[param_row[0]] = param_row[1]

                        results.append({
                            'version': row[1],
                            'method_name': row[2],
                            'r_squared': row[3],
                            'rmse': row[4],
                            'data_points': row[5],
                            'coefficients': coefficients
                        })

            return results
        except Exception as e:
            self._logger.error(
                f"[约束学习] 获取历史记录失败: {e}",
                extra={"extra_data": {"设备ID": device_id, "曲线类型": curve_type}}
            )
            raise

    def _learn_3sigma(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """使用3σ原则学习参数范围"""
        params = {}

        # 收集所有系数
        all_coefficients = {}
        for fit in history:
            coeffs = fit.get('coefficients', {})
            for key, value in coeffs.items():
                if key not in all_coefficients:
                    all_coefficients[key] = []
                if isinstance(value, (int, float)):
                    all_coefficients[key].append(value)

        # 计算每个系数的范围
        for key, values in all_coefficients.items():
            if len(values) >= 3:
                arr = np.array(values)
                mean = np.mean(arr)
                std = np.std(arr)
                params[f'{key}_min'] = float(mean - 3 * std)
                params[f'{key}_max'] = float(mean + 3 * std)
                params[f'{key}_mean'] = float(mean)

        return params

    def _learn_quantile(
        self,
        history: List[Dict[str, Any]],
        lower_quantile: float = 0.05,
        upper_quantile: float = 0.95
    ) -> Dict[str, Any]:
        """使用分位数方法学习参数范围"""
        params = {}

        # 收集所有系数
        all_coefficients = {}
        for fit in history:
            coeffs = fit.get('coefficients', {})
            for key, value in coeffs.items():
                if key not in all_coefficients:
                    all_coefficients[key] = []
                if isinstance(value, (int, float)):
                    all_coefficients[key].append(value)

        # 计算每个系数的分位数范围
        for key, values in all_coefficients.items():
            if len(values) >= 3:
                arr = np.array(values)
                params[f'{key}_min'] = float(
                    np.percentile(arr, lower_quantile * 100))
                params[f'{key}_max'] = float(
                    np.percentile(arr, upper_quantile * 100))
                params[f'{key}_median'] = float(np.median(arr))

        return params

    def _learn_rated_based(
        self,
        history: List[Dict[str, Any]],
        device_id: int
    ) -> Dict[str, Any]:
        """基于额定值学习参数范围（需要设备参数）"""
        # 首先使用3sigma作为基础
        params = self._learn_3sigma(history)

        # 从设备参数表获取额定值，调整参数范围
        try:
            from app.adapters.db import get_connection

            sql = """
                SELECT param_key, value_numeric
                FROM device_rated_params
                WHERE device_id = %s
                  AND param_key IN ('rated_flow', 'rated_head', 'rated_power')
                  AND (effective_to IS NULL OR effective_to > NOW())
            """

            device_params = {}
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (device_id,))
                    rows = cur.fetchall()
                    for row in rows:
                        device_params[row[0]] = float(
                            row[1]) if row[1] else None

            # 如果成功获取额定值，使用它们约束参数范围
            if device_params:
                rated_head = device_params.get('rated_head')
                rated_flow = device_params.get('rated_flow')

                if rated_head:
                    # H0(关死点扬程)应该在 0.7~1.3倍额定扬程之间
                    if 'H0_max' in params:
                        params['H0_max'] = min(
                            params['H0_max'], rated_head * 1.3)
                    if 'H0_min' in params:
                        params['H0_min'] = max(
                            params['H0_min'], rated_head * 0.7)

                if rated_flow:
                    # Q_max应该不超过1.5倍额定流量
                    if 'Q_max' in params:
                        params['Q_max'] = min(
                            params['Q_max'], rated_flow * 1.5)

                self._logger.info(
                    "[约束学习] 已使用额定参数调整范围",
                    extra={"extra_data": {
                        "设备ID": device_id,
                        "额定扬程": rated_head,
                        "额定流量": rated_flow
                    }}
                )
            else:
                self._logger.warning(
                    "[约束学习] 未找到额定参数，仅使用3sigma范围",
                    extra={"extra_data": {"设备ID": device_id}}
                )

        except Exception as e:
            self._logger.warning(
                f"[约束学习] 获取额定参数失败: {e}，仅使用3sigma范围",
                extra={"extra_data": {"设备ID": device_id}}
            )

        return params

    def learn_curve_constraints(
        self,
        device_id: int,
        curve_type: str,
        min_samples: int = 20
    ) -> Dict[str, Any]:
        """学习曲线约束参数（别名方法）

        等同于 learn_from_history，提供更明确的方法名。
        """
        return self.learn_from_history(device_id, curve_type, min_samples)

    @property
    def method(self) -> str:
        """获取学习方法"""
        return self._method

    @method.setter
    def method(self, value: str) -> None:
        """设置学习方法"""
        if value not in ('3sigma', 'quantile', 'rated_based'):
            raise ValueError(f"不支持的学习方法: {value}")
        self._method = value
