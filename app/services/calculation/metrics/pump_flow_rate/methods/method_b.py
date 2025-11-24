"""
方法B: 累计流量导数

公式: Q_i = dQ_cumulative_i / dt

依赖: pump_cumulative_flow_rate
"""

from __future__ import annotations

from typing import Dict, Any
import pandas as pd


def calculate_method_b(data: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """
    方法B: 累计流量导数

    Args:
        data: 输入数据（已过滤 running=1）
        params: 参数配置（smooth_window）

    Returns:
        计算结果（包含 pump_flow_rate 列）
    """
    smooth_window = params.get('smooth_window', 5)

    df_result = data.copy()

    # 确保数值列是 float 类型（数据库可能返回 Decimal 类型）
    df_result['pump_cumulative_flow'] = df_result['pump_cumulative_flow'].astype(float)

    # 计算时间差（秒）
    df_result['dt'] = df_result['ts_bucket'].diff().dt.total_seconds()

    # 计算累计流量差
    df_result['dcum'] = df_result['pump_cumulative_flow'].diff()

    # 计算瞬时流量（m³/h）
    df_result['pump_flow_rate'] = (df_result['dcum'] / df_result['dt']) * 3600

    # 平滑处理（移动平均）
    df_result['pump_flow_rate'] = df_result['pump_flow_rate'].rolling(
        window=smooth_window,
        min_periods=1,
        center=True
    ).mean()

    # 填充第一行的NaN（diff产生的）
    df_result['pump_flow_rate'] = df_result['pump_flow_rate'].fillna(0)

    # 删除临时列
    df_result = df_result.drop(columns=['dt', 'dcum'], errors='ignore')

    return df_result

