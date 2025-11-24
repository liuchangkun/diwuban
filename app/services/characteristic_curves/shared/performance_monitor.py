"""
性能监控器 (app.services.characteristic_curves.shared.performance_monitor)

监控拟合过程的性能指标。

版本: v1.0
更新日期: 2025-12-08
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PerformanceMetrics:
    """性能指标

    Attributes:
        operation: 操作名称
        duration_ms: 执行时间（毫秒）
        memory_mb: 内存使用（MB）
        success: 是否成功
        details: 详细信息
    """

    operation: str
    duration_ms: float
    memory_mb: float = 0.0
    success: bool = True
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "operation": self.operation,
            "duration_ms": self.duration_ms,
            "memory_mb": self.memory_mb,
            "success": self.success,
            "details": self.details,
        }


class PerformanceMonitor:
    """性能监控器

    记录和分析拟合操作的性能。

    Attributes:
        max_history: 最大历史记录数
    """

    def __init__(self, max_history: int = 1000) -> None:
        """初始化性能监控器

        Args:
            max_history: 最大历史记录数
        """
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.max_history = max_history
        self._history: List[PerformanceMetrics] = []
        self._active_timers: Dict[str, float] = {}

    def start_timer(self, operation: str) -> None:
        """开始计时

        Args:
            operation: 操作名称
        """
        self._active_timers[operation] = time.perf_counter()

    def stop_timer(
        self, operation: str, success: bool = True, **details: Any
    ) -> PerformanceMetrics:
        """停止计时并记录

        Args:
            operation: 操作名称
            success: 是否成功
            **details: 额外详细信息

        Returns:
            PerformanceMetrics: 性能指标
        """
        if operation not in self._active_timers:
            raise ValueError(f"未找到操作的计时器: {operation}")

        start_time = self._active_timers.pop(operation)
        duration_ms = (time.perf_counter() - start_time) * 1000

        metrics = PerformanceMetrics(
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            details=details,
        )

        self._record(metrics)
        return metrics

    def record(
        self, operation: str, duration_ms: float, success: bool = True, **details: Any
    ) -> PerformanceMetrics:
        """直接记录性能指标

        Args:
            operation: 操作名称
            duration_ms: 执行时间（毫秒）
            success: 是否成功
            **details: 额外详细信息

        Returns:
            PerformanceMetrics: 性能指标
        """
        metrics = PerformanceMetrics(
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            details=details,
        )
        self._record(metrics)
        return metrics

    def _record(self, metrics: PerformanceMetrics) -> None:
        """内部记录方法"""
        self._history.append(metrics)
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history :]

    def get_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """获取统计信息

        Args:
            operation: 操作名称（如果为None，返回所有统计）

        Returns:
            Dict: 统计信息
        """
        if operation:
            metrics = [m for m in self._history if m.operation == operation]
        else:
            metrics = self._history

        if not metrics:
            return {"count": 0}

        durations = [m.duration_ms for m in metrics]
        success_count = sum(1 for m in metrics if m.success)

        return {
            "count": len(metrics),
            "success_rate": success_count / len(metrics),
            "avg_duration_ms": sum(durations) / len(durations),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations),
        }

    def get_history(self, limit: int = 10) -> List[PerformanceMetrics]:
        """获取历史记录"""
        return self._history[-limit:][::-1]

    def clear(self) -> None:
        """清除历史记录"""
        self._history.clear()
        self._active_timers.clear()

