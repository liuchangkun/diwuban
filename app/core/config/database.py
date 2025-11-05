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
    数据库超时配置（统一超时管理）

    用于配置数据库操作的各种超时时间，所有超时配置统一使用毫秒作为内部存储单位。

    属性：
        connect_timeout_ms: 连接建立超时时间（毫秒）
        statement_timeout_ms: 单个SQL语句执行超时时间（毫秒）
        query_timeout_ms: 复杂查询执行超时时间（毫秒）
        connection_acquire_timeout_ms: 从连接池获取连接的超时时间（毫秒）
        connection_validation_timeout_ms: 连接健康验证的超时时间（毫秒）
        pool_shutdown_timeout_ms: 连接池关闭的超时时间（毫秒）
    """

    # 基础超时配置
    connect_timeout_ms: int = 5000
    statement_timeout_ms: int = 30000
    query_timeout_ms: int = 60000

    # 连接池专用超时配置
    connection_acquire_timeout_ms: int = 10000  # 获取连接超时
    connection_validation_timeout_ms: int = 1000  # 连接验证超时
    pool_shutdown_timeout_ms: int = 30000  # 连接池关闭超时

    def connect_timeout_seconds(self) -> float:
        """获取连接超时时间（秒，浮点数）"""
        return self.connect_timeout_ms / 1000.0

    def statement_timeout_sql(self) -> str:
        """获取设置语句超时的SQL语句"""
        return f"SET statement_timeout TO '{self.statement_timeout_ms}ms'"

    def query_timeout_seconds(self) -> float:
        """获取查询超时时间（秒，浮点数）"""
        return self.query_timeout_ms / 1000.0

    def connection_acquire_timeout_seconds(self) -> float:
        """获取连接获取超时时间（秒，浮点数）"""
        return self.connection_acquire_timeout_ms / 1000.0

    def connection_validation_timeout_seconds(self) -> float:
        """获取连接验证超时时间（秒，浮点数）"""
        return self.connection_validation_timeout_ms / 1000.0

    def pool_shutdown_timeout_seconds(self) -> float:
        """获取连接池关闭超时时间（秒，浮点数）"""
        return self.pool_shutdown_timeout_ms / 1000.0

    def validate(self) -> list[str]:
        """
        验证超时配置的合理性

        返回：
            错误信息列表，空列表表示验证通过
        """
        errors = []

        # 验证基础超时配置
        if self.connect_timeout_ms <= 0:
            errors.append("connect_timeout_ms 必须大于 0")
        elif self.connect_timeout_ms > 300000:  # 5分钟
            errors.append("connect_timeout_ms 不应超过 300000ms (5分钟)")

        if self.statement_timeout_ms <= 0:
            errors.append("statement_timeout_ms 必须大于 0")
        elif self.statement_timeout_ms > 3600000:  # 1小时
            errors.append("statement_timeout_ms 不应超过 3600000ms (1小时)")

        if self.query_timeout_ms <= 0:
            errors.append("query_timeout_ms 必须大于 0")
        elif self.query_timeout_ms > 7200000:  # 2小时
            errors.append("query_timeout_ms 不应超过 7200000ms (2小时)")

        # 验证连接池超时配置
        if self.connection_acquire_timeout_ms <= 0:
            errors.append("connection_acquire_timeout_ms 必须大于 0")
        elif self.connection_acquire_timeout_ms > 60000:  # 1分钟
            errors.append("connection_acquire_timeout_ms 不应超过 60000ms (1分钟)")

        if self.connection_validation_timeout_ms <= 0:
            errors.append("connection_validation_timeout_ms 必须大于 0")
        elif self.connection_validation_timeout_ms > 10000:  # 10秒
            errors.append("connection_validation_timeout_ms 不应超过 10000ms (10秒)")

        if self.pool_shutdown_timeout_ms <= 0:
            errors.append("pool_shutdown_timeout_ms 必须大于 0")
        elif self.pool_shutdown_timeout_ms > 300000:  # 5分钟
            errors.append("pool_shutdown_timeout_ms 不应超过 300000ms (5分钟)")

        # 验证超时配置的逻辑关系
        if self.statement_timeout_ms > self.query_timeout_ms:
            errors.append("statement_timeout_ms 不应大于 query_timeout_ms")

        if self.connection_validation_timeout_ms > self.connection_acquire_timeout_ms:
            errors.append(
                "connection_validation_timeout_ms 不应大于 connection_acquire_timeout_ms"
            )

        return errors

    def to_dict(self) -> dict:
        """
        转换为字典格式，包含毫秒和秒两种单位

        返回：
            包含所有超时配置的字典
        """
        return {
            # 毫秒单位（原始配置）
            "connect_timeout_ms": self.connect_timeout_ms,
            "statement_timeout_ms": self.statement_timeout_ms,
            "query_timeout_ms": self.query_timeout_ms,
            "connection_acquire_timeout_ms": self.connection_acquire_timeout_ms,
            "connection_validation_timeout_ms": self.connection_validation_timeout_ms,
            "pool_shutdown_timeout_ms": self.pool_shutdown_timeout_ms,
            # 秒单位（转换后）
            "connect_timeout_seconds": self.connect_timeout_seconds(),
            "statement_timeout_seconds": self.statement_timeout_ms / 1000.0,
            "query_timeout_seconds": self.query_timeout_seconds(),
            "connection_acquire_timeout_seconds": self.connection_acquire_timeout_seconds(),
            "connection_validation_timeout_seconds": self.connection_validation_timeout_seconds(),
            "pool_shutdown_timeout_seconds": self.pool_shutdown_timeout_seconds(),
            # SQL语句
            "statement_timeout_sql": self.statement_timeout_sql(),
        }


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
    password: str | None = None  # 数据库密码（可选）
    dsn_read: str | None = None
    dsn_write: str | None = None
    pool: DbPoolSettings = DbPoolSettings()
    timeouts: DbTimeoutSettings = DbTimeoutSettings()
    retry: DbRetrySettings = DbRetrySettings()
    staging_unlogged: bool = False
