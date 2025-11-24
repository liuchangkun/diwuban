"""
pump_efficiency 数据过滤模块
"""

import pandas as pd
import numpy as np
import logging


class DataFilter:
    """数据过滤器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def filter(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        过滤无效数据

        Args:
            data: 原始数据

        Returns:
            pd.DataFrame: 过滤后的数据
        """
        if data.empty:
            return data

        original_count = len(data)

        self.logger.info(
            "[数据过滤] 开始过滤",
            extra={'extra_data': {'原始数量': original_count}}
        )

        # 1. 过滤运行状态（效率只在运行时有意义）
        before_running = len(data)
        if 'running' in data.columns:
            data = data[data['running'] == 1].copy()
            running_count = before_running - len(data)
            self.logger.info(
                "[数据过滤] 运行状态过滤完成",
                extra={'extra_data': {
                    '移除停机': running_count,
                    '剩余数量': len(data)
                }}
            )

        # 检查必需的列是否存在
        required_columns = ['pump_flow_rate', 'pump_head', 'pump_active_power']
        missing_columns = [col for col in required_columns if col not in data.columns]

        if missing_columns:
            self.logger.warning(
                "[数据过滤] 缺少必需的列，返回空数据",
                extra={'extra_data': {
                    '原始数量': original_count,
                    '缺失列': missing_columns
                }}
            )
            return pd.DataFrame()

        # 2. 移除 NaN 值
        before_nan = len(data)
        data = data.dropna(subset=required_columns)
        nan_count = before_nan - len(data)

        # 3. 移除 Inf 值
        before_inf = len(data)
        data = data[~data['pump_flow_rate'].isin([np.inf, -np.inf])]
        data = data[~data['pump_head'].isin([np.inf, -np.inf])]
        data = data[~data['pump_active_power'].isin([np.inf, -np.inf])]
        inf_count = before_inf - len(data)

        # 4. 移除负值
        before_negative = len(data)
        data = data[data['pump_flow_rate'] >= 0]
        data = data[data['pump_head'] >= 0]
        data = data[data['pump_active_power'] >= 0]
        negative_count = before_negative - len(data)

        # 5. 移除功率为0的数据（避免除零错误）
        before_zero_power = len(data)
        data = data[data['pump_active_power'] > 0]
        zero_power_count = before_zero_power - len(data)

        final_count = len(data)

        self.logger.info(
            "[数据过滤] 过滤完成",
            extra={'extra_data': {
                '原始数量': original_count,
                '移除NaN': nan_count,
                '移除Inf': inf_count,
                '移除负值': negative_count,
                '移除零功率': zero_power_count,
                '最终数量': final_count,
                '过滤比例': f"{(original_count - final_count) / original_count * 100:.2f}%" if original_count > 0 else "0%"
            }}
        )

        return data

