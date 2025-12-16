"""
pump_hydraulic_power DataFilter模块

职责：过滤非运行状态的数据
"""

import pandas as pd
from typing import Optional


class DataFilter:
    """数据过滤器"""

    def __init__(self, trace_id: str = ""):
        """
        初始化DataFilter

        Args:
            trace_id: 追踪ID
        """
        self.trace_id = trace_id

    def filter(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        过滤非运行状态的数据

        Args:
            data: 原始数据

        Returns:
            pd.DataFrame: 过滤后的数据
        """
        print(f"[{self.trace_id}] [DataFilter] 开始过滤数据...")
        print(f"  - 输入数据行数: {len(data)}")

        if data.empty:
            print(f"  - ⚠️ 输入数据为空")
            return data

        # 过滤运行状态
        # 使用mv_device_running_1s.running字段（严格禁止硬编码阈值）
        filtered_data = data[data['running'] == 1].copy()

        print(f"  - 过滤后数据行数: {len(filtered_data)}")
        print(f"  - 移除行数: {len(data) - len(filtered_data)}")

        # 检查必需列
        required_cols = ['pump_flow_rate', 'pump_head']
        missing_cols = [col for col in required_cols if col not in filtered_data.columns]
        if missing_cols:
            print(f"  - ⚠️ 缺失必需列: {missing_cols}")
            return pd.DataFrame()

        # 移除缺失值
        before_dropna = len(filtered_data)
        filtered_data = filtered_data.dropna(subset=required_cols)
        after_dropna = len(filtered_data)

        if before_dropna > after_dropna:
            print(f"  - 移除缺失值: {before_dropna - after_dropna}行")

        print(f"  - 最终数据行数: {len(filtered_data)}")

        return filtered_data

