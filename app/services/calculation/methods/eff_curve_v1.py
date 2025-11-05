"""
EFF_CURVE_V1: 基于特性曲线的泵效率计算方法

基于泵特性曲线的效率插值计算。
从 pump_characteristic_curves 表中读取效率曲线数据，
根据实际流量进行线性插值得到效率值。

作者：AI Agent
创建时间：2025-10-26
版本：v1.0
"""

from typing import Dict
import numpy as np
from app.adapters.db import get_connection
import logging

logger = logging.getLogger(__name__)


def calculate_pump_efficiency_eff_curve_v1(
    data: Dict[str, np.ndarray],
    params: Dict[str, float],
    device_id: int = None
) -> np.ndarray:
    """
    基于特性曲线的泵效率计算

    从 pump_characteristic_curves 表中读取效率曲线数据，
    根据实际流量进行线性插值得到效率值。

    公式:
        η = interp(Q, Q_curve, η_curve)

    其中:
        - η: 泵效率（0-1）
        - Q: 实际流量（m³/h）
        - Q_curve: 特性曲线流量点
        - η_curve: 特性曲线效率点

    Args:
        data: 包含 pump_flow_rate
        params: 参数字典（当前未使用）
        device_id: 设备ID（必需，用于查询特性曲线）

    Returns:
        计算得到的效率数组（0-1）
    """
    Q = data['pump_flow_rate']  # m³/h

    # 创建有效数据掩码
    valid_mask = ~np.isnan(Q) & (Q > 0)

    # 初始化效率数组为NaN
    efficiency = np.full_like(Q, np.nan)

    # 如果没有设备ID，无法查询特性曲线
    if device_id is None:
        logger.warning(
            "EFF_CURVE_V1: device_id is None, cannot query characteristic curves"
        )
        return efficiency

    # 查询设备的效率特性曲线
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT flow_rate, value
                    FROM pump_characteristic_curves
                    WHERE device_id = %s
                      AND curve_type = 'efficiency'
                      AND flow_rate IS NOT NULL
                      AND value IS NOT NULL
                    ORDER BY flow_rate
                """
                cur.execute(query, (device_id,))
                curve_data = cur.fetchall()

        # 如果没有特性曲线数据，返回NaN
        if not curve_data or len(curve_data) < 2:
            logger.warning(
                f"EFF_CURVE_V1: No efficiency curve data for device {device_id}, "
                f"found {len(curve_data) if curve_data else 0} points (need at least 2)"
            )
            return efficiency

        # 提取曲线数据
        Q_curve = np.array([row[0] for row in curve_data], dtype=float)
        eff_curve = np.array([row[1] for row in curve_data], dtype=float)

        # 对有效数据点进行插值
        if np.any(valid_mask):
            # 使用numpy的线性插值
            # 超出范围的值会被外推（使用边界值）
            efficiency[valid_mask] = np.interp(
                Q[valid_mask],
                Q_curve,
                eff_curve,
                left=np.nan,  # 低于最小流量返回NaN
                right=np.nan  # 高于最大流量返回NaN
            )

            # 限制效率范围在 [0, 1]
            efficiency = np.clip(efficiency, 0.0, 1.0)

            logger.debug(
                f"EFF_CURVE_V1: Interpolated efficiency for device {device_id}, "
                f"curve points: {len(Q_curve)}, "
                f"flow range: [{Q_curve.min():.1f}, {Q_curve.max():.1f}] m³/h, "
                f"efficiency range: [{eff_curve.min():.3f}, {eff_curve.max():.3f}]"
            )

    except Exception as e:
        logger.error(
            f"EFF_CURVE_V1: Error querying characteristic curves for device {device_id}: {e}",
            exc_info=True
        )
        return efficiency

    return efficiency


def get_efficiency_curve_info(device_id: int) -> Dict:
    """
    获取设备的效率曲线信息（用于调试和验证）

    Args:
        device_id: 设备ID

    Returns:
        包含曲线信息的字典：
        - has_curve: 是否有曲线数据
        - point_count: 曲线点数
        - flow_range: 流量范围 [min, max]
        - efficiency_range: 效率范围 [min, max]
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT 
                        COUNT(*) as point_count,
                        MIN(flow_rate) as min_flow,
                        MAX(flow_rate) as max_flow,
                        MIN(value) as min_eff,
                        MAX(value) as max_eff
                    FROM pump_characteristic_curves
                    WHERE device_id = %s
                      AND curve_type = 'efficiency'
                      AND flow_rate IS NOT NULL
                      AND value IS NOT NULL
                """
                cur.execute(query, (device_id,))
                row = cur.fetchone()

                if row and row[0] > 0:
                    return {
                        'has_curve': True,
                        'point_count': row[0],
                        'flow_range': [row[1], row[2]],
                        'efficiency_range': [row[3], row[4]]
                    }
                else:
                    return {
                        'has_curve': False,
                        'point_count': 0,
                        'flow_range': None,
                        'efficiency_range': None
                    }

    except Exception as e:
        logger.error(
            f"Error getting efficiency curve info for device {device_id}: {e}",
            exc_info=True
        )
        return {
            'has_curve': False,
            'point_count': 0,
            'flow_range': None,
            'efficiency_range': None,
            'error': str(e)
        }

