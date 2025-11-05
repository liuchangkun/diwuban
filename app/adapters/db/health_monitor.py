"""
连接健康监控模块

提供连接健康检查的统计、监控和优化功能
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from threading import Lock


import logging

_act = logging.getLogger(__name__)


@dataclass
class HealthCheckStats:
    """健康检查统计信息"""

    # 检查计数
    total_checks: int = 0
    cached_checks: int = 0  # 使用缓存的检查次数
    lightweight_checks: int = 0  # 轻量级检查次数
    deep_checks: int = 0  # 深度SQL检查次数
    failed_checks: int = 0  # 失败的检查次数

    # 时间统计
    total_check_time: float = 0.0  # 总检查时间（秒）
    deep_check_time: float = 0.0  # 深度检查时间（秒）

    # 缓存效率
    cache_hit_rate: float = 0.0  # 缓存命中率

    # 最近更新时间
    last_updated: float = field(default_factory=time.time)

    def update_cache_hit_rate(self):
        """更新缓存命中率"""
        if self.total_checks > 0:
            self.cache_hit_rate = self.cached_checks / self.total_checks
        else:
            self.cache_hit_rate = 0.0

    def get_average_check_time(self) -> float:
        """获取平均检查时间（毫秒）"""
        if self.total_checks > 0:
            return (self.total_check_time / self.total_checks) * 1000
        return 0.0

    def get_average_deep_check_time(self) -> float:
        """获取平均深度检查时间（毫秒）"""
        if self.deep_checks > 0:
            return (self.deep_check_time / self.deep_checks) * 1000
        return 0.0

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "total_checks": self.total_checks,
            "cached_checks": self.cached_checks,
            "lightweight_checks": self.lightweight_checks,
            "deep_checks": self.deep_checks,
            "failed_checks": self.failed_checks,
            "cache_hit_rate": round(self.cache_hit_rate * 100, 2),  # 百分比
            "average_check_time_ms": round(self.get_average_check_time(), 2),
            "average_deep_check_time_ms": round(self.get_average_deep_check_time(), 2),
            "last_updated": self.last_updated,
        }


class HealthMonitor:
    """连接健康监控器"""

    def __init__(self):
        self._stats = HealthCheckStats()
        self._lock = Lock()
        self._recent_failures: List[Dict] = []  # 最近的失败记录
        self._max_failure_history = 100  # 最大失败历史记录数

    def record_check(
        self,
        check_type: str,
        duration: float,
        success: bool,
        details: Optional[Dict] = None,
    ):
        """记录健康检查结果

        参数：
            check_type: 检查类型 ('cached', 'lightweight', 'deep')
            duration: 检查耗时（秒）
            success: 是否成功
            details: 额外详情
        """
        if not success:
            _act.warning(
                "[核心-健康检查] [检查失败]",
                extra={
                    "extra_data": {
                        "check_type": check_type,
                        "duration_ms": int(duration * 1000),
                    }
                },
            )

        with self._lock:
            self._stats.total_checks += 1
            self._stats.total_check_time += duration

            if check_type == "cached":
                self._stats.cached_checks += 1
            elif check_type == "lightweight":
                self._stats.lightweight_checks += 1
            elif check_type == "deep":
                self._stats.deep_checks += 1
                self._stats.deep_check_time += duration

            if not success:
                self._stats.failed_checks += 1
                # 记录失败详情
                failure_record = {
                    "timestamp": time.time(),
                    "check_type": check_type,
                    "duration": duration,
                    "details": details or {},
                }
                self._recent_failures.append(failure_record)

                # 限制失败历史记录数量
                if len(self._recent_failures) > self._max_failure_history:
                    self._recent_failures = self._recent_failures[
                        -self._max_failure_history :
                    ]

            # 更新统计信息
            self._stats.update_cache_hit_rate()
            self._stats.last_updated = time.time()

    def get_stats(self) -> HealthCheckStats:
        """获取统计信息"""
        with self._lock:
            return self._stats

    def get_recent_failures(self, limit: int = 10) -> List[Dict]:
        """获取最近的失败记录"""
        with self._lock:
            return self._recent_failures[-limit:] if self._recent_failures else []

    def get_health_summary(self) -> Dict:
        """获取健康状况摘要"""
        with self._lock:
            stats_dict = self._stats.to_dict()

            # 计算健康指标
            failure_rate = (
                self._stats.failed_checks / self._stats.total_checks * 100
                if self._stats.total_checks > 0
                else 0
            )

            # 最近5分钟的失败次数
            current_time = time.time()
            recent_failures = [
                f
                for f in self._recent_failures
                if current_time - f["timestamp"] < 300  # 5分钟
            ]

            return {
                "stats": stats_dict,
                "health_indicators": {
                    "failure_rate_percent": round(failure_rate, 2),
                    "recent_failures_5min": len(recent_failures),
                    "cache_efficiency": (
                        "excellent"
                        if self._stats.cache_hit_rate > 0.8
                        else "good" if self._stats.cache_hit_rate > 0.6 else "poor"
                    ),
                    "performance": (
                        "excellent"
                        if self._stats.get_average_check_time() < 1.0
                        else (
                            "good"
                            if self._stats.get_average_check_time() < 5.0
                            else "poor"
                        )
                    ),
                },
                "recent_failures": recent_failures[-5:] if recent_failures else [],
            }

    def reset_stats(self):
        """重置统计信息"""
        with self._lock:
            self._stats = HealthCheckStats()
            self._recent_failures.clear()

    def get_optimization_recommendations(self) -> List[str]:
        """获取优化建议"""
        recommendations = []

        with self._lock:
            # 基于统计数据生成建议
            if self._stats.cache_hit_rate < 0.5:
                recommendations.append("缓存命中率较低，考虑调整缓存策略或检查频率")

            if self._stats.total_checks > 0:
                avg_time = self._stats.get_average_check_time()
                if avg_time > 10.0:  # 超过10ms
                    recommendations.append("健康检查平均耗时较高，考虑优化检查逻辑")

                failure_rate = self._stats.failed_checks / self._stats.total_checks
                if failure_rate > 0.1:  # 失败率超过10%
                    recommendations.append("健康检查失败率较高，检查网络或数据库状态")

            # 检查深度检查比例
            if self._stats.total_checks > 0:
                deep_check_ratio = self._stats.deep_checks / self._stats.total_checks
                if deep_check_ratio > 0.3:  # 深度检查超过30%
                    recommendations.append("深度检查比例较高，考虑优化缓存策略")

        return recommendations


# 全局健康监控器实例
_health_monitor: Optional[HealthMonitor] = None
_monitor_lock = Lock()


def get_health_monitor() -> HealthMonitor:
    """获取全局健康监控器实例"""
    global _health_monitor

    with _monitor_lock:
        if _health_monitor is None:
            _health_monitor = HealthMonitor()
        return _health_monitor


def record_health_check(
    check_type: str, duration: float, success: bool, details: Optional[Dict] = None
):
    """记录健康检查结果的便捷函数"""
    monitor = get_health_monitor()
    monitor.record_check(check_type, duration, success, details)


def get_health_stats() -> Dict:
    """获取健康检查统计信息的便捷函数"""
    monitor = get_health_monitor()
    return monitor.get_health_summary()
