"""
pump_hydraulic_power Calculator模块

职责：执行计算
"""

import pandas as pd
from typing import Dict, Any
from datetime import datetime


class Calculator:
    """计算器"""

    def __init__(self, params: Dict[str, Any], method_id: str, trace_id: str = ""):
        """
        初始化Calculator

        Args:
            params: 参数字典
            method_id: 方法ID
            trace_id: 追踪ID
        """
        self.params = params
        self.method_id = method_id
        self.trace_id = trace_id

    def calculate(self, data: pd.DataFrame, device_id: int) -> pd.DataFrame:
        """
        执行计算

        Args:
            data: 过滤后的数据
            device_id: 设备ID

        Returns:
            pd.DataFrame: 计算结果
        """
        print(f"[{self.trace_id}] [Calculator] 开始计算...")
        print(f"  - 方法: {self.method_id}")
        print(f"  - 设备ID: {device_id}")
        print(f"  - 输入数据行数: {len(data)}")

        if data.empty:
            print(f"  - ⚠️ 输入数据为空")
            return pd.DataFrame()

        # 导入对应的方法
        if self.method_id == 'method_a':
            from .methods.method_a import calculate
        else:
            raise ValueError(f"未知的方法ID: {self.method_id}")

        # 执行计算
        result_df = calculate(data, self.params, device_id, self.trace_id)

        print(f"  - 输出数据行数: {len(result_df)}")

        # 显示样本结果
        if not result_df.empty:
            sample = result_df.head(3)
            print(f"  - 样本结果（前3行）:")
            for idx, row in sample.iterrows():
                print(f"    {row['ts_bucket']} | device={row['device_id']} | "
                      f"P_h={row['pump_hydraulic_power']:.2f} kW | "
                      f"Q={row['pump_flow_rate']:.2f} m³/h | H={row['pump_head']:.2f} m")

        return result_df

