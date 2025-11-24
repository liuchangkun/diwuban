"""
方法选择器（MethodSelector）

职责：
- 根据数据可用性和条件，选择最合适的计算方法
- 按优先级顺序检查方法可用性
- 返回方法ID
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
import pandas as pd
import logging


class MethodSelector:
    """
    方法选择器

    职责：
    - 根据数据可用性和条件选择最合适的计算方法
    - 按优先级顺序检查（100 → 90 → 80）
    """

    # 方法配置（按优先级从高到低：数字越小优先级越高）
    METHODS = [
        {
            'id': 'method_c',
            'name': '校准系数法',
            'priority': 80,
            'dependencies': ['pump_frequency', 'speed_calibration_k', 'speed_calibration_b'],
            'conditions': {'calibration_quality': ['medium', 'high']}
        },
        {
            'id': 'method_b',
            'name': '极对数法',
            'priority': 90,
            'dependencies': ['pump_frequency', 'pole_pairs', 'slip'],
            'conditions': {}
        },
        {
            'id': 'method_a',
            'name': '频率比例法',
            'priority': 100,
            'dependencies': ['pump_frequency'],
            'conditions': {}
        }
    ]

    def __init__(self, params: Optional[Dict[str, Any]] = None, trace_id: Optional[str] = None):
        """
        初始化方法选择器

        Args:
            params: 参数字典
            trace_id: 追踪ID（用于日志关联）
        """
        self.logger = logging.getLogger(__name__)
        self.trace_id = trace_id
        self.params = params or {}

    def select_method(self, data: pd.DataFrame) -> str:
        """
        选择计算方法（按优先级顺序）

        Args:
            data: 过滤后的数据

        Returns:
            方法ID（method_a, method_b, method_c）

        Raises:
            ValueError: 如果没有合适的方法
        """
        self.logger.info(
            "[方法选择] 开始选择计算方法",
            extra={'extra_data': {
                '追踪ID': self.trace_id,
                '数据行数': len(data),
                '可用列': list(data.columns)
            }}
        )

        # 按优先级检查每个方法
        for method in self.METHODS:
            method_id = method['id']
            method_name = method['name']
            priority = method['priority']

            # 检查依赖
            dependencies_met = self._check_dependencies(data, method['dependencies'])

            # 检查条件
            conditions_met = self._check_conditions(data, method['conditions'])

            self.logger.debug(
                f"[方法选择] 检查方法: {method_name}",
                extra={'extra_data': {
                    '追踪ID': self.trace_id,
                    '方法ID': method_id,
                    'priority': priority,
                    'dependencies_met': dependencies_met,
                    'conditions_met': conditions_met
                }}
            )

            # 如果依赖和条件都满足，选择此方法
            if dependencies_met and conditions_met:
                self.logger.info(
                    f"[方法选择] 选择完成: {method_name}",
                    extra={'extra_data': {
                        '追踪ID': self.trace_id,
                        '选择的方法': method_id,
                        'method_name': method_name,
                        'priority': priority
                    }}
                )
                return method_id

        # 没有合适的方法
        error_msg = "没有合适的计算方法"
        self.logger.error(
            f"[方法选择] 失败: {error_msg}",
            extra={'extra_data': {
                '追踪ID': self.trace_id,
                '可用列': list(data.columns)
            }}
        )
        raise ValueError(error_msg)

    def _check_dependencies(self, data: pd.DataFrame, dependencies: List[str]) -> bool:
        """
        检查依赖是否满足

        Args:
            data: 数据
            dependencies: 依赖列表

        Returns:
            是否满足
        """
        for dep in dependencies:
            if dep not in data.columns:
                return False
            # 检查是否有非空值
            if data[dep].isna().all():
                return False
        return True

    def _check_conditions(self, data: pd.DataFrame, conditions: Dict[str, Any]) -> bool:
        """
        检查条件是否满足

        Args:
            data: 数据
            conditions: 条件字典

        Returns:
            是否满足
        """
        # 如果没有条件，直接返回True
        if not conditions:
            return True

        # 检查calibration_quality条件
        if 'calibration_quality' in conditions:
            if 'calibration_quality' not in data.columns:
                return False
            quality = data['calibration_quality'].iloc[0] if len(data) > 0 else None
            if quality not in conditions['calibration_quality']:
                return False

        return True

