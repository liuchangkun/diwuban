"""
日志过滤配置模块（app.core.config.logging_filters）

本模块包含日志过滤相关的配置类定义，包括：
- 级别过滤配置
- 模块过滤配置
- 内容过滤配置
- 频率过滤配置
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class LevelFilterSettings:
    """
    级别过滤配置

    用于配置基于日志级别的过滤规则。

    属性：
        global_level: 全局日志级别
        module_levels: 模块特定的日志级别
        dynamic_adjustment: 是否启用动态调整
        level_hierarchy: 级别层次结构
    """

    global_level: str = "INFO"
    module_levels: Dict[str, str] = field(default_factory=dict)
    dynamic_adjustment: bool = False
    level_hierarchy: List[str] = field(
        default_factory=lambda: ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    )


@dataclass(frozen=True)
class ModuleFilterSettings:
    """
    模块过滤配置

    用于配置基于模块名的过滤规则。

    属性：
        whitelist: 白名单模块列表
        blacklist: 黑名单模块列表
        use_whitelist: 是否使用白名单模式
        pattern_matching: 是否启用模式匹配
        case_sensitive: 是否区分大小写
    """

    whitelist: List[str] = field(default_factory=list)
    blacklist: List[str] = field(default_factory=list)
    use_whitelist: bool = False
    pattern_matching: bool = False
    case_sensitive: bool = True


@dataclass(frozen=True)
class ContentFilterSettings:
    """
    内容过滤配置

    用于配置基于日志内容的过滤规则。

    属性：
        keyword_filters: 关键词过滤列表
        regex_filters: 正则表达式过滤列表
        sensitive_patterns: 敏感信息模式
        max_message_size: 最大消息大小
        truncate_long_messages: 是否截断长消息
    """

    keyword_filters: List[str] = field(default_factory=list)
    regex_filters: List[str] = field(default_factory=list)
    sensitive_patterns: List[str] = field(
        default_factory=lambda: ["password", "token", "secret", "key"]
    )
    max_message_size: int = 10000
    truncate_long_messages: bool = True


@dataclass(frozen=True)
class FrequencyFilterSettings:
    """
    频率过滤配置

    用于配置基于频率的日志过滤规则。

    属性：
        rate_limit_enabled: 是否启用频率限制
        max_messages_per_second: 每秒最大消息数
        burst_limit: 突发限制
        cooldown_period: 冷却期（秒）
        duplicate_detection: 是否启用重复检测
        duplicate_window: 重复检测窗口（秒）
    """

    rate_limit_enabled: bool = False
    max_messages_per_second: float = 100.0
    burst_limit: int = 500
    cooldown_period: int = 60
    duplicate_detection: bool = True
    duplicate_window: int = 60


@dataclass(frozen=True)
class LoggingFiltersSettings:
    """
    日志过滤完整配置

    集成所有日志过滤相关配置，提供统一的配置访问接口。

    属性：
        level: 级别过滤配置
        module: 模块过滤配置
        content: 内容过滤配置
        frequency: 频率过滤配置
    """

    level: LevelFilterSettings = LevelFilterSettings()
    module: ModuleFilterSettings = ModuleFilterSettings()
    content: ContentFilterSettings = ContentFilterSettings()
    frequency: FrequencyFilterSettings = FrequencyFilterSettings()
