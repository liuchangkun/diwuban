"""
pump_efficiency 方法选择模块
"""

import pandas as pd
import logging
from typing import Optional


class MethodSelector:
    """方法选择器"""

    # 方法配置（按优先级从高到低）
    METHODS = [
        {
            'id': 'EFF_SIMPLE_V1',
            'name': '简化效率估算（基于Q/H/Pe）',
            'priority': 100,
            'dependencies': [
                'pump_flow_rate',
                'pump_head',
                'pump_active_power'
            ],
            'conditions': {}  # 无特殊条件
        }
    ]

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def select(self, data: pd.DataFrame) -> Optional[str]:
        """
        选择计算方法

        Args:
            data: 过滤后的数据

        Returns:
            str: 方法ID，如果没有合适的方法则返回 None
        """
        if data.empty:
            self.logger.warning("[方法选择] 数据为空，无法选择方法")
            return None

        self.logger.info(
            "[方法选择] 开始选择方法",
            extra={'extra_data': {'数据数量': len(data)}}
        )

        # 按优先级检查每个方法
        for method in sorted(self.METHODS, key=lambda x: x['priority'], reverse=True):
            method_id = method['id']
            method_name = method['name']

            # 检查依赖
            dependencies_met = self._check_dependencies(data, method['dependencies'])

            # 检查条件
            conditions_met = self._check_conditions(data, method['conditions'])

            self.logger.debug(
                "[方法选择] 检查方法",
                extra={'extra_data': {
                    '方法ID': method_id,
                    '方法名称': method_name,
                    '优先级': method['priority'],
                    '依赖满足': dependencies_met,
                    '条件满足': conditions_met
                }}
            )

            if dependencies_met and conditions_met:
                self.logger.info(
                    "[方法选择] 选择方法",
                    extra={'extra_data': {
                        '方法ID': method_id,
                        '方法名称': method_name,
                        '优先级': method['priority']
                    }}
                )
                return method_id

        # 没有合适的方法
        self.logger.warning("[方法选择] 没有找到合适的方法")
        return None

    def _check_dependencies(self, data: pd.DataFrame, dependencies: list) -> bool:
        """检查依赖是否满足"""
        for dep in dependencies:
            if dep not in data.columns:
                self.logger.debug(
                    "[方法选择] 缺少依赖列",
                    extra={'extra_data': {'依赖项': dep}}
                )
                return False
            if data[dep].isna().all():
                self.logger.debug(
                    "[方法选择] 依赖列全为NaN",
                    extra={'extra_data': {'依赖项': dep}}
                )
                return False
        return True

    def _check_conditions(self, data: pd.DataFrame, conditions: dict) -> bool:
        """检查条件是否满足"""
        # 当前方法没有特殊条件
        return True

