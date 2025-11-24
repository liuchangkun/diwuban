"""
pump_head 方法选择模块
"""

import pandas as pd
import logging
from typing import Dict, List


class MethodSelector:
    """方法选择器"""

    # 方法配置（按优先级从高到低）
    METHODS = [
        {
            'id': 'pipe_loss_multi_pump',
            'name': '压差法（简化版）',
            'priority': 100,
            'dependencies': [
                'pump_inlet_pressure',
                'main_pipeline_outlet_pressure'
            ],
            'conditions': {
                # 简化版不需要设备参数，只需要物理常数（rho, g）
                # 这些参数在全局级别已经配置
            }
        }
    ]

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def select_method(self, data: pd.DataFrame, params: dict) -> str:
        """
        选择计算方法

        Args:
            data: 输入数据
            params: 参数字典

        Returns:
            str: 选中的方法ID

        Raises:
            ValueError: 没有找到合适的计算方法
        """
        self.logger.info(
            "[方法选择] 开始选择计算方法",
            extra={'extra_data': {
                'data_columns': list(data.columns),
                'params_keys': list(params.keys())
            }}
        )

        for method in self.METHODS:
            self.logger.info(
                f"[方法选择] 检查方法: {method['name']}",
                extra={'extra_data': {'method_id': method['id'], 'priority': method['priority']}}
            )

            # 检查依赖
            dependencies_met = self._check_dependencies(data, method['dependencies'])

            # 检查条件
            conditions_met = self._check_conditions(params, method['conditions'])

            if dependencies_met and conditions_met:
                self.logger.info(
                    f"[方法选择] 选中方法: {method['name']}",
                    extra={'extra_data': {'method_id': method['id']}}
                )
                return method['id']

        # 没有找到合适的方法
        raise ValueError("没有找到合适的计算方法")

    def _check_dependencies(self, data: pd.DataFrame, dependencies: List[str]) -> bool:
        """检查数据依赖"""
        missing = [dep for dep in dependencies if dep not in data.columns]

        if missing:
            self.logger.warning(
                "[方法选择] 依赖检查失败",
                extra={'extra_data': {'missing_dependencies': missing}}
            )
            return False

        self.logger.info("[方法选择] 依赖检查通过")
        return True

    def _check_conditions(self, params: dict, conditions: Dict) -> bool:
        """检查参数条件"""
        # 检查设备参数
        if 'has_device_params' in conditions:
            missing_device_params = [
                p for p in conditions['has_device_params']
                if p not in params
            ]
            if missing_device_params:
                self.logger.warning(
                    "[方法选择] 设备参数检查失败",
                    extra={'extra_data': {'missing_params': missing_device_params}}
                )
                return False

        # 检查泵站参数
        if 'has_station_params' in conditions:
            missing_station_params = [
                p for p in conditions['has_station_params']
                if p not in params
            ]
            if missing_station_params:
                self.logger.warning(
                    "[方法选择] 泵站参数检查失败",
                    extra={'extra_data': {'missing_params': missing_station_params}}
                )
                return False

        self.logger.info("[方法选择] 条件检查通过")
        return True

