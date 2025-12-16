"""
性能监控器 (app.services.characteristic_curves.shared.performance_monitor)

提供性能指标采集和分析功能。

功能:
- 监控操作耗时、内存使用、成功率
- 统计历史性能趋势
- 支持性能告警阈值检查

优先级: P0
参考文档: 07_辅助模块/02_监控和报告.md
"""

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional

import psutil


@dataclass
class PerformanceMetrics:
    """性能指标数据结构"""

    operation: str
    duration_ms: float
    memory_mb: float
    success: bool
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None


class PerformanceMonitor:
    """性能监控器

    监控特性曲线拟合各阶段的性能指标。
    """

    def __init__(self, max_history: int = 1000):
        """初始化性能监控器

        Args:
            max_history: 最大历史记录数
        """
        self._max_history = max_history
        self._history: Deque[PerformanceMetrics] = deque(maxlen=max_history)
        self._timers: Dict[str, float] = {}
        self._stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'count': 0,
            'success_count': 0,
            'total_duration_ms': 0.0,
            'total_memory_mb': 0.0,
            'max_duration_ms': 0.0,
            'min_duration_ms': float('inf'),
        })
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}")
        self._process = None

        self._logger.info(
            "[性能监控器] 初始化",
            extra={"extra_data": {
                "组件": "PerformanceMonitor",
                "最大历史": max_history
            }}
        )

    def start_timer(self, operation: str) -> None:
        """开始计时

        Args:
            operation: 操作名称
        """
        self._timers[operation] = time.time()

    def stop_timer(
        self,
        operation: str,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None
    ) -> PerformanceMetrics:
        """停止计时并记录性能指标

        Args:
            operation: 操作名称
            success: 是否成功
            details: 详细信息

        Returns:
            PerformanceMetrics: 性能指标
        """
        if operation not in self._timers:
            self._logger.warning(
                f"[性能监控器] 计时器不存在: {operation}",
                extra={"extra_data": {"operation": operation}}
            )
            return None

        # 计算耗时
        duration_ms = (time.time() - self._timers[operation]) * 1000
        del self._timers[operation]

        # 获取内存使用
        memory_mb = self._get_memory_usage()

        # 创建性能指标
        metrics = PerformanceMetrics(
            operation=operation,
            duration_ms=duration_ms,
            memory_mb=memory_mb,
            success=success,
            timestamp=datetime.now(),
            details=details
        )

        # 记录历史
        self._history.append(metrics)

        # 更新统计
        stats = self._stats[operation]
        stats['count'] += 1
        if success:
            stats['success_count'] += 1
        stats['total_duration_ms'] += duration_ms
        stats['total_memory_mb'] += memory_mb
        stats['max_duration_ms'] = max(stats['max_duration_ms'], duration_ms)
        stats['min_duration_ms'] = min(stats['min_duration_ms'], duration_ms)

        return metrics

    def get_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """获取统计信息

        Args:
            operation: 操作名称,不指定则返回所有操作

        Returns:
            Dict: 统计信息
        """
        if operation:
            if operation not in self._stats:
                return {}

            stats = self._stats[operation]
            count = stats['count']

            return {
                'operation': operation,
                'count': count,
                'success_rate': stats['success_count'] / count if count > 0 else 0.0,
                'avg_duration_ms': stats['total_duration_ms'] / count if count > 0 else 0.0,
                'max_duration_ms': stats['max_duration_ms'],
                'min_duration_ms': stats['min_duration_ms'] if stats['min_duration_ms'] != float('inf') else 0.0,
                'avg_memory_mb': stats['total_memory_mb'] / count if count > 0 else 0.0,
            }

        # 返回所有操作的统计
        return {
            op: self.get_stats(op)
            for op in self._stats.keys()
        }

    def get_history(self, limit: int = 100) -> List[PerformanceMetrics]:
        """获取最近的性能记录

        Args:
            limit: 返回数量限制

        Returns:
            List[PerformanceMetrics]: 性能记录列表
        """
        return list(self._history)[-limit:]

    def check_threshold(
        self,
        operation: str,
        duration_threshold_ms: float,
        memory_threshold_mb: float
    ) -> Dict[str, bool]:
        """检查性能阈值

        Args:
            operation: 操作名称
            duration_threshold_ms: 耗时阈值(毫秒)
            memory_threshold_mb: 内存阈值(MB)

        Returns:
            Dict: 检查结果
        """
        stats = self.get_stats(operation)

        if not stats:
            return {
                'duration_ok': True,
                'memory_ok': True,
                'message': f'无{operation}统计数据'
            }

        duration_ok = stats['avg_duration_ms'] <= duration_threshold_ms
        memory_ok = stats['avg_memory_mb'] <= memory_threshold_mb

        result = {
            'duration_ok': duration_ok,
            'memory_ok': memory_ok,
            'avg_duration_ms': stats['avg_duration_ms'],
            'avg_memory_mb': stats['avg_memory_mb'],
        }

        if not duration_ok:
            result['message'] = (
                f"{operation} 平均耗时 {stats['avg_duration_ms']:.2f}ms "
                f"超过阈值 {duration_threshold_ms}ms"
            )
        elif not memory_ok:
            result['message'] = (
                f"{operation} 平均内存 {stats['avg_memory_mb']:.2f}MB "
                f"超过阈值 {memory_threshold_mb}MB"
            )
        else:
            result['message'] = f"{operation} 性能正常"

        return result

    def reset(self, operation: Optional[str] = None) -> None:
        """重置统计数据

        Args:
            operation: 操作名称,不指定则重置所有
        """
        if operation:
            if operation in self._stats:
                del self._stats[operation]
        else:
            self._stats.clear()
            self._history.clear()

    def _get_memory_usage(self) -> float:
        """获取当前内存使用(MB)

        Returns:
            float: 内存使用(MB)
        """
        try:
            if self._process is None:
                self._process = psutil.Process()

            memory_info = self._process.memory_info()
            return memory_info.rss / 1024 / 1024  # 转换为MB
        except Exception as e:
            self._logger.warning(
                f"[性能监控器] 获取内存使用失败: {e}",
                extra={"extra_data": {"error": str(e)}}
            )
            return 0.0
