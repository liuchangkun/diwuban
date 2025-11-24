"""
pump_flow_rate 计算方法模块

提供7种计算方法：
- method_a: 功率×频率分摊
- method_b: 累计流量导数
- method_c: 单泵直读
- method_d: 功率分摊
- method_e: 频率分摊
- method_f: 数据驱动回归
- method_g: 待机状态检测
"""

from app.services.calculation.metrics.pump_flow_rate.methods.method_a import calculate_method_a
from app.services.calculation.metrics.pump_flow_rate.methods.method_b import calculate_method_b
from app.services.calculation.metrics.pump_flow_rate.methods.method_c import calculate_method_c
from app.services.calculation.metrics.pump_flow_rate.methods.method_d import calculate_method_d
from app.services.calculation.metrics.pump_flow_rate.methods.method_e import calculate_method_e
from app.services.calculation.metrics.pump_flow_rate.methods.method_f import calculate_method_f
from app.services.calculation.metrics.pump_flow_rate.methods.method_g import calculate_method_g

__all__ = [
    'calculate_method_a',
    'calculate_method_b',
    'calculate_method_c',
    'calculate_method_d',
    'calculate_method_e',
    'calculate_method_f',
    'calculate_method_g',
]

