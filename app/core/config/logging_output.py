"""
日志输出配置模块（app.core.config.logging_output）

本模块包含日志输出相关的配置类定义，包括：
- 文件输出配置
- 控制台输出配置
- 网络输出配置
- 队列输出配置
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FileOutputSettings:
    """
    文件输出配置
    
    用于配置日志文件输出的参数。
    
    属性：
        enabled: 是否启用文件输出
        base_path: 日志文件基础路径
        filename_pattern: 文件名模式
        use_date_suffix: 是否使用日期后缀
        create_subdirs: 是否创建子目录
        permissions: 文件权限
    """
    enabled: bool = True
    base_path: str = "logs"
    filename_pattern: str = "app_{date}.log"
    use_date_suffix: bool = True
    create_subdirs: bool = True
    permissions: int = 0o644


@dataclass(frozen=True)
class ConsoleOutputSettings:
    """
    控制台输出配置
    
    用于配置控制台日志输出的参数。
    
    属性：
        enabled: 是否启用控制台输出
        use_colors: 是否使用颜色输出
        show_timestamps: 是否显示时间戳
        show_levels: 是否显示日志级别
        compact_format: 是否使用紧凑格式
    """
    enabled: bool = True
    use_colors: bool = True
    show_timestamps: bool = True
    show_levels: bool = True
    compact_format: bool = False


@dataclass(frozen=True)
class NetworkOutputSettings:
    """
    网络输出配置
    
    用于配置网络日志输出的参数。
    
    属性：
        enabled: 是否启用网络输出
        protocol: 网络协议 (tcp|udp|http)
        host: 目标主机
        port: 目标端口
        timeout: 连接超时时间
        retry_attempts: 重试次数
        buffer_size: 缓冲区大小
    """
    enabled: bool = False
    protocol: str = "tcp"
    host: str = "localhost"
    port: int = 514
    timeout: int = 5
    retry_attempts: int = 3
    buffer_size: int = 8192


@dataclass(frozen=True)
class QueueOutputSettings:
    """
    队列输出配置
    
    用于配置异步队列日志输出的参数。
    
    属性：
        enabled: 是否启用队列输出
        max_size: 队列最大大小
        timeout: 队列操作超时时间
        drop_on_full: 队列满时是否丢弃消息
        batch_size: 批处理大小
        flush_interval: 刷新间隔
    """
    enabled: bool = True
    max_size: int = 10000
    timeout: float = 1.0
    drop_on_full: bool = False
    batch_size: int = 100
    flush_interval: float = 1.0


@dataclass(frozen=True)
class LoggingOutputSettings:
    """
    日志输出完整配置
    
    集成所有日志输出相关配置，提供统一的配置访问接口。
    
    属性：
        file: 文件输出配置
        console: 控制台输出配置
        network: 网络输出配置
        queue: 队列输出配置
    """
    file: FileOutputSettings = FileOutputSettings()
    console: ConsoleOutputSettings = ConsoleOutputSettings()
    network: NetworkOutputSettings = NetworkOutputSettings()
    queue: QueueOutputSettings = QueueOutputSettings()