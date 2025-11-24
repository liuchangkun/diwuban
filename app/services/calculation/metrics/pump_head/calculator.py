"""
pump_head 计算执行模块
"""

import pandas as pd
import logging
from typing import Tuple
from app.services.calculation.metrics.pump_head.methods import calculate_pipe_loss_multi_pump


class Calculator:
    """计算执行器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def calculate(
        self,
        data: pd.DataFrame,
        method_id: str,
        params: dict
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        执行计算

        Args:
            data: 输入数据
            method_id: 方法ID
            params: 参数字典

        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]: (pump_outlet_pressure结果, pump_head结果)

        Raises:
            ValueError: 不支持的计算方法
        """
        self.logger.info(
            "[计算执行] 开始计算",
            extra={'extra_data': {
                'method_id': method_id,
                'data_rows': len(data)
            }}
        )

        # 根据方法ID调用对应的计算函数
        if method_id == 'pipe_loss_multi_pump':
            pump_outlet_pressure_result, pump_head_result = calculate_pipe_loss_multi_pump(data, params)
        else:
            raise ValueError(f"不支持的计算方法: {method_id}")

        self.logger.info(
            "[计算执行] 计算完成",
            extra={'extra_data': {
                'pump_outlet_pressure_rows': len(pump_outlet_pressure_result),
                'pump_head_rows': len(pump_head_result)
            }}
        )

        return pump_outlet_pressure_result, pump_head_result

