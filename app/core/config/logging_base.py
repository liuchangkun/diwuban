"""
日志配置基础模块（app.core.config.logging_base）

本模块包含日志系统的基础配置类定义，包括：
- SQL日志配置
- 日志轮转配置
- 日志格式化配置
- 日志性能配置
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LoggingSql:
    """
    SQL日志配置
    
    用于配置SQL语句的日志记录策略。
    
    属性：
        text: SQL文本记录模式 ("full" | "summary" | "none")
        explain: SQL执行计划记录模式 ("always" | "on_error" | "never")
        top_n_slow: 记录最慢的N条SQL语句
    """
    text: str = "full"
    explain: str = "on_error"
    top_n_slow: int = 5


@dataclass(frozen=True)
class LoggingRotation:
    """
    日志轮转配置
    
    用于配置日志文件的轮转策略。
    
    属性：
        max_bytes: 单个日志文件最大大小（字节）
        backup_count: 保留的备份文件数量
        rotation_interval: 轮转间隔时间（秒），0表示按大小轮转
    """
    max_bytes: int = 104_857_600  # 100MB
    backup_count: int = 7
    rotation_interval: int = 86_400  # 秒，0 表示按大小轮转


@dataclass(frozen=True)
class LoggingFormatting:
    """
    日志格式化配置
    
    用于配置日志输出的格式和样式。
    
    属性：
        timestamp_format: 时间戳格式字符串
        max_message_length: 单条日志消息最大长度
        field_order: 日志字段输出顺序
    """
    timestamp_format: str = "%Y-%m-%d %H:%M:%S.%f"
    max_message_length: int = 8192
    field_order: tuple[str, ...] = ("timestamp", "level", "message", "extra")


@dataclass(frozen=True)
class LoggingPerformance:
    """
    日志性能配置
    
    用于配置日志系统的性能优化参数。
    
    属性：
        buffer_size: 日志缓冲区大小
        flush_interval: 缓冲区刷新间隔（秒）
        async_handler_queue_size: 异步日志处理队列大小
    """
    buffer_size: int = 8192
    flush_interval: float = 1.0
    async_handler_queue_size: int = 1000


@dataclass(frozen=True)
class SamplingSettings:
    """
    日志采样配置
    
    用于配置日志的采样策略，减少高频日志的输出量。
    
    属性：
        loop_log_every_n: 循环日志每N次输出一次
        min_interval_sec: 最小日志输出间隔（秒）
        default_rate: 默认采样率（0.0-1.0）
        high_frequency_events: 高频事件采样率表
        burst_limit: 突发日志限制数量
    """
    loop_log_every_n: int = 1000
    min_interval_sec: float = 1.0
    default_rate: float = 1.0
    high_frequency_events: dict[str, float] = field(default_factory=dict)
    burst_limit: int = 100