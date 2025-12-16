"""
pump_efficiency 计算器模块
"""

import pandas as pd
import logging
from typing import Optional
from app.services.calculation.metrics.pump_efficiency.methods import calculate_power_flow_head


class Calculator:
    """计算器"""

    def __init__(self, shared_services):
        self.logger = logging.getLogger(__name__)
        self.shared_services = shared_services

    def calculate(
        self,
        data: pd.DataFrame,
        method_id: str,
        device_id: int
    ) -> Optional[pd.DataFrame]:
        """
        执行计算

        Args:
            data: 过滤后的数据
            method_id: 方法ID
            device_id: 设备ID

        Returns:
            pd.DataFrame: 计算结果，如果计算失败则返回 None
        """
        if data.empty:
            self.logger.warning("[计算器] 数据为空，无法计算")
            return None

        self.logger.info(
            "[计算器] 开始计算",
            extra={'extra_data': {
                '方法ID': method_id,
                '设备ID': device_id,
                '数据数量': len(data)
            }}
        )

        # 加载参数
        params = self._load_parameters(method_id, device_id)

        # 根据方法ID调用对应的计算函数
        if method_id == 'EFF_SIMPLE_V1':
            result = calculate_power_flow_head(data, params)
        else:
            self.logger.error(
                "[计算器] 未知的方法ID",
                extra={'extra_data': {'方法ID': method_id}}
            )
            return None

        self.logger.info(
            "[计算器] 计算完成",
            extra={'extra_data': {
                '方法ID': method_id,
                '结果数量': len(result) if result is not None else 0
            }}
        )

        return result

    def _load_parameters(self, method_id: str, device_id: int) -> dict:
        """
        加载计算参数

        Args:
            method_id: 方法ID
            device_id: 设备ID

        Returns:
            dict: 参数字典
        """
        # 使用 SharedServices.parameter_manager 加载参数
        params = self.shared_services.parameter_manager.get_parameters(
            metric_key='pump_efficiency',
            method_id=method_id,
            device_id=device_id
        )

        self.logger.debug(
            "[计算器] 参数加载完成",
            extra={'extra_data': {
                '方法ID': method_id,
                '设备ID': device_id,
                '参数': params
            }}
        )

        return params

