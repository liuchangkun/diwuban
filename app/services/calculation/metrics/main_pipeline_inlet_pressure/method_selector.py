"""
方法选择器（MethodSelector）

职责：
- 根据数据可用性选择最优计算方法
- 检查依赖指标是否存在
- 检查参数是否满足条件
- 返回选中的方法ID和优先级
"""

from __future__ import annotations

from typing import Dict, Any, Optional, Tuple
import pandas as pd
import logging


class MethodSelector:
    """
    方法选择器
    
    职责：
    - 根据数据可用性和参数配置选择最优计算方法
    - 优先级：数字越小优先级越高（90 > 100）
    """
    
    # 方法配置（按优先级从高到低排序）
    METHODS = [
        {
            'id': 'PIN_COEF_V1',
            'priority': 90,  # 优先级更高
            'dependencies': ['pool_liquid_level'],
            'conditions': {
                'calibration_quality': ['medium', 'high']
            }
        },
        {
            'id': 'method_b',
            'priority': 100,  # 优先级较低
            'dependencies': ['pool_liquid_level'],
            'conditions': {}
        }
    ]
    
    def __init__(self, params: Dict[str, Any] = None, trace_id: str = None):
        """
        初始化方法选择器
        
        Args:
            params: 参数字典（包含设备参数和计算参数）
            trace_id: 追踪ID（用于日志关联）
        """
        self.logger = logging.getLogger(__name__)
        self.trace_id = trace_id
        self.params = params or {}
    
    def select_method(self, data: pd.DataFrame) -> Optional[Tuple[str, int]]:
        """
        选择计算方法
        
        Args:
            data: 输入数据
        
        Returns:
            (method_id, priority) 或 None（无可用方法）
        """
        if data.empty:
            self.logger.warning(
                "[方法选择] 输入数据为空，无法选择方法",
                extra={'extra_data': {'追踪ID': self.trace_id}}
            )
            return None
        
        self.logger.info(
            "[方法选择] 开始选择计算方法",
            extra={'extra_data': {
                '追踪ID': self.trace_id,
                'data_columns': list(data.columns),
                'data_count': len(data)
            }}
        )
        
        # 按优先级遍历方法
        for method in self.METHODS:
            method_id = method['id']
            priority = method['priority']
            dependencies = method['dependencies']
            conditions = method['conditions']
            
            # 检查依赖指标
            missing_deps = [dep for dep in dependencies if dep not in data.columns]
            if missing_deps:
                self.logger.debug(
                    f"[方法选择] 方法 {method_id} 不可用：缺少依赖指标 {missing_deps}",
                    extra={'extra_data': {'追踪ID': self.trace_id}}
                )
                continue
            
            # 检查条件
            conditions_met = True
            for param_key, expected_values in conditions.items():
                actual_value = self.params.get(param_key)
                if actual_value not in expected_values:
                    self.logger.debug(
                        f"[方法选择] 方法 {method_id} 不可用：条件不满足 {param_key}={actual_value}, 期望{expected_values}",
                        extra={'extra_data': {'追踪ID': self.trace_id}}
                    )
                    conditions_met = False
                    break
            
            if not conditions_met:
                continue
            
            # 找到可用方法
            self.logger.info(
                f"[方法选择] 选择方法: {method_id} (优先级={priority})",
                extra={'extra_data': {'追踪ID': self.trace_id}}
            )
            return (method_id, priority)
        
        # 无可用方法
        self.logger.warning(
            "[方法选择] 无可用方法",
            extra={'extra_data': {'追踪ID': self.trace_id}}
        )
        return None

