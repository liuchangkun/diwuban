"""
日志辅助函数

职责：
- 提供统一的日志记录接口
- 支持 trace_id/span_id 追踪
- 写入文件日志（不再使用 calculation_logs 表）
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from app.core.logging.setup import log_activity


class CalculationLogger:
    """
    计算日志记录器

    职责：
    - 记录计算过程的详细日志
    - 支持分布式追踪（trace_id/span_id）
    - 写入文件日志
    """

    def __init__(self, task_id: str, metric_key: str):
        """
        初始化日志记录器

        Args:
            task_id: 任务ID
            metric_key: 指标键
        """
        self.task_id = task_id
        self.metric_key = metric_key
        self.trace_id = str(uuid.uuid4())
        self.logger = log_activity

    def log_stage(
        self,
        stage: str,
        message: str,
        station_id: Optional[int] = None,
        device_id: Optional[int] = None,
        log_level: str = 'INFO',
        extra_data: Optional[Dict[str, Any]] = None
    ):
        """
        记录阶段日志

        Args:
            stage: 阶段名称（DataLoader, DataFilter, etc.）
            message: 日志消息
            station_id: 泵站ID
            device_id: 设备ID
            log_level: 日志级别
            extra_data: 额外数据
        """
        span_id = str(uuid.uuid4())
        
        # 记录到文件日志
        self.logger(
            f"[{stage}] {message}",
            extra={
                'extra_data': {
                    'task_id': self.task_id,
                    'trace_id': self.trace_id,
                    'span_id': span_id,
                    'metric_key': self.metric_key,
                    'station_id': station_id,
                    'device_id': device_id,
                    'stage': stage,
                    **(extra_data or {})
                }
            }
        )

    def create_child_logger(self, stage: str) -> CalculationLogger:
        """
        创建子日志记录器（用于嵌套阶段）

        Args:
            stage: 子阶段名称

        Returns:
            子日志记录器
        """
        child = CalculationLogger(self.task_id, self.metric_key)
        child.trace_id = self.trace_id  # 继承 trace_id
        return child

