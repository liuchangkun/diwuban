"""
方法B: 极对数法

公式: n = 60 × f / pole_pairs × (1 - slip)

依赖: pump_frequency, pole_pairs, slip
"""

from __future__ import annotations

from typing import Dict, Any
import pandas as pd
import numpy as np


def calculate_method_b(data: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """
    方法B: 极对数法

    Args:
        data: 输入数据（已过滤 running=1）
        params: 参数配置（可选，用于覆盖设备参数）

    Returns:
        计算结果（包含 pump_speed 列）
    """
    # 验证必需的数据列
    required_columns = ['pump_frequency', 'pole_pairs', 'slip']
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(
            f"缺少必需的数据列: {', '.join(missing_columns)}. "
            f"这些参数应该从 device_rated_params 表加载到数据中"
        )

    # 计算转速
    results = []
    for idx, row in data.iterrows():
        f = float(row['pump_frequency'])
        pole_pairs = float(row['pole_pairs'])
        slip = float(row['slip'])
        
        # 频率为0时，转速为0
        if f <= 0:
            n = 0.0
        else:
            # 同步转速
            n_sync = 60 * f / pole_pairs
            # 实际转速（考虑滑差）
            n = n_sync * (1 - slip)

        results.append(n)

    # 创建结果 DataFrame
    df_result = data.copy()
    df_result['pump_speed'] = results

    return df_result

