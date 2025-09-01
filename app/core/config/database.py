"""
数据库配置模块（app.core.config.database）

本模块包含数据库相关的配置类定义，包括：
- 数据库连接配置
- 连接池配置
- 超时配置
- 重试策略配置
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DbPoolSettings:
    """
    数据库连接池配置

    用于配置数据库连接池的大小和生命周期管理。

    属性：
        min_size: 最小连接数
        max_size: 最大连接数
        max_inactive_connection_lifetime: 非活跃连接生存时间（秒）
    """

    min_size: int = 1
    max_size: int = 10
    max_inactive_connection_lifetime: int = 3600  # 秒


@dataclass(frozen=True)
class DbTimeoutSettings:
    """
    数据库超时配置

    用于配置数据库操作的各种超时时间。

    属性：
        connect_timeout_ms: 连接超时时间（毫秒）
        statement_timeout_ms: 语句执行超时时间（毫秒）
        query_timeout_ms: 查询超时时间（毫秒）
    """

    connect_timeout_ms: int = 5000
    statement_timeout_ms: int = 30000
    query_timeout_ms: int = 60000


@dataclass(frozen=True)
class DbRetrySettings:
    """
    数据库重试策略配置

    用于配置数据库连接失败时的重试策略。

    属性：
        max_retries: 最大重试次数
        retry_delay_ms: 重试延迟时间（毫秒）
        backoff_multiplier: 退避倍数
    """

    max_retries: int = 3
    retry_delay_ms: int = 1000
    backoff_multiplier: float = 2.0


@dataclass(frozen=True)
class DbSettings:
    """
    数据库配置设置

    包含数据库连接、连接池、超时和重试策略的全部配置。

    安全注意事项：
    - 数据库配置仅允许来自 database.yaml，不允许通过 ENV/CLI 覆盖
    - 连接信息不应该在日志中明文输出
    - DSN 优先级：dsn_write > dsn_read > host/name/user 组合

    属性：
        host: 数据库主机地址
        name: 数据库名称
        user: 连接用户名
        dsn_read: 只读连接的完整 DSN（可选）
        dsn_write: 读写连接的完整 DSN（可选）
        pool: 连接池配置
        timeouts: 超时配置
        retry: 重试策略配置
    """

    # 注意：数据库配置仅允许来自 database.yaml，不允许通过 ENV/CLI 覆盖
    host: str = "localhost"  # fallback 默认值，实际使用从 database.yaml 加载
    name: str = (
        "pump_station_optimization"  # fallback 默认值，实际使用从 database.yaml 加载
    )
    user: str = "postgres"  # fallback 默认值，实际使用从 database.yaml 加载
    dsn_read: str | None = None
    dsn_write: str | None = None
    pool: DbPoolSettings = DbPoolSettings()
    timeouts: DbTimeoutSettings = DbTimeoutSettings()
    retry: DbRetrySettings = DbRetrySettings()
