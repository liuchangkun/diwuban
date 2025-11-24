"""
pump_hydraulic_power MethodSelector模块

职责：选择计算方法
"""

import pandas as pd
from typing import Dict, Any


class MethodSelector:
    """方法选择器"""

    def __init__(self, params: Dict[str, Any], trace_id: str = ""):
        """
        初始化MethodSelector

        Args:
            params: 参数字典
            trace_id: 追踪ID
        """
        self.params = params
        self.trace_id = trace_id

    def select(self, data: pd.DataFrame, device_id: int) -> str:
        """
        选择计算方法

        Args:
            data: 过滤后的数据
            device_id: 设备ID

        Returns:
            str: 方法ID（'method_a'）
        """
        print(f"[{self.trace_id}] [MethodSelector] 开始选择方法...")
        print(f"  - 设备ID: {device_id}")
        print(f"  - 数据行数: {len(data)}")

        # pump_hydraulic_power只有一个方法：method_a（流量-扬程法）
        # 只要有pump_flow_rate和pump_head数据就可以使用
        if data.empty:
            print(f"  - ⚠️ 数据为空，无法选择方法")
            return None

        # 检查必需列
        required_cols = ['pump_flow_rate', 'pump_head']
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            print(f"  - ⚠️ 缺失必需列: {missing_cols}")
            return None

        # 检查数据可用性
        valid_rows = data[required_cols].notna().all(axis=1).sum()
        if valid_rows == 0:
            print(f"  - ⚠️ 无有效数据行")
            return None

        # 选择method_a
        method_id = 'method_a'
        print(f"  - ✅ 选择方法: {method_id}")
        print(f"  - 有效数据行数: {valid_rows}")

        return method_id

