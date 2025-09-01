"""
数据合并配置模块（app.core.config.merge）

本模块包含数据合并相关的配置类定义，包括：
- 时区策略配置
- 分段合并配置
"""

from dataclasses import dataclass
from .ingest import IngestWindow


@dataclass(frozen=True)
class MergeTzPolicy:
    """
    合并时区策略配置
    
    用于配置数据合并过程中的时区处理策略。
    
    属性：
        default_station_tz: 默认站点时区
        allow_missing_tz: 是否允许缺失时区
        missing_tz_policy: 缺失时区处理策略
    """
    default_station_tz: str = "Asia/Shanghai"
    allow_missing_tz: bool = True
    missing_tz_policy: str = "default"  # or "fail"


@dataclass(frozen=True)
class SegmentedMergeSettings:
    """
    分段合并配置
    
    用于配置数据的分段合并策略。
    
    属性：
        enabled: 是否启用分段合并
        granularity: 合并粒度，如 "30m"、"1h"
    """
    enabled: bool = True
    granularity: str = "1h"  # 例如：30m/1h


@dataclass(frozen=True)
class MergeSettings:
    """
    数据合并完整配置
    
    集成所有数据合并相关配置，提供统一的配置访问接口。
    
    属性：
        window: 时间窗口配置
        tz: 时区策略配置
        segmented: 分段合并配置
    """
    window: IngestWindow = IngestWindow(size="7d")
    tz: MergeTzPolicy = MergeTzPolicy()
    segmented: SegmentedMergeSettings = SegmentedMergeSettings()