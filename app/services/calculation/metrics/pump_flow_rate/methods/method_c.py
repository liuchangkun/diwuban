"""
方法C: 单泵直读

公式: Q_i = pump_flow_rate（直接读取）

依赖: pump_flow_rate
"""

from __future__ import annotations

from typing import Dict, Any
import pandas as pd


def calculate_method_c(data: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """
    方法C: 单泵直读

    Args:
        data: 输入数据（已过滤 running=1）
        params: 参数配置（未使用）

    Returns:
        计算结果（包含 pump_flow_rate 列）
    """
    df_result = data.copy()
    df_result['pump_flow_rate'] = df_result['main_pipeline_flow_rate']
    return df_result

