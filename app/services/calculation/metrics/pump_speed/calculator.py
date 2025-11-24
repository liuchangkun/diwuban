"""
计算执行器（Calculator）

职责：
- 根据 method_id 分发到对应的计算方法
- 从 ParameterManager 加载参数
- 执行计算并返回结果
- 日志记录（参数、计算统计）
"""

from __future__ import annotations

from typing import Dict, Any, Optional
import pandas as pd
import logging


class Calculator:
    """
    计算执行器

    职责：
    - 根据 method_id 分发到对应的计算方法
    - 加载参数（从 ParameterManager）
    - 执行计算
    - 日志记录
    """

    def __init__(self, param_manager=None, trace_id: Optional[str] = None):
        """
        初始化计算器

        Args:
            param_manager: 参数管理器（可选，用于加载参数）
            trace_id: 追踪ID（用于日志关联）
        """
        self.param_manager = param_manager
        self.trace_id = trace_id
        self.logger = logging.getLogger(__name__)

        # 导入3个计算方法
        from .methods import method_a, method_b, method_c

        # 方法映射字典
        self.methods = {
            'method_a': method_a.calculate_method_a,
            'method_b': method_b.calculate_method_b,
            'method_c': method_c.calculate_method_c
        }

    def calculate(
        self,
        data: pd.DataFrame,
        method_id: str,
        params: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        执行计算

        Args:
            data: 过滤后的数据
            method_id: 方法ID（method_a, method_b, method_c）
            params: 参数字典（可选，如果不提供则从 ParameterManager 加载）

        Returns:
            计算结果（包含 pump_speed 列）

        Raises:
            ValueError: 如果 method_id 不存在
        """
        # 验证 method_id
        if method_id not in self.methods:
            error_msg = f"未知的方法ID: {method_id}，可用方法: {list(self.methods.keys())}"
            self.logger.error(
                f"[计算执行] 失败: {error_msg}",
                extra={'extra_data': {'追踪ID': self.trace_id, '方法ID': method_id}}
            )
            raise ValueError(error_msg)

        # 加载参数（如果未提供）
        if params is None and self.param_manager is not None:
            params = self.param_manager.get_parameters(
                metric_key='pump_speed',
                method_id=method_id
            )
        elif params is None:
            params = {}  # 使用默认参数

        self.logger.info(
            "[计算执行] 开始计算",
            extra={'extra_data': {
                '追踪ID': self.trace_id,
                '方法ID': method_id,
                '参数': params,
                '数据行数': len(data)
            }}
        )

        # 执行计算
        import time
        calc_start = time.time()

        result = self.methods[method_id](data, params)

        calc_duration = time.time() - calc_start

        self.logger.info(
            "[计算执行] 计算完成",
            extra={'extra_data': {
                '追踪ID': self.trace_id,
                '方法ID': method_id,
                '结果行数': len(result),
                '耗时（毫秒）': round(calc_duration * 1000, 2)
            }}
        )

        return result

