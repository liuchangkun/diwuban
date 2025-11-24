"""
计算执行器（Calculator）

职责：
- 执行选定的计算方法
- 调用对应的方法模块
- 返回计算结果
"""

from __future__ import annotations

from typing import Dict, Any, Optional
import pandas as pd
import logging


class Calculator:
    """
    计算执行器

    职责：
    - 根据方法ID调用对应的计算方法
    - 传递参数给计算方法
    - 返回计算结果
    """

    def __init__(self, params: Dict[str, Any], trace_id: Optional[str] = None):
        """
        初始化计算执行器

        Args:
            params: 参数字典
            trace_id: 追踪ID（用于日志关联）
        """
        self.logger = logging.getLogger(__name__)
        self.trace_id = trace_id
        self.params = params

    def calculate(self, data: pd.DataFrame, method_id: str) -> pd.DataFrame:
        """
        执行计算

        Args:
            data: 过滤后的数据
            method_id: 方法ID（method_a 或 method_b）

        Returns:
            计算结果（包含 pump_torque 列）

        Raises:
            ValueError: 如果方法ID无效
        """
        self.logger.info(
            "[计算执行] 开始计算",
            extra={'extra_data': {
                'trace_id': self.trace_id,
                'method_id': method_id,
                'data_rows': len(data)
            }}
        )

        import time
        calc_start = time.time()

        # 根据方法ID调用对应的计算方法
        if method_id == 'method_a':
            from .methods import method_a
            result = method_a.calculate(data, self.params)
        elif method_id == 'method_b':
            from .methods import method_b
            result = method_b.calculate(data, self.params)
        else:
            self.logger.error(
                f"[计算执行] 无效的方法ID: {method_id}",
                extra={'extra_data': {'trace_id': self.trace_id}}
            )
            raise ValueError(f"无效的方法ID: {method_id}")

        calc_duration = time.time() - calc_start

        # 添加 method_id 列
        result['method_id'] = method_id

        self.logger.info(
            "[计算执行] 计算完成",
            extra={'extra_data': {
                'trace_id': self.trace_id,
                'method_id': method_id,
                'result_rows': len(result),
                'calc_duration_ms': round(calc_duration * 1000, 2),
                'avg_torque': round(result['pump_torque'].mean(), 2) if len(result) > 0 else 0,
                'min_torque': round(result['pump_torque'].min(), 2) if len(result) > 0 else 0,
                'max_torque': round(result['pump_torque'].max(), 2) if len(result) > 0 else 0
            }}
        )

        return result

