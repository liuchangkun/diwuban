"""
压差法（简化版）计算方法

计算公式：
1. 泵出口压力：P_pump_out = P_main_out（并联系统中，泵出口压力 ≈ 总管出口压力）
2. 水泵扬程：H = (P_pump_out - P_pump_in) × 1e6 / (ρ × g)

说明：
- 在并联系统中，所有泵的出口压力应该相等，且等于总管出口压力
- 之前的公式使用 correction_factor 和 delta_P_pipe 修正，导致计算值偏高120-180%
- 简化后的公式直接使用实测总管出口压力，精度最高
"""

import pandas as pd
import numpy as np
from typing import Tuple
import logging


def calculate_pipe_loss_multi_pump(
    data: pd.DataFrame,
    params: dict
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    压差法（简化版）计算 pump_outlet_pressure 和 pump_head

    Args:
        data: 输入数据（包含 pump_inlet_pressure, main_pipeline_outlet_pressure）
        params: 参数字典（rho, g）

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: (pump_outlet_pressure结果, pump_head结果)
    """
    logger = logging.getLogger(__name__)

    # 获取参数（只需要物理常数）
    rho = params.get('rho', 1000.0)
    g = params.get('g', 9.81)

    logger.info(
        f"[计算方法] 压差法（简化版）",
        extra={'extra_data': {
            'rho': rho,
            'g': g,
            'note': '并联系统中，泵出口压力 ≈ 总管出口压力'
        }}
    )

    # 复制数据
    result = data.copy()

    # 步骤1：泵出口压力 = 总管出口压力
    # 在并联系统中，所有泵的出口压力应该相等，且等于总管出口压力
    result['pump_outlet_pressure'] = result['main_pipeline_outlet_pressure']

    # 步骤2：计算水泵扬程
    # H = (P_pump_out - P_pump_in) × 1e6 / (ρ × g) (m)
    result['pump_head'] = (
        (result['pump_outlet_pressure'] - result['pump_inlet_pressure']) * 1e6 / (rho * g)
    )

    logger.info(
        f"[计算方法] 计算完成",
        extra={'extra_data': {
            'total_rows': len(result),
            'pump_outlet_pressure_range': f"[{result['pump_outlet_pressure'].min():.4f}, {result['pump_outlet_pressure'].max():.4f}] MPa",
            'pump_head_range': f"[{result['pump_head'].min():.2f}, {result['pump_head'].max():.2f}] m"
        }}
    )

    # 返回两个结果DataFrame
    pump_outlet_pressure_result = result[['ts_bucket', 'pump_outlet_pressure']].copy()
    pump_head_result = result[['ts_bucket', 'pump_head']].copy()

    return pump_outlet_pressure_result, pump_head_result

