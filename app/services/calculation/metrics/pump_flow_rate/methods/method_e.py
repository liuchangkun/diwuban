"""
方法E: 频率分摊

公式: Q_i = Q_total × f_i / Σ(f_j)

依赖: main_pipeline_flow_rate, pump_frequency
"""

from __future__ import annotations

from typing import Dict, Any
import pandas as pd


def calculate_method_e(data: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """
    方法E: 频率分摊

    Args:
        data: 输入数据（已过滤 running=1）
        params: 参数配置（beta）

    Returns:
        计算结果（包含 pump_flow_rate 列）
    """
    # 获取参数（不允许默认值）
    beta = params.get('beta')

    # 验证必需参数
    if beta is None:
        raise ValueError(
            "缺少必需参数 'beta' (频率分摊指数). "
            "请在 calculation_parameters 表中添加该参数: "
            "metric_key='pump_flow_rate', method_id='method_e', param_name='beta'"
        )

    results = []

    for idx, row in data.iterrows():
        main_flow = row['main_pipeline_flow_rate']
        frequency = row['pump_frequency']
        other_devices = row.get('other_devices', None)

        # 计算当前设备的权重
        weight_current = frequency ** beta

        # 计算其他设备的权重总和
        weight_others = 0.0
        if other_devices is not None and isinstance(other_devices, list) and len(other_devices) > 0:
            for record in other_devices:
                frequency_other = record.get('pump_frequency', 0)
                running_other = record.get('running', 1)

                # 只计算运行设备的权重（使用 running 字段）
                if running_other == 1:
                    weight_others += frequency_other ** beta

        # 计算总权重
        weight_total = weight_current + weight_others

        # 计算当前设备的流量
        if weight_total > 0:
            flow = main_flow * (weight_current / weight_total)
        else:
            flow = 0.0

        results.append(flow)

    # 创建结果 DataFrame
    df_result = data.copy()
    df_result['pump_flow_rate'] = results

    return df_result

