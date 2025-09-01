"""
日志配置模块（app.core.config.logging）

本模块整合所有日志相关配置，提供统一的日志配置管理。

配置组织结构：
- 基础配置：SQL日志、轮转、格式化、性能、采样
- 高级配置：启动清理、详细日志、关键指标、SQL执行、内部执行
"""

from dataclasses import dataclass

from .logging_base import (
    LoggingSql,
    LoggingRotation,
    LoggingFormatting,
    LoggingPerformance,
    SamplingSettings,
)
from .logging_advanced import (
    StartupCleanupSettings,
    DetailedLoggingSettings,
    KeyMetricsSettings,
    SqlExecutionSettings,
    InternalExecutionSettings,
)
from .logging_output import LoggingOutputSettings
from .logging_filters import LoggingFiltersSettings


@dataclass(frozen=True)
class LoggingSettings:
    """
    日志系统完整配置

    集成所有日志相关配置，提供统一的配置访问接口。

    属性：
        level: 日志级别
        format: 日志格式 ("json" | "text")
        routing: 日志路由 ("by_run" | "by_module")
        queue_handler: 是否启用异步队列处理
        sql: SQL日志配置
        sampling: 采样配置
        rotation: 轮转配置
        formatting: 格式化配置
        performance: 性能配置
        redaction_enable: 是否启用敏感信息脱敏
        retention_days: 日志保留天数
        startup_cleanup: 启动清理配置
        detailed_logging: 详细日志配置
        key_metrics: 关键指标配置
        sql_execution: SQL执行日志配置
        internal_execution: 内部执行日志配置
        output: 输出配置
        filters: 过滤配置
    """

    level: str = "INFO"
    format: str = "json"  # json|text
    routing: str = "by_run"  # by_run|by_module
    queue_handler: bool = True
    sql: LoggingSql = LoggingSql()
    sampling: SamplingSettings = SamplingSettings()
    rotation: LoggingRotation = LoggingRotation()
    formatting: LoggingFormatting = LoggingFormatting()
    performance: LoggingPerformance = LoggingPerformance()
    redaction_enable: bool = False
    retention_days: int = 14
    startup_cleanup: StartupCleanupSettings = StartupCleanupSettings()
    detailed_logging: DetailedLoggingSettings = DetailedLoggingSettings()
    key_metrics: KeyMetricsSettings = KeyMetricsSettings()
    sql_execution: SqlExecutionSettings = SqlExecutionSettings()
    internal_execution: InternalExecutionSettings = InternalExecutionSettings()
    output: LoggingOutputSettings = LoggingOutputSettings()
    filters: LoggingFiltersSettings = LoggingFiltersSettings()
