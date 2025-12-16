"""
method_a: 电机效率法

公式：
P_shaft = P_active × η_motor × η_vfd

参数：
- P_active: 泵有功功率（kW），从 pump_active_power 获取（电网输入功率）
- η_motor: 电机效率（无量纲），从 device_rated_params 获取
- η_vfd: 变频器效率（无量纲），从 device_rated_params 获取

物理意义：
- 电网输入功率经过变频器和电机损失后，传递到泵轴的有效功率
- η_motor × η_vfd < 1，因此 P_shaft < P_active（能量守恒）
- 典型值：η_motor = 0.92, η_vfd = 0.97, η_motor × η_vfd ≈ 0.8924
- 示例：P_active = 100 kW → P_shaft ≈ 89.24 kW
"""

from typing import Dict, Any
import pandas as pd


def calculate(data: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """
    电机效率法计算泵轴功率
    
    Args:
        data: 输入数据（包含 pump_active_power 列）
        params: 参数字典（包含 device_params）
    
    Returns:
        计算结果（包含 pump_shaft_power 列）
    
    公式：
        P_shaft = P_active / (η_motor × η_vfd)
    """
    result = data.copy()
    
    # 获取设备参数
    device_params = params.get('device_params', {})
    
    # 获取当前设备ID
    if 'device_id' not in result.columns or result.empty:
        raise ValueError("数据中缺少 device_id 列或数据为空")
    
    device_id = result['device_id'].iloc[0]
    
    # 获取设备的 eta_motor 和 eta_vfd
    device_param = device_params.get(device_id, {})
    eta_motor = device_param.get('eta_motor')
    eta_vfd = device_param.get('eta_vfd')

    # 验证必需参数
    if eta_motor is None:
        raise ValueError(
            f"设备{device_id}缺少必需参数 'eta_motor'。"
            f"请在 device_rated_params 表中添加该参数。"
        )
    if eta_vfd is None:
        raise ValueError(
            f"设备{device_id}缺少必需参数 'eta_vfd'。"
            f"请在 device_rated_params 表中添加该参数。"
        )
    
    # 计算轴功率
    # P_shaft = P_active × η_motor × η_vfd
    result['pump_shaft_power'] = (
        result['pump_active_power'] * eta_motor * eta_vfd
    )
    
    return result

