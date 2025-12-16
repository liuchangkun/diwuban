"""
方法A: 频率比例法

公式: n = (f / f_ref) × n_ref

依赖: pump_frequency
参数: f_ref (额定频率), n_ref (额定转速)
"""

from __future__ import annotations

from typing import Dict, Any
import pandas as pd
import numpy as np


def calculate_method_a(data: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """
    方法A: 频率比例法

    Args:
        data: 输入数据（已过滤 running=1）
        params: 参数配置（f_ref, n_ref）

    Returns:
        计算结果（包含 pump_speed 列）
    """
    # 获取参数
    f_ref = params.get('f_ref')
    n_ref = params.get('n_ref')

    # 验证必需参数
    if f_ref is None:
        raise ValueError(
            "缺少必需参数 'f_ref'. "
            "请在 calculation_parameters 表中添加该参数"
        )
    if n_ref is None:
        raise ValueError(
            "缺少必需参数 'n_ref'. "
            "请在 calculation_parameters 表中添加该参数"
        )

    # 计算转速
    results = []
    for idx, row in data.iterrows():
        f = float(row['pump_frequency'])
        
        # 频率为0时，转速为0
        if f <= 0:
            n = 0.0
        else:
            n = (f / f_ref) * n_ref

        results.append(n)

    # 创建结果 DataFrame
    df_result = data.copy()
    df_result['pump_speed'] = results

    return df_result

