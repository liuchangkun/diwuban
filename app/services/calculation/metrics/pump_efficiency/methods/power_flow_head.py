"""
功率-流量-扬程法计算pump_efficiency

计算公式：
1. 将流量从 m³/h 转换为 m³/s：Q_s = Q / 3600
2. 计算水力功率：P_h = ρ × g × Q_s × H (W)
3. 计算效率：η = P_h / (P_e × 1000)
4. 裁剪到合理范围：η = clip(η, eta_min, eta_max)

其中：
- Q: 泵瞬时流量 (m³/h)
- H: 泵扬程 (m)
- P_e: 泵有功功率 (kW)
- ρ: 水密度 (kg/m³)
- g: 重力加速度 (m/s²)
- η: 泵效率 (0-1)
"""

import pandas as pd
import numpy as np
import logging
from typing import Tuple


def calculate_power_flow_head(
    data: pd.DataFrame,
    params: dict
) -> pd.DataFrame:
    """
    功率-流量-扬程法计算pump_efficiency

    Args:
        data: 输入数据（包含 pump_flow_rate, pump_head, pump_active_power）
        params: 参数字典（rho, g, eta_min, eta_max）

    Returns:
        pd.DataFrame: 计算结果（包含 pump_efficiency 列）
    """
    logger = logging.getLogger(__name__)

    # 获取参数
    rho = params.get('rho', 1000.0)  # 水密度 (kg/m³)
    g = params.get('g', 9.81)  # 重力加速度 (m/s²)
    eta_min = params.get('eta_min', 0.30)  # 最小效率阈值
    eta_max = params.get('eta_max', 0.95)  # 最大效率阈值

    logger.info(
        "[计算方法] 功率-流量-扬程法",
        extra={'extra_data': {
            'rho': rho,
            'g': g,
            'eta_min': eta_min,
            'eta_max': eta_max,
            'data_count': len(data)
        }}
    )

    # 复制数据
    result = data.copy()

    # 步骤1: 将流量从 m³/h 转换为 m³/s
    result['Q_s'] = result['pump_flow_rate'] / 3600.0

    # 步骤2: 计算水力功率 (W)
    # P_h = ρ × g × Q_s × H
    result['P_h'] = rho * g * result['Q_s'] * result['pump_head']

    # 步骤3: 计算效率
    # η = P_h / (P_e × 1000)
    result['pump_efficiency'] = result['P_h'] / (result['pump_active_power'] * 1000.0)

    # 步骤4: 裁剪到合理范围
    result['pump_efficiency'] = result['pump_efficiency'].clip(lower=eta_min, upper=eta_max)

    logger.info(
        "[计算方法] 计算完成",
        extra={'extra_data': {
            'result_count': len(result),
            'efficiency_stats': {
                'min': float(result['pump_efficiency'].min()),
                'max': float(result['pump_efficiency'].max()),
                'mean': float(result['pump_efficiency'].mean()),
                'median': float(result['pump_efficiency'].median())
            }
        }}
    )

    return result

