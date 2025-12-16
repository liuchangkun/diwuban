"""
错误分析和监控模块（app.core.error_analysis）

本模块提供错误分析和监控功能：
- 错误统计和趋势分析
- 错误模式识别
- 故障预测和预警
- 错误报告生成

使用方式：
1. 使用 ErrorAnalyzer 进行错误分析
2. 使用 @error_monitor 装饰器监控函数错误
3. 生成错误报告和趋势分析

设计原则：
- 实时错误监控和统计
- 智能错误模式识别
- 预测性故障分析
- 详细的错误报告
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar

from app.core.exceptions import BaseAppException, ErrorSeverity

# 类型变量定义
F = TypeVar("F", bound=Callable[..., Any])


import logging

_act = logging.getLogger(__name__)


@dataclass
class ErrorRecord:
    """错误记录"""

    timestamp: float
    error_type: str
    error_message: str
    severity: ErrorSeverity
    context: Dict[str, Any]
    function_name: str
    module_name: str
    recovery_action: str
    resolved: bool = False


@dataclass
class ErrorPattern:
    """错误模式"""

    pattern_id: str
    error_types: List[str]
    frequency: int
    time_window: float
    severity_distribution: Dict[str, int]
    common_contexts: Dict[str, Any]
    suggested_actions: List[str]


@dataclass
class ErrorTrends:
    """错误趋势"""

    total_errors: int
    error_rate: float  # 每分钟错误数
    severity_distribution: Dict[str, int]
    top_error_types: List[tuple[str, int]]
    trend_direction: str  # "increasing", "decreasing", "stable"
    prediction: Optional[str] = None


@dataclass
class ErrorReport:
    """错误报告"""

    report_id: str
    generated_at: datetime
    time_range: tuple[datetime, datetime]
    summary: ErrorTrends
    patterns: List[ErrorPattern]
    recommendations: List[str]
    critical_issues: List[ErrorRecord]


class ErrorAnalyzer:
    """错误分析器"""

    def __init__(self, error_analysis_settings=None):
        if error_analysis_settings:
            # 从配置加载参数
            recording_config = error_analysis_settings.recording
            self.max_records = recording_config.max_records
            self.analysis_window = recording_config.analysis_window
            self.cleanup_interval = recording_config.cleanup_interval
            self.auto_cleanup = recording_config.auto_cleanup

            # 模式检测配置
            pattern_config = error_analysis_settings.pattern_detection
            self.min_frequency = pattern_config.min_frequency
            self.pattern_time_window = pattern_config.time_window
            self.similarity_threshold = pattern_config.similarity_threshold
            self.enable_auto_detection = pattern_config.enable_auto_detection

            # 趋势分析配置
            trend_config = error_analysis_settings.trend_analysis
            self.trend_analysis_interval = trend_config.analysis_interval
            self.trend_window = trend_config.trend_window
            self.rate_threshold = trend_config.rate_threshold
            self.enable_prediction = trend_config.enable_prediction
        else:
            # 使用默认值（向后兼容）
            self.max_records = 10000
            self.analysis_window = 3600
            self.cleanup_interval = 300
            self.auto_cleanup = True
            self.min_frequency = 3
            self.pattern_time_window = 1800
            self.similarity_threshold = 0.8
            self.enable_auto_detection = True
            self.trend_analysis_interval = 300
            self.trend_window = 3600
            self.rate_threshold = 0.1
            self.enable_prediction = True

        self.error_records: deque[ErrorRecord] = deque(maxlen=self.max_records)
        self.error_counts = defaultdict(int)
        self.severity_counts = defaultdict(int)
        self.function_error_counts = defaultdict(int)
        self.patterns: List[ErrorPattern] = []
        self._last_analysis_time = 0.0
        self._last_cleanup_time = 0.0

    def record_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        function_name: str = "unknown",
        module_name: str = "unknown",
    ):
        """记录错误"""
        # 提取错误信息
        if isinstance(error, BaseAppException):
            severity = error.severity
            recovery_action = error.recovery_action.value
            error_context = {**context, **error.context}
        else:
            severity = ErrorSeverity.MEDIUM
            recovery_action = "retry"
            error_context = context

        # 创建错误记录
        record = ErrorRecord(
            timestamp=time.time(),
            error_type=type(error).__name__,
            error_message=str(error),
            severity=severity,
            context=error_context,
            function_name=function_name,
            module_name=module_name,
            recovery_action=recovery_action,
        )

        # 添加到记录中
        self.error_records.append(record)

        # 更新统计
        self.error_counts[record.error_type] += 1
        self.severity_counts[severity.value] += 1
        self.function_error_counts[function_name] += 1

        # 略过日志输出
        pass

        # 定期分析错误模式
        current_time = time.time()
        if current_time - self._last_analysis_time > 300:  # 每5分钟分析一次
            self._analyze_patterns()
            self._last_analysis_time = current_time

    def _analyze_patterns(self):
        """分析错误模式"""
        current_time = time.time()
        window_start = current_time - self.analysis_window

        # 获取时间窗口内的错误记录
        recent_errors = [
            record for record in self.error_records if record.timestamp >= window_start
        ]

        if len(recent_errors) < 5:  # 错误数量太少，无法分析模式
            return

        # 按错误类型分组
        error_groups = defaultdict(list)
        for record in recent_errors:
            error_groups[record.error_type].append(record)

        # 识别高频错误模式
        new_patterns = []
        for error_type, records in error_groups.items():
            if len(records) >= 3:  # 至少3次相同错误才认为是模式
                pattern = self._create_pattern(error_type, records)
                new_patterns.append(pattern)

        # 更新模式列表
        self.patterns = new_patterns

        if new_patterns:
            _act.warning(
                "[核心-错误] [错误模式检测]",
                extra={
                    "extra_data": {
                        "pattern_count": len(new_patterns),
                        "patterns": [
                            {
                                "pattern_id": p.pattern_id,
                                "error_types": p.error_types,
                                "frequency": p.frequency,
                                "suggested_actions": p.suggested_actions,
                            }
                            for p in new_patterns[:3]  # 只记录前3个模式
                        ],
                    }
                },
            )

    def _create_pattern(
        self, error_type: str, records: List[ErrorRecord]
    ) -> ErrorPattern:
        """创建错误模式"""
        # 计算严重程度分布
        severity_dist = defaultdict(int)
        for record in records:
            severity_dist[record.severity.value] += 1

        # 提取公共上下文
        common_contexts = {}
        if records:
            first_context = records[0].context
            for key, value in first_context.items():
                if all(record.context.get(key) == value for record in records):
                    common_contexts[key] = value

        # 生成建议动作
        suggested_actions = self._generate_suggestions(error_type, records)

        pattern_id = f"{error_type}_{int(time.time())}"

        return ErrorPattern(
            pattern_id=pattern_id,
            error_types=[error_type],
            frequency=len(records),
            time_window=self.analysis_window,
            severity_distribution=dict(severity_dist),
            common_contexts=common_contexts,
            suggested_actions=suggested_actions,
        )

    def _generate_suggestions(
        self, error_type: str, records: List[ErrorRecord]
    ) -> List[str]:
        """生成错误处理建议"""
        suggestions = []

        # 基于错误类型的建议
        if "Connection" in error_type:
            suggestions.extend(
                ["检查数据库连接配置", "验证网络连接状态", "考虑增加连接池大小"]
            )
        elif "Timeout" in error_type:
            suggestions.extend(["增加超时时间配置", "优化查询性能", "检查系统负载"])
        elif "Pool" in error_type:
            suggestions.extend(
                ["调整连接池配置", "监控连接池使用情况", "考虑连接池重启"]
            )

        # 基于频率的建议
        if len(records) > 10:
            suggestions.append("错误频率过高，建议立即处理")

        # 基于严重程度的建议
        critical_count = sum(1 for r in records if r.severity == ErrorSeverity.CRITICAL)
        if critical_count > 0:
            suggestions.append("包含严重错误，需要紧急处理")

        return suggestions

    def analyze_trends(self, time_window: int = 3600) -> ErrorTrends:
        """分析错误趋势"""
        current_time = time.time()
        window_start = current_time - time_window

        # 获取时间窗口内的错误记录
        recent_errors = [
            record for record in self.error_records if record.timestamp >= window_start
        ]

        total_errors = len(recent_errors)
        error_rate = total_errors / (time_window / 60)  # 每分钟错误数

        # 严重程度分布
        severity_dist = defaultdict(int)
        for record in recent_errors:
            severity_dist[record.severity.value] += 1

        # 错误类型排行
        error_type_counts = defaultdict(int)
        for record in recent_errors:
            error_type_counts[record.error_type] += 1

        top_error_types = sorted(
            error_type_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]

        # 趋势方向分析
        trend_direction = self._analyze_trend_direction(time_window)

        # 预测
        prediction = self._predict_future_errors(recent_errors)

        return ErrorTrends(
            total_errors=total_errors,
            error_rate=error_rate,
            severity_distribution=dict(severity_dist),
            top_error_types=top_error_types,
            trend_direction=trend_direction,
            prediction=prediction,
        )

    def _analyze_trend_direction(self, time_window: int) -> str:
        """分析趋势方向"""
        current_time = time.time()

        # 将时间窗口分为两半
        half_window = time_window // 2
        first_half_start = current_time - time_window
        first_half_end = current_time - half_window
        second_half_start = first_half_end

        # 计算两个时间段的错误数量
        first_half_errors = sum(
            1
            for record in self.error_records
            if first_half_start <= record.timestamp < first_half_end
        )

        second_half_errors = sum(
            1 for record in self.error_records if second_half_start <= record.timestamp
        )

        # 判断趋势
        if second_half_errors > first_half_errors * 1.2:
            return "increasing"
        elif second_half_errors < first_half_errors * 0.8:
            return "decreasing"
        else:
            return "stable"

    def _predict_future_errors(self, recent_errors: List[ErrorRecord]) -> Optional[str]:
        """预测未来错误"""
        if len(recent_errors) < 10:
            return None

        # 简单的预测逻辑
        critical_errors = sum(
            1 for r in recent_errors if r.severity == ErrorSeverity.CRITICAL
        )
        high_errors = sum(1 for r in recent_errors if r.severity == ErrorSeverity.HIGH)

        if critical_errors > 5:
            return "预计将出现系统级故障，建议立即采取措施"
        elif high_errors > 20:
            return "错误率较高，建议加强监控"
        elif len(recent_errors) > 100:
            return "错误数量较多，建议检查系统状态"
        else:
            return "系统运行正常"

    def generate_report(self, time_window: int = 3600) -> ErrorReport:
        """生成错误报告"""
        current_time = datetime.now()
        start_time = current_time - timedelta(seconds=time_window)

        # 分析趋势
        trends = self.analyze_trends(time_window)

        # 获取关键问题
        critical_issues = [
            record
            for record in self.error_records
            if record.severity == ErrorSeverity.CRITICAL
            and record.timestamp >= time.time() - time_window
        ]

        # 生成建议
        recommendations = self._generate_recommendations(trends, critical_issues)

        report_id = f"error_report_{int(time.time())}"

        return ErrorReport(
            report_id=report_id,
            generated_at=current_time,
            time_range=(start_time, current_time),
            summary=trends,
            patterns=self.patterns.copy(),
            recommendations=recommendations,
            critical_issues=critical_issues,
        )

    def _generate_recommendations(
        self, trends: ErrorTrends, critical_issues: List[ErrorRecord]
    ) -> List[str]:
        """生成建议"""
        recommendations = []

        # 基于趋势的建议
        if trends.trend_direction == "increasing":
            recommendations.append("错误趋势上升，建议加强监控和预防措施")

        if trends.error_rate > 10:  # 每分钟超过10个错误
            recommendations.append("错误率过高，建议检查系统负载和配置")

        # 基于严重错误的建议
        if critical_issues:
            recommendations.append(
                f"发现 {len(critical_issues)} 个严重错误，需要立即处理"
            )

        # 基于错误类型的建议
        for error_type, count in trends.top_error_types[:3]:
            if count > 5:
                recommendations.append(f"{error_type} 错误频繁出现，建议重点关注")

        return recommendations

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_records": len(self.error_records),
            "error_counts": dict(self.error_counts),
            "severity_counts": dict(self.severity_counts),
            "function_error_counts": dict(self.function_error_counts),
            "patterns_count": len(self.patterns),
        }


# 全局错误分析器实例
_error_analyzer = ErrorAnalyzer()


def error_monitor(func: F) -> F:
    """
    错误监控装饰器

    自动记录函数执行过程中的错误到错误分析器中。

    使用示例：
        @error_monitor
        def database_operation():
            # 数据库操作
            pass
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # 记录错误到分析器
            context = {
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys()),
                "timestamp": time.time(),
            }

            _error_analyzer.record_error(
                error=e,
                context=context,
                function_name=func.__name__,
                module_name=func.__module__,
            )

            # 重新抛出异常
            raise

    return wrapper  # type: ignore


def initialize_error_analyzer(error_analysis_settings=None):
    """初始化全局错误分析器"""
    global _error_analyzer
    _error_analyzer = ErrorAnalyzer(error_analysis_settings)


def get_error_analyzer() -> ErrorAnalyzer:
    """获取全局错误分析器"""
    return _error_analyzer


def shutdown_error_analyzer():
    """关闭错误分析器"""
    global _error_analyzer
    if _error_analyzer:
        # 生成最终报告
        try:
            final_report = _error_analyzer.generate_report()
        except Exception:
            pass

        # 清理资源
        _error_analyzer.error_records.clear()
        _error_analyzer.error_counts.clear()
        _error_analyzer.severity_counts.clear()
        _error_analyzer.function_error_counts.clear()
        _error_analyzer.patterns.clear()


def generate_error_report(time_window: int = 3600) -> ErrorReport:
    """生成错误报告"""
    return _error_analyzer.generate_report(time_window)


def get_error_trends(time_window: int = 3600) -> ErrorTrends:
    """获取错误趋势"""
    return _error_analyzer.analyze_trends(time_window)
