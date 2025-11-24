"""
方法选择器（MethodSelector）

职责：
- 选择合适的计算方法
- pump_shaft_power 仅有 method_a（电机效率法）
"""

from __future__ import annotations

from typing import Dict, Any, Optional
import pandas as pd
import logging


# 方法配置
METHODS = [
    {
        'id': 'method_a',
        'name': '电机效率法',
        'priority': 100,
        'dependencies': ['pump_active_power'],
        'conditions': {
            'has_device_params': ['eta_motor', 'eta_vfd']
        }
    }
]


class MethodSelector:
    """
    方法选择器
    
    职责：
    - 选择计算方法（pump_shaft_power 仅有 method_a）
    - 检查依赖数据和参数
    """
    
    def __init__(self, params: Dict[str, Any], trace_id: Optional[str] = None):
        """
        初始化方法选择器
        
        Args:
            params: 参数字典（包含 device_params）
            trace_id: 追踪ID（用于日志关联）
        """
        self.params = params
        self.trace_id = trace_id
        self.logger = logging.getLogger(__name__)
    
    def select_method(self, data: pd.DataFrame) -> str:
        """
        选择计算方法
        
        Args:
            data: 过滤后的数据
        
        Returns:
            方法ID（'method_a'）
        
        Raises:
            ValueError: 如果依赖数据或参数缺失
        """
        self.logger.info(
            "[方法选择] 开始选择方法",
            extra={'extra_data': {
                '追踪ID': self.trace_id,
                '可用列': list(data.columns)
            }}
        )
        
        # 检查依赖列
        if 'pump_active_power' not in data.columns:
            raise ValueError("缺少依赖列: pump_active_power")
        
        # 检查设备参数
        device_params = self.params.get('device_params', {})
        if not device_params:
            raise ValueError(
                "缺少设备参数: device_params。"
                "必须在device_rated_params表中配置eta_motor和eta_vfd参数。"
            )
        
        # pump_shaft_power 仅有 method_a
        method_id = 'method_a'
        
        self.logger.info(
            "[方法选择] 方法选择完成",
            extra={'extra_data': {
                '追踪ID': self.trace_id,
                '选择的方法': method_id,
                'method_name': '电机效率法'
            }}
        )
        
        return method_id

