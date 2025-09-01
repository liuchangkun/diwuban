from __future__ import annotations

"""
配置加载（app.core.config.loader）

本模块负责应用程序的配置管理，提供统一的配置加载和验证机制：

核心功能：
- Settings：应用全局配置（db/ingest/merge/logging）
- load_settings：按目录优先级与 YAML 合并规则加载配置，且强制 ingest.base_dir = data
- load_settings_with_sources：提供配置来源追踪的加载函数

配置优先级：
1. CLI 参数 > 环境变量 > YAML 文件 > 默认值
2. 数据库配置仅允许来自 database.yaml，不允许通过 ENV/CLI 覆盖
3. 部分 ingest 配置支持环境变量覆盖（见白名单）

配置文件结构：
- configs/database.yaml：数据库连接和池配置
- configs/logging.yaml：日志格式、级别和路由配置
- configs/ingest.yaml：数据导入和处理配置

安全注意事项：
- YAML 使用安全加载（yaml.safe_load）
- 数据库连接信息严格限制在 YAML 文件中
- 避免在日志中输出敏感配置信息

使用示例：
    from pathlib import Path
    from app.core.config.loader import load_settings
    
    # 加载配置
    settings = load_settings(Path("configs"))
    
    # 访问配置项
    print(f"数据库主机: {settings.db.host}")
    print(f"导入工作线程: {settings.ingest.workers}")
    print(f"日志级别: {settings.logging.level}")

注意事项：
- 修改配置字段需同步更新 docs/配置说明.md
- logging 路由与格式需与 adapters.logging.init 对齐
- 环境变量支持仅限白名单字段，见 ENV 覆盖部分
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml  # type: ignore[import-untyped]


@dataclass(frozen=True)
class IngestWindow:
    """
    数据导入时间窗口配置
    
    用于定义数据导入的时间范围，支持相对时间（如 "7d"）和绝对时间。
    
    属性：
        size: 相对时间窗口大小，如 "7d"、"1h"、"30m"
        start: 绝对开始时间，ISO 格式
        end: 绝对结束时间，ISO 格式
    """
    size: str | None = None  # e.g. "7d"
    start: str | None = None
    end: str | None = None


@dataclass(frozen=True)
class MergeTzPolicy:
    default_station_tz: str = "Asia/Shanghai"
    allow_missing_tz: bool = True
    missing_tz_policy: str = "default"  # or "fail"


@dataclass(frozen=True)
class CsvSettings:
    delimiter: str = ","
    encoding: str = "utf-8"
    quote_char: str = '"'
    escape_char: str = "\\"
    allow_bom: bool = True


@dataclass(frozen=True)
class BatchSettingsExt:
    size: int = 50_000
    max_memory_mb: int = 256
    parallel_batches: int = 2


@dataclass(frozen=True)
class ErrorHandlingSettings:
    max_errors_per_file: int = 100
    error_threshold_percent: float = 5.0
    continue_on_error: bool = True


@dataclass(frozen=True)
class WebServerSettings:
    """
    Web服务器配置
    
    用于配置FastAPI应用程序的运行参数。
    
    属性：
        host: 服务器绑定地址
        port: 服务器端口
        reload: 开发模式下是否启用热重载
        workers: 生产环境下的工作进程数
    """
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = True
    workers: int = 1


@dataclass(frozen=True)
class WebApiSettings:
    """
    Web API配置
    
    用于配置FastAPI应用程序的API相关设置。
    
    属性：
        title: API标题
        description: API描述
        version: API版本
        docs_url: Swagger文档路径
        redoc_url: ReDoc文档路径
    """
    title: str = "Pump Station Optimization API"
    description: str = "泵站运行数据优化系统 API"
    version: str = "1.0.0"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"


@dataclass(frozen=True)
class WebAppSettings:
    """
    Web应用配置
    
    用于配置应用程序的运行模式和行为。
    
    属性：
        debug: 调试模式
        log_requests: 是否记录HTTP请求日志
        cors_enabled: 是否启用CORS
        cors_origins: 允许的跨域来源
    """
    debug: bool = False
    log_requests: bool = True
    cors_enabled: bool = False
    cors_origins: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WebPerformanceSettings:
    """
    Web性能配置
    
    用于配置应用程序的性能相关参数。
    
    属性：
        request_timeout: 请求超时时间（秒）
        max_request_size: 最大请求大小（字节）
        keepalive_timeout: Keep-Alive超时时间（秒）
    """
    request_timeout: int = 30
    max_request_size: int = 16777216  # 16MB
    keepalive_timeout: int = 65


@dataclass(frozen=True)
class WebSettings:
    """
    Web服务完整配置
    
    集成所有Web相关配置，提供统一的配置访问接口。
    
    属性：
        server: 服务器配置
        api: API配置
        app: 应用配置
        performance: 性能配置
    """
    server: WebServerSettings = WebServerSettings()
    api: WebApiSettings = WebApiSettings()
    app: WebAppSettings = WebAppSettings()
    performance: WebPerformanceSettings = WebPerformanceSettings()


@dataclass(frozen=True)
class SystemDirectoriesSettings:
    """
    系统目录配置
    
    用于配置系统级别的目录路径。
    
    属性：
        data: 数据文件目录
        logs: 日志文件目录
        configs: 配置文件目录
        temp: 临时文件目录
        backup: 备份文件目录
    """
    data: str = "data"
    logs: str = "logs"
    configs: str = "configs"
    temp: str = "temp"
    backup: str = "backup"


@dataclass(frozen=True)
class SystemTimezoneSettings:
    """
    系统时区配置
    
    用于配置系统级别的时区设置。
    
    属性：
        default: 默认时区
        storage: 数据库存储时区
        display: 显示时区
    """
    default: str = "Asia/Shanghai"
    storage: str = "UTC"
    display: str = "Asia/Shanghai"


@dataclass(frozen=True)
class SystemGeneralSettings:
    """
    系统通用配置
    
    用于配置系统级别的通用设置。
    
    属性：
        encoding: 默认文件编码
        locale: 系统语言环境
        max_workers: 系统级别默认最大工作线程数
    """
    encoding: str = "utf-8"
    locale: str = "zh_CN.UTF-8"
    max_workers: int = 4


@dataclass(frozen=True)
class SystemSettings:
    """
    系统完整配置
    
    集成所有系统级别配置，提供统一的配置访问接口。
    
    属性：
        directories: 目录配置
        timezone: 时区配置
        general: 通用配置
    """
    directories: SystemDirectoriesSettings = SystemDirectoriesSettings()
    timezone: SystemTimezoneSettings = SystemTimezoneSettings()
    general: SystemGeneralSettings = SystemGeneralSettings()


@dataclass(frozen=True)
class DefaultPathSettings:
    """
    默认文件路径配置
    
    用于指定各种配置文件的默认路径，支持从配置文件中读取默认值。
    
    属性：
        mapping_file: data_mapping.json 默认路径
        dim_metric_config: dim_metric_config.json 默认路径
    """
    mapping_file: str = "config/data_mapping.v2.json"
    dim_metric_config: str = "config/dim_metric_config.json"


@dataclass(frozen=True)
class DefaultWindowSettings:
    """
    默认时间窗口配置
    
    用于指定数据处理的默认时间窗口，支持全量数据处理模式。
    
    属性：
        process_all_data: 是否处理全量数据（忽略时间窗口限制）
        start_utc: 默认开始时间（UTC）
        end_utc: 默认结束时间（UTC）
    """
    process_all_data: bool = True
    start_utc: str = "2025-02-27T18:00:00Z"
    end_utc: str = "2025-02-27T19:59:59Z"


@dataclass(frozen=True)
class BackpressureThresholds:
    p95_ms: int = 2000
    fail_rate: float = 0.01
    min_batch: int = 1000
    min_workers: int = 1


@dataclass(frozen=True)
class IngestBackpressure:
    thresholds: BackpressureThresholds = BackpressureThresholds()


@dataclass(frozen=True)
class IngestPerformance:
    read_buffer_size: int = 65_536
    write_buffer_size: int = 65_536
    connection_pool_size: int = 5


@dataclass(frozen=True)
class IngestSettings:
    base_dir: str = "data"
    workers: int = 6
    commit_interval: int = 1_000_000
    p95_window: int = 20
    enhanced_source_hint: bool = True
    batch_id_mode: str = "run_id"
    site_timezone: str = "Asia/Shanghai"
    csv: CsvSettings = CsvSettings()
    batch: BatchSettingsExt = BatchSettingsExt()
    error_handling: ErrorHandlingSettings = ErrorHandlingSettings()
    performance: IngestPerformance = IngestPerformance()
    backpressure: IngestBackpressure = IngestBackpressure()
    default_paths: DefaultPathSettings = DefaultPathSettings()
    default_window: DefaultWindowSettings = DefaultWindowSettings()


@dataclass(frozen=True)
class SegmentedMergeSettings:
    enabled: bool = True
    granularity: str = "1h"  # 例如：30m/1h


@dataclass(frozen=True)
class MergeSettings:
    window: IngestWindow = IngestWindow(size="7d")
    tz: MergeTzPolicy = MergeTzPolicy()
    segmented: SegmentedMergeSettings = SegmentedMergeSettings()


@dataclass(frozen=True)
class DbPoolSettings:
    min_size: int = 1
    max_size: int = 10
    max_inactive_connection_lifetime: int = 3600  # 秒


@dataclass(frozen=True)
class DbTimeoutSettings:
    connect_timeout_ms: int = 5000
    statement_timeout_ms: int = 30000
    query_timeout_ms: int = 60000


@dataclass(frozen=True)
class DbRetrySettings:
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
    host: str = "localhost"
    name: str = "pump_station_optimization"
    user: str = "postgres"
    dsn_read: str | None = None
    dsn_write: str | None = None
    pool: DbPoolSettings = DbPoolSettings()
    timeouts: DbTimeoutSettings = DbTimeoutSettings()
    retry: DbRetrySettings = DbRetrySettings()


@dataclass(frozen=True)
class LoggingSql:
    text: str = "full"
    explain: str = "on_error"
    top_n_slow: int = 5


@dataclass(frozen=True)
class LoggingRotation:
    max_bytes: int = 104_857_600  # 100MB
    backup_count: int = 7
    rotation_interval: int = 86_400  # 秒，0 表示按大小轮转


@dataclass(frozen=True)
class LoggingFormatting:
    timestamp_format: str = "%Y-%m-%d %H:%M:%S.%f"
    max_message_length: int = 8192
    field_order: tuple[str, ...] = ("timestamp", "level", "message", "extra")


@dataclass(frozen=True)
class LoggingPerformance:
    buffer_size: int = 8192
    flush_interval: float = 1.0
    async_handler_queue_size: int = 1000


@dataclass(frozen=True)
class StartupCleanupSettings:
    """
    启动清理配置
    
    用于控制程序启动时的清理行为，确保干净的运行环境。
    
    属性：
        clear_logs: 启动时清空logs目录
        clear_database: 启动时清空数据库
        logs_backup_count: 清理前保留的日志备份数
        confirm_clear: 是否需要确认清理操作
    """
    clear_logs: bool = True
    clear_database: bool = True
    logs_backup_count: int = 3
    confirm_clear: bool = False


@dataclass(frozen=True)
class DetailedLoggingSettings:
    """
    详细日志记录配置
    
    用于控制日志记录的详细程度，支持函数级别的日志跟踪。
    
    属性：
        enable_function_entry: 记录函数进入
        enable_function_exit: 记录函数退出
        enable_parameter_logging: 记录函数参数
        enable_context_logging: 记录上下文信息
        enable_business_logging: 记录业务逻辑
        enable_progress_logging: 记录进度信息
        enable_performance_logging: 记录性能指标
        enable_error_details: 记录详细错误信息
        enable_internal_steps: 记录函数内部执行步骤
        enable_condition_branches: 记录条件分支执行
        enable_loop_iterations: 记录循环迭代过程
        enable_intermediate_results: 记录中间结果
        enable_data_validation: 记录数据验证过程
        enable_resource_usage: 记录资源使用情况
        enable_timing_details: 记录详细时间信息
        internal_steps_interval: 内部步骤日志输出间隔（秒）
        loop_log_interval: 循环日志输出间隔（次数）
    """
    enable_function_entry: bool = True
    enable_function_exit: bool = True
    enable_parameter_logging: bool = True
    enable_context_logging: bool = True
    enable_business_logging: bool = True
    enable_progress_logging: bool = True
    enable_performance_logging: bool = True
    enable_error_details: bool = True
    enable_internal_steps: bool = True
    enable_condition_branches: bool = True
    enable_loop_iterations: bool = True
    enable_intermediate_results: bool = True
    enable_data_validation: bool = True
    enable_resource_usage: bool = True
    enable_timing_details: bool = True
    internal_steps_interval: int = 10
    loop_log_interval: int = 100


@dataclass(frozen=True)
class KeyMetricsSettings:
    """
    关键信息日志配置
    
    用于控制关键业务指标的日志记录，包括文件处理、数据统计等。
    
    属性：
        enable_file_count: 记录文件数量
        enable_data_time_range: 记录数据时间范围
        enable_processing_progress: 记录处理进度
        enable_merge_statistics: 记录合并统计
        enable_performance_metrics: 记录性能指标
        enable_memory_usage: 记录内存使用
        enable_database_stats: 记录数据库统计
        enable_file_size_info: 记录文件大小信息
        enable_throughput_metrics: 记录吞吐量指标
        enable_error_statistics: 记录错误统计
        enable_quality_metrics: 记录数据质量指标
        enable_pipeline_stages: 记录管道阶段信息
        enable_batch_statistics: 记录批处理统计
        enable_resource_consumption: 记录资源消耗
        enable_data_distribution: 记录数据分布信息
        progress_report_interval: 进度报告间隔（行数）
        metrics_summary_interval: 指标汇总间隔（秒）
    """
    enable_file_count: bool = True
    enable_data_time_range: bool = True
    enable_processing_progress: bool = True
    enable_merge_statistics: bool = True
    enable_performance_metrics: bool = True
    enable_memory_usage: bool = True
    enable_database_stats: bool = True
    enable_file_size_info: bool = True
    enable_throughput_metrics: bool = True
    enable_error_statistics: bool = True
    enable_quality_metrics: bool = True
    enable_pipeline_stages: bool = True
    enable_batch_statistics: bool = True
    enable_resource_consumption: bool = True
    enable_data_distribution: bool = True
    progress_report_interval: int = 1000
    metrics_summary_interval: int = 300


@dataclass(frozen=True)
class SqlExecutionSettings:
    """
    SQL执行日志配置
    
    用于控制SQL语句执行的详细日志记录。
    
    属性：
        enable_statement_logging: 记录完整SQL语句
        enable_execution_metrics: 记录执行指标
        enable_parameter_logging: 记录SQL参数
        enable_result_summary: 记录结果摘要
        enable_slow_query_detection: 启用慢查询检测
        slow_query_threshold_ms: 慢查询阈值（毫秒）
        max_sql_length: SQL语句最大记录长度
        sensitive_fields: 敏感字段列表
    """
    enable_statement_logging: bool = True
    enable_execution_metrics: bool = True
    enable_parameter_logging: bool = True
    enable_result_summary: bool = True
    enable_slow_query_detection: bool = True
    slow_query_threshold_ms: int = 1000
    max_sql_length: int = 2000
    sensitive_fields: tuple[str, ...] = ("password", "token", "secret", "key")


@dataclass(frozen=True)
class InternalExecutionSettings:
    """
    函数内部执行过程配置
    
    用于控制函数内部执行步骤的详细日志记录。
    
    属性：
        enable_step_logging: 启用步骤日志
        enable_checkpoint_logging: 启用检查点日志
        enable_branch_logging: 启用分支日志
        enable_iteration_logging: 启用迭代日志
        enable_validation_logging: 启用验证日志
        enable_transformation_logging: 启用转换日志
        step_detail_level: 步骤详细级别（low/medium/high）
        iteration_log_frequency: 迭代日志频率（每多X次记录一次）
        checkpoint_auto_interval: 自动检查点间隔（秒）
    """
    enable_step_logging: bool = True
    enable_checkpoint_logging: bool = True
    enable_branch_logging: bool = True
    enable_iteration_logging: bool = True
    enable_validation_logging: bool = True
    enable_transformation_logging: bool = True
    step_detail_level: str = "medium"
    iteration_log_frequency: int = 100
    checkpoint_auto_interval: int = 30


@dataclass(frozen=True)
class LoggingPerformance:
    buffer_size: int = 8192
    flush_interval: float = 1.0
    async_handler_queue_size: int = 1000


@dataclass(frozen=True)
class SamplingSettings:
    loop_log_every_n: int = 1000
    min_interval_sec: float = 1.0
    default_rate: float = 1.0
    high_frequency_events: dict[str, float] = field(
        default_factory=dict
    )  # 事件采样率表
    burst_limit: int = 100


@dataclass(frozen=True)
class LoggingSettings:
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


@dataclass(frozen=True)
class Settings:
    """
    应用程序主配置类
    
    集成所有子系统的配置，提供统一的配置访问接口。
    所有配置对象都是 frozen dataclass，确保配置的不可变性。
    
    配置组织结构：
    - db: 数据库连接和池配置
    - ingest: 数据导入和处理配置
    - merge: 数据合并和对齐配置
    - logging: 日志系统配置
    
    使用示例：
        settings = load_settings(Path("configs"))
        
        # 访问数据库配置
        db_host = settings.db.host
        pool_size = settings.db.pool.max_size
        
        # 访问导入配置
        workers = settings.ingest.workers
        batch_size = settings.ingest.batch.size
        
        # 访问日志配置
        log_level = settings.logging.level
        log_format = settings.logging.format
    """
    db: DbSettings = DbSettings()
    ingest: IngestSettings = IngestSettings()
    merge: MergeSettings = MergeSettings()
    logging: LoggingSettings = LoggingSettings()


def _first_existing_dir(config_dir: Path) -> Path:
    """返回第一个存在的配置目录（优先级：传入 → ./configs → ./config）。"""
    for d in [config_dir, Path("configs"), Path("config")]:
        if d.exists() and d.is_dir():
            return d
    return config_dir


def load_settings(config_dir: Path) -> Settings:
    """加载配置（强制 ingest.base_dir 固定为 data）。

    - 目录优先级：传入 config_dir → ./configs → ./config
    - 支持文件：ingest.yaml、logging.yaml、database.yaml
    - 合并策略：ingest 支持 CLI/ENV > YAML > 默认；db/logging 仅 YAML > 默认；仅白名单字段；不允许覆盖 ingest.base_dir
    """
    cfg = Settings()

    def _first_existing_dir_compat() -> Path:
        # 兼容旧实现内部函数引用
        return _first_existing_dir(config_dir)

    cdir = _first_existing_dir(config_dir)
    ingest_path = cdir / "ingest.yaml"
    logging_path = cdir / "logging.yaml"
    database_path = cdir / "database.yaml"

    data: dict = {}
    if ingest_path.exists():
        data.setdefault("ingest", {})
        with ingest_path.open("r", encoding="utf-8") as f:
            data["ingest"] = yaml.safe_load(f) or {}
    if logging_path.exists():
        data.setdefault("logging", {})
        with logging_path.open("r", encoding="utf-8") as f:
            data["logging"] = yaml.safe_load(f) or {}
    if database_path.exists():
        data.setdefault("db", {})
        with database_path.open("r", encoding="utf-8") as f:
            data["db"] = yaml.safe_load(f) or {}

    # 合并：仅合并允许的键；ingest.base_dir 强制为 data
    db = data.get("db", {})
    ingest = data.get("ingest", {})
    merge = data.get("merge", {})
    logging_cfg = data.get("logging", {})

    cfg = Settings(
        db=DbSettings(
            # 严格按 YAML 加载，不读取 ENV/CLI
            host=str(db.get("host", cfg.db.host)),
            name=str(db.get("name", cfg.db.name)),
            user=str(db.get("user", cfg.db.user)),
            dsn_read=db.get("dsn_read", cfg.db.dsn_read),
            dsn_write=db.get("dsn_write", cfg.db.dsn_write),
            pool=DbPoolSettings(
                min_size=int(
                    ((db.get("pool", {}) or {}).get("min_size", cfg.db.pool.min_size))
                ),
                max_size=int(
                    ((db.get("pool", {}) or {}).get("max_size", cfg.db.pool.max_size))
                ),
                max_inactive_connection_lifetime=int(
                    (
                        (db.get("pool", {}) or {}).get(
                            "max_inactive_connection_lifetime",
                            cfg.db.pool.max_inactive_connection_lifetime,
                        )
                    ),
                ),
            ),
            timeouts=DbTimeoutSettings(
                connect_timeout_ms=int(
                    (db.get("timeouts", {}) or {}).get(
                        "connect_timeout_ms", cfg.db.timeouts.connect_timeout_ms
                    )
                ),
                statement_timeout_ms=int(
                    (db.get("timeouts", {}) or {}).get(
                        "statement_timeout_ms", cfg.db.timeouts.statement_timeout_ms
                    )
                ),
                query_timeout_ms=int(
                    (db.get("timeouts", {}) or {}).get(
                        "query_timeout_ms", cfg.db.timeouts.query_timeout_ms
                    )
                ),
            ),
            retry=DbRetrySettings(
                max_retries=int(
                    (
                        (db.get("retry", {}) or {}).get(
                            "max_retries", cfg.db.retry.max_retries
                        )
                    )
                ),
                retry_delay_ms=int(
                    (
                        (db.get("retry", {}) or {}).get(
                            "retry_delay_ms", cfg.db.retry.retry_delay_ms
                        )
                    )
                ),
                backoff_multiplier=float(
                    (
                        (db.get("retry", {}) or {}).get(
                            "backoff_multiplier", cfg.db.retry.backoff_multiplier
                        )
                    )
                ),
            ),
        ),
        ingest=IngestSettings(
            base_dir="data",  # 强制固定
            workers=int(
                os.getenv("INGEST_WORKERS", ingest.get("workers", cfg.ingest.workers))
            ),
            commit_interval=int(
                os.getenv(
                    "INGEST_COMMIT_INTERVAL",
                    ingest.get("commit_interval", cfg.ingest.commit_interval),
                )
            ),
            p95_window=int(
                os.getenv(
                    "INGEST_P95_WINDOW", ingest.get("p95_window", cfg.ingest.p95_window)
                )
            ),
            enhanced_source_hint=(
                (
                    os.getenv("INGEST_ENHANCED_SOURCE_HINT").lower()
                    in ("1", "true", "yes")
                )
                if os.getenv("INGEST_ENHANCED_SOURCE_HINT") is not None
                else bool(
                    ingest.get("enhanced_source_hint", cfg.ingest.enhanced_source_hint)
                )
            ),
            batch_id_mode=str(
                os.getenv(
                    "INGEST_BATCH_ID_MODE",
                    ingest.get("batch_id_mode", cfg.ingest.batch_id_mode),
                )
            ),
            csv=CsvSettings(
                delimiter=str(
                    (
                        (ingest.get("csv", {}) or {}).get(
                            "delimiter", cfg.ingest.csv.delimiter
                        )
                    )
                ),
                encoding=str(
                    (
                        (ingest.get("csv", {}) or {}).get(
                            "encoding", cfg.ingest.csv.encoding
                        )
                    )
                ),
                quote_char=str(
                    (
                        (ingest.get("csv", {}) or {}).get(
                            "quote_char", cfg.ingest.csv.quote_char
                        )
                    )
                ),
                escape_char=str(
                    (
                        (ingest.get("csv", {}) or {}).get(
                            "escape_char", cfg.ingest.csv.escape_char
                        )
                    )
                ),
                allow_bom=bool(
                    (
                        (ingest.get("csv", {}) or {}).get(
                            "allow_bom", cfg.ingest.csv.allow_bom
                        )
                    )
                ),
            ),
            batch=BatchSettingsExt(
                size=int(
                    ((ingest.get("batch", {}) or {}).get("size", cfg.ingest.batch.size))
                ),
                max_memory_mb=int(
                    (
                        (ingest.get("batch", {}) or {}).get(
                            "max_memory_mb", cfg.ingest.batch.max_memory_mb
                        )
                    )
                ),
                parallel_batches=int(
                    (
                        (ingest.get("batch", {}) or {}).get(
                            "parallel_batches", cfg.ingest.batch.parallel_batches
                        )
                    )
                ),
            ),
            error_handling=ErrorHandlingSettings(
                max_errors_per_file=int(
                    (
                        (ingest.get("error_handling", {}) or {}).get(
                            "max_errors_per_file",
                            cfg.ingest.error_handling.max_errors_per_file,
                        )
                    )
                ),
                error_threshold_percent=float(
                    (
                        (ingest.get("error_handling", {}) or {}).get(
                            "error_threshold_percent",
                            cfg.ingest.error_handling.error_threshold_percent,
                        )
                    )
                ),
                continue_on_error=bool(
                    (
                        (ingest.get("error_handling", {}) or {}).get(
                            "continue_on_error",
                            cfg.ingest.error_handling.continue_on_error,
                        )
                    )
                ),
            ),
            performance=IngestPerformance(
                read_buffer_size=int(
                    (
                        (ingest.get("performance", {}) or {}).get(
                            "read_buffer_size",
                            cfg.ingest.performance.read_buffer_size,
                        )
                    )
                ),
                write_buffer_size=int(
                    (
                        (ingest.get("performance", {}) or {}).get(
                            "write_buffer_size",
                            cfg.ingest.performance.write_buffer_size,
                        )
                    )
                ),
                connection_pool_size=int(
                    (
                        (ingest.get("performance", {}) or {}).get(
                            "connection_pool_size",
                            cfg.ingest.performance.connection_pool_size,
                        )
                    )
                ),
            ),
            backpressure=IngestBackpressure(
                thresholds=BackpressureThresholds(
                    p95_ms=int(
                        (
                            (ingest.get("backpressure", {}) or {}).get("thresholds", {})
                            or {}
                        ).get("p95_ms", cfg.ingest.backpressure.thresholds.p95_ms)
                    ),
                    fail_rate=float(
                        (
                            (ingest.get("backpressure", {}) or {}).get("thresholds", {})
                            or {}
                        ).get("fail_rate", cfg.ingest.backpressure.thresholds.fail_rate)
                    ),
                    min_batch=int(
                        (
                            (ingest.get("backpressure", {}) or {}).get("thresholds", {})
                            or {}
                        ).get("min_batch", cfg.ingest.backpressure.thresholds.min_batch)
                    ),
                    min_workers=int(
                        (
                            (ingest.get("backpressure", {}) or {}).get("thresholds", {})
                            or {}
                        ).get(
                            "min_workers",
                            cfg.ingest.backpressure.thresholds.min_workers,
                        )
                    ),
                )
            ),
            default_paths=DefaultPathSettings(
                mapping_file=str(
                    (ingest.get("default_paths", {}) or {}).get(
                        "mapping_file", cfg.ingest.default_paths.mapping_file
                    )
                ),
                dim_metric_config=str(
                    (ingest.get("default_paths", {}) or {}).get(
                        "dim_metric_config", cfg.ingest.default_paths.dim_metric_config
                    )
                ),
            ),
            default_window=DefaultWindowSettings(
                process_all_data=bool(
                    (ingest.get("default_window", {}) or {}).get(
                        "process_all_data", cfg.ingest.default_window.process_all_data
                    )
                ),
                start_utc=str(
                    (ingest.get("default_window", {}) or {}).get(
                        "start_utc", cfg.ingest.default_window.start_utc
                    )
                ),
                end_utc=str(
                    (ingest.get("default_window", {}) or {}).get(
                        "end_utc", cfg.ingest.default_window.end_utc
                    )
                ),
            ),
        ),
        merge=MergeSettings(
            window=IngestWindow(
                size=(
                    str(merge.get("window", {}).get("size", cfg.merge.window.size))
                    if merge.get("window")
                    else cfg.merge.window.size
                ),
                start=(
                    str(merge.get("window", {}).get("start", cfg.merge.window.start))
                    if merge.get("window")
                    else cfg.merge.window.start
                ),
                end=(
                    str(merge.get("window", {}).get("end", cfg.merge.window.end))
                    if merge.get("window")
                    else cfg.merge.window.end
                ),
            ),
            tz=MergeTzPolicy(
                default_station_tz=(
                    str(
                        merge.get("tz", {}).get(
                            "default_station_tz", cfg.merge.tz.default_station_tz
                        )
                    )
                    if merge.get("tz")
                    else cfg.merge.tz.default_station_tz
                ),
                allow_missing_tz=(
                    bool(
                        merge.get("tz", {}).get(
                            "allow_missing_tz", cfg.merge.tz.allow_missing_tz
                        )
                    )
                    if merge.get("tz")
                    else cfg.merge.tz.allow_missing_tz
                ),
                missing_tz_policy=(
                    str(
                        merge.get("tz", {}).get(
                            "missing_tz_policy", cfg.merge.tz.missing_tz_policy
                        )
                    )
                    if merge.get("tz")
                    else cfg.merge.tz.missing_tz_policy
                ),
            ),
        ),
        logging=LoggingSettings(
            # 严格按 YAML 加载，不读取 ENV/CLI
            level=str(logging_cfg.get("level", cfg.logging.level)),
            format=str(logging_cfg.get("format", cfg.logging.format)),
            routing=str(logging_cfg.get("routing", cfg.logging.routing)),
            queue_handler=(
                bool(logging_cfg.get("performance", {}).get("queue_handler"))
                if logging_cfg.get("performance")
                else cfg.logging.queue_handler
            ),
            sql=LoggingSql(
                text=str(logging_cfg.get("sql", {}).get("text", cfg.logging.sql.text)),
                explain=str(
                    logging_cfg.get("sql", {}).get("explain", cfg.logging.sql.explain)
                ),
                top_n_slow=int(
                    logging_cfg.get("sql", {}).get(
                        "top_n_slow", cfg.logging.sql.top_n_slow
                    )
                ),
            ),
            sampling=SamplingSettings(
                loop_log_every_n=(
                    int(
                        logging_cfg.get("sampling", {}).get(
                            "loop_log_every_n",
                            cfg.logging.sampling.loop_log_every_n,
                        )
                    )
                    if logging_cfg.get("sampling")
                    else cfg.logging.sampling.loop_log_every_n
                ),
                min_interval_sec=(
                    float(
                        logging_cfg.get("sampling", {}).get(
                            "min_interval_sec",
                            cfg.logging.sampling.min_interval_sec,
                        )
                    )
                    if logging_cfg.get("sampling")
                    else cfg.logging.sampling.min_interval_sec
                ),
                default_rate=float(
                    (logging_cfg.get("sampling", {}) or {}).get(
                        "default_rate", cfg.logging.sampling.default_rate
                    )
                ),
                high_frequency_events=(
                    (logging_cfg.get("sampling", {}) or {}).get(
                        "high_frequency_events",
                        cfg.logging.sampling.high_frequency_events,
                    )
                    or {},
                ),
                burst_limit=int(
                    (logging_cfg.get("sampling", {}) or {}).get(
                        "burst_limit", cfg.logging.sampling.burst_limit
                    )
                ),
            ),
            rotation=LoggingRotation(
                max_bytes=int(
                    (logging_cfg.get("rotation", {}) or {}).get(
                        "max_bytes", cfg.logging.rotation.max_bytes
                    )
                ),
                backup_count=int(
                    (logging_cfg.get("rotation", {}) or {}).get(
                        "backup_count", cfg.logging.rotation.backup_count
                    )
                ),
                rotation_interval=int(
                    (logging_cfg.get("rotation", {}) or {}).get(
                        "rotation_interval", cfg.logging.rotation.rotation_interval
                    )
                ),
            ),
            formatting=LoggingFormatting(
                timestamp_format=str(
                    (logging_cfg.get("formatting", {}) or {}).get(
                        "timestamp_format", cfg.logging.formatting.timestamp_format
                    )
                ),
                max_message_length=int(
                    (logging_cfg.get("formatting", {}) or {}).get(
                        "max_message_length",
                        cfg.logging.formatting.max_message_length,
                    )
                ),
                field_order=tuple(
                    (logging_cfg.get("formatting", {}) or {}).get(
                        "field_order", list(cfg.logging.formatting.field_order)
                    )
                ),
            ),
            performance=LoggingPerformance(
                buffer_size=int(
                    (logging_cfg.get("performance", {}) or {}).get(
                        "buffer_size", cfg.logging.performance.buffer_size
                    )
                ),
                flush_interval=float(
                    (logging_cfg.get("performance", {}) or {}).get(
                        "flush_interval", cfg.logging.performance.flush_interval
                    )
                ),
                async_handler_queue_size=int(
                    (logging_cfg.get("performance", {}) or {}).get(
                        "async_handler_queue_size",
                        cfg.logging.performance.async_handler_queue_size,
                    )
                ),
            ),
            redaction_enable=(
                bool((logging_cfg.get("redaction", {}) or {}).get("enable"))
                if logging_cfg.get("redaction")
                else cfg.logging.redaction_enable
            ),
            retention_days=int(
                logging_cfg.get("retention_days", cfg.logging.retention_days)
            ),
            startup_cleanup=StartupCleanupSettings(
                clear_logs=bool(
                    (logging_cfg.get("startup_cleanup", {}) or {}).get(
                        "clear_logs", cfg.logging.startup_cleanup.clear_logs
                    )
                ),
                clear_database=bool(
                    (logging_cfg.get("startup_cleanup", {}) or {}).get(
                        "clear_database", cfg.logging.startup_cleanup.clear_database
                    )
                ),
                logs_backup_count=int(
                    (logging_cfg.get("startup_cleanup", {}) or {}).get(
                        "logs_backup_count", cfg.logging.startup_cleanup.logs_backup_count
                    )
                ),
                confirm_clear=bool(
                    (logging_cfg.get("startup_cleanup", {}) or {}).get(
                        "confirm_clear", cfg.logging.startup_cleanup.confirm_clear
                    )
                ),
            ),
            detailed_logging=DetailedLoggingSettings(
                enable_function_entry=bool(
                    (logging_cfg.get("detailed_logging", {}) or {}).get(
                        "enable_function_entry", cfg.logging.detailed_logging.enable_function_entry
                    )
                ),
                enable_function_exit=bool(
                    (logging_cfg.get("detailed_logging", {}) or {}).get(
                        "enable_function_exit", cfg.logging.detailed_logging.enable_function_exit
                    )
                ),
                enable_parameter_logging=bool(
                    (logging_cfg.get("detailed_logging", {}) or {}).get(
                        "enable_parameter_logging", cfg.logging.detailed_logging.enable_parameter_logging
                    )
                ),
                enable_context_logging=bool(
                    (logging_cfg.get("detailed_logging", {}) or {}).get(
                        "enable_context_logging", cfg.logging.detailed_logging.enable_context_logging
                    )
                ),
                enable_business_logging=bool(
                    (logging_cfg.get("detailed_logging", {}) or {}).get(
                        "enable_business_logging", cfg.logging.detailed_logging.enable_business_logging
                    )
                ),
                enable_progress_logging=bool(
                    (logging_cfg.get("detailed_logging", {}) or {}).get(
                        "enable_progress_logging", cfg.logging.detailed_logging.enable_progress_logging
                    )
                ),
                enable_performance_logging=bool(
                    (logging_cfg.get("detailed_logging", {}) or {}).get(
                        "enable_performance_logging", cfg.logging.detailed_logging.enable_performance_logging
                    )
                ),
                enable_error_details=bool(
                    (logging_cfg.get("detailed_logging", {}) or {}).get(
                        "enable_error_details", cfg.logging.detailed_logging.enable_error_details
                    )
                ),
                enable_internal_steps=bool(
                    (logging_cfg.get("detailed_logging", {}) or {}).get(
                        "enable_internal_steps", cfg.logging.detailed_logging.enable_internal_steps
                    )
                ),
                enable_condition_branches=bool(
                    (logging_cfg.get("detailed_logging", {}) or {}).get(
                        "enable_condition_branches", cfg.logging.detailed_logging.enable_condition_branches
                    )
                ),
                enable_loop_iterations=bool(
                    (logging_cfg.get("detailed_logging", {}) or {}).get(
                        "enable_loop_iterations", cfg.logging.detailed_logging.enable_loop_iterations
                    )
                ),
                enable_intermediate_results=bool(
                    (logging_cfg.get("detailed_logging", {}) or {}).get(
                        "enable_intermediate_results", cfg.logging.detailed_logging.enable_intermediate_results
                    )
                ),
                enable_data_validation=bool(
                    (logging_cfg.get("detailed_logging", {}) or {}).get(
                        "enable_data_validation", cfg.logging.detailed_logging.enable_data_validation
                    )
                ),
                enable_resource_usage=bool(
                    (logging_cfg.get("detailed_logging", {}) or {}).get(
                        "enable_resource_usage", cfg.logging.detailed_logging.enable_resource_usage
                    )
                ),
                enable_timing_details=bool(
                    (logging_cfg.get("detailed_logging", {}) or {}).get(
                        "enable_timing_details", cfg.logging.detailed_logging.enable_timing_details
                    )
                ),
                internal_steps_interval=int(
                    (logging_cfg.get("detailed_logging", {}) or {}).get(
                        "internal_steps_interval", cfg.logging.detailed_logging.internal_steps_interval
                    )
                ),
                loop_log_interval=int(
                    (logging_cfg.get("detailed_logging", {}) or {}).get(
                        "loop_log_interval", cfg.logging.detailed_logging.loop_log_interval
                    )
                ),
            ),
            key_metrics=KeyMetricsSettings(
                enable_file_count=bool(
                    (logging_cfg.get("key_metrics", {}) or {}).get(
                        "enable_file_count", cfg.logging.key_metrics.enable_file_count
                    )
                ),
                enable_data_time_range=bool(
                    (logging_cfg.get("key_metrics", {}) or {}).get(
                        "enable_data_time_range", cfg.logging.key_metrics.enable_data_time_range
                    )
                ),
                enable_processing_progress=bool(
                    (logging_cfg.get("key_metrics", {}) or {}).get(
                        "enable_processing_progress", cfg.logging.key_metrics.enable_processing_progress
                    )
                ),
                enable_merge_statistics=bool(
                    (logging_cfg.get("key_metrics", {}) or {}).get(
                        "enable_merge_statistics", cfg.logging.key_metrics.enable_merge_statistics
                    )
                ),
                enable_performance_metrics=bool(
                    (logging_cfg.get("key_metrics", {}) or {}).get(
                        "enable_performance_metrics", cfg.logging.key_metrics.enable_performance_metrics
                    )
                ),
                enable_memory_usage=bool(
                    (logging_cfg.get("key_metrics", {}) or {}).get(
                        "enable_memory_usage", cfg.logging.key_metrics.enable_memory_usage
                    )
                ),
                enable_database_stats=bool(
                    (logging_cfg.get("key_metrics", {}) or {}).get(
                        "enable_database_stats", cfg.logging.key_metrics.enable_database_stats
                    )
                ),
                enable_file_size_info=bool(
                    (logging_cfg.get("key_metrics", {}) or {}).get(
                        "enable_file_size_info", cfg.logging.key_metrics.enable_file_size_info
                    )
                ),
                enable_throughput_metrics=bool(
                    (logging_cfg.get("key_metrics", {}) or {}).get(
                        "enable_throughput_metrics", cfg.logging.key_metrics.enable_throughput_metrics
                    )
                ),
                enable_error_statistics=bool(
                    (logging_cfg.get("key_metrics", {}) or {}).get(
                        "enable_error_statistics", cfg.logging.key_metrics.enable_error_statistics
                    )
                ),
                enable_quality_metrics=bool(
                    (logging_cfg.get("key_metrics", {}) or {}).get(
                        "enable_quality_metrics", cfg.logging.key_metrics.enable_quality_metrics
                    )
                ),
                enable_pipeline_stages=bool(
                    (logging_cfg.get("key_metrics", {}) or {}).get(
                        "enable_pipeline_stages", cfg.logging.key_metrics.enable_pipeline_stages
                    )
                ),
                enable_batch_statistics=bool(
                    (logging_cfg.get("key_metrics", {}) or {}).get(
                        "enable_batch_statistics", cfg.logging.key_metrics.enable_batch_statistics
                    )
                ),
                enable_resource_consumption=bool(
                    (logging_cfg.get("key_metrics", {}) or {}).get(
                        "enable_resource_consumption", cfg.logging.key_metrics.enable_resource_consumption
                    )
                ),
                enable_data_distribution=bool(
                    (logging_cfg.get("key_metrics", {}) or {}).get(
                        "enable_data_distribution", cfg.logging.key_metrics.enable_data_distribution
                    )
                ),
                progress_report_interval=int(
                    (logging_cfg.get("key_metrics", {}) or {}).get(
                        "progress_report_interval", cfg.logging.key_metrics.progress_report_interval
                    )
                ),
                metrics_summary_interval=int(
                    (logging_cfg.get("key_metrics", {}) or {}).get(
                        "metrics_summary_interval", cfg.logging.key_metrics.metrics_summary_interval
                    )
                ),
            ),
            sql_execution=SqlExecutionSettings(
                enable_statement_logging=bool(
                    (logging_cfg.get("sql_execution", {}) or {}).get(
                        "enable_statement_logging", cfg.logging.sql_execution.enable_statement_logging
                    )
                ),
                enable_execution_metrics=bool(
                    (logging_cfg.get("sql_execution", {}) or {}).get(
                        "enable_execution_metrics", cfg.logging.sql_execution.enable_execution_metrics
                    )
                ),
                enable_parameter_logging=bool(
                    (logging_cfg.get("sql_execution", {}) or {}).get(
                        "enable_parameter_logging", cfg.logging.sql_execution.enable_parameter_logging
                    )
                ),
                enable_result_summary=bool(
                    (logging_cfg.get("sql_execution", {}) or {}).get(
                        "enable_result_summary", cfg.logging.sql_execution.enable_result_summary
                    )
                ),
                enable_slow_query_detection=bool(
                    (logging_cfg.get("sql_execution", {}) or {}).get(
                        "enable_slow_query_detection", cfg.logging.sql_execution.enable_slow_query_detection
                    )
                ),
                slow_query_threshold_ms=int(
                    (logging_cfg.get("sql_execution", {}) or {}).get(
                        "slow_query_threshold_ms", cfg.logging.sql_execution.slow_query_threshold_ms
                    )
                ),
                max_sql_length=int(
                    (logging_cfg.get("sql_execution", {}) or {}).get(
                        "max_sql_length", cfg.logging.sql_execution.max_sql_length
                    )
                ),
                sensitive_fields=tuple(
                    (logging_cfg.get("sql_execution", {}) or {}).get(
                        "sensitive_fields", list(cfg.logging.sql_execution.sensitive_fields)
                    )
                ),
            ),
            internal_execution=InternalExecutionSettings(
                enable_step_logging=bool(
                    (logging_cfg.get("internal_execution", {}) or {}).get(
                        "enable_step_logging", cfg.logging.internal_execution.enable_step_logging
                    )
                ),
                enable_checkpoint_logging=bool(
                    (logging_cfg.get("internal_execution", {}) or {}).get(
                        "enable_checkpoint_logging", cfg.logging.internal_execution.enable_checkpoint_logging
                    )
                ),
                enable_branch_logging=bool(
                    (logging_cfg.get("internal_execution", {}) or {}).get(
                        "enable_branch_logging", cfg.logging.internal_execution.enable_branch_logging
                    )
                ),
                enable_iteration_logging=bool(
                    (logging_cfg.get("internal_execution", {}) or {}).get(
                        "enable_iteration_logging", cfg.logging.internal_execution.enable_iteration_logging
                    )
                ),
                enable_validation_logging=bool(
                    (logging_cfg.get("internal_execution", {}) or {}).get(
                        "enable_validation_logging", cfg.logging.internal_execution.enable_validation_logging
                    )
                ),
                enable_transformation_logging=bool(
                    (logging_cfg.get("internal_execution", {}) or {}).get(
                        "enable_transformation_logging", cfg.logging.internal_execution.enable_transformation_logging
                    )
                ),
                step_detail_level=str(
                    (logging_cfg.get("internal_execution", {}) or {}).get(
                        "step_detail_level", cfg.logging.internal_execution.step_detail_level
                    )
                ),
                iteration_log_frequency=int(
                    (logging_cfg.get("internal_execution", {}) or {}).get(
                        "iteration_log_frequency", cfg.logging.internal_execution.iteration_log_frequency
                    )
                ),
                checkpoint_auto_interval=int(
                    (logging_cfg.get("internal_execution", {}) or {}).get(
                        "checkpoint_auto_interval", cfg.logging.internal_execution.checkpoint_auto_interval
                    )
                ),
            ),
        ),
    )
    return cfg


def load_settings_with_sources(config_dir: Path) -> tuple[Settings, dict]:
    """加载配置并返回 (Settings, sources)；sources 标注来源：DEFAULT|YAML。
    说明：根据规范，db 与 logging 仅来自 YAML；不标注 ENV。
    """
    settings = load_settings(config_dir)

    # 仅读取 YAML 以判定来源（不改变 settings 值）
    cdir = _first_existing_dir(config_dir)
    ingest_path = cdir / "ingest.yaml"
    logging_path = cdir / "logging.yaml"
    database_path = cdir / "database.yaml"

    data: dict[str, dict] = {}
    if ingest_path.exists():
        with ingest_path.open("r", encoding="utf-8") as f:
            data["ingest"] = yaml.safe_load(f) or {}
    if logging_path.exists():
        with logging_path.open("r", encoding="utf-8") as f:
            data["logging"] = yaml.safe_load(f) or {}
    if database_path.exists():
        with database_path.open("r", encoding="utf-8") as f:
            data["db"] = yaml.safe_load(f) or {}

    db = data.get("db", {})
    ingest = data.get("ingest", {})
    merge = data.get("merge", {})
    logging_cfg = data.get("logging", {})

    def src_yaml_only(yaml_has: bool) -> str:
        return "YAML" if yaml_has else "DEFAULT"

    def src_env_or_yaml(env_key: str, yaml_has: bool) -> str:
        # 仅用于 ingest（允许 ENV 覆盖）；db/logging 禁止 ENV
        import os as _os

        return (
            "ENV"
            if _os.getenv(env_key) is not None
            else ("YAML" if yaml_has else "DEFAULT")
        )

    sources: dict[str, dict[str, str]] = {
        "db": {
            "host": src_yaml_only("host" in db),
            "name": src_yaml_only("name" in db),
            "user": src_yaml_only("user" in db),
            "dsn_read": src_yaml_only("dsn_read" in db),
            "dsn_write": src_yaml_only("dsn_write" in db),
        },
        "ingest": {
            "base_dir": "DEFAULT",  # 固定为 data
            "workers": src_env_or_yaml("INGEST_WORKERS", "workers" in ingest),
            "commit_interval": src_env_or_yaml(
                "INGEST_COMMIT_INTERVAL", "commit_interval" in ingest
            ),
            "p95_window": src_env_or_yaml("INGEST_P95_WINDOW", "p95_window" in ingest),
            "enhanced_source_hint": src_env_or_yaml(
                "INGEST_ENHANCED_SOURCE_HINT", "enhanced_source_hint" in ingest
            ),
            "batch_id_mode": src_env_or_yaml(
                "INGEST_BATCH_ID_MODE", "batch_id_mode" in ingest
            ),
        },
        "merge": {
            "window.size": (
                "YAML" if merge.get("window", {}).get("size") is not None else "DEFAULT"
            ),
            "window.start": (
                "YAML"
                if merge.get("window", {}).get("start") is not None
                else "DEFAULT"
            ),
            "window.end": (
                "YAML" if merge.get("window", {}).get("end") is not None else "DEFAULT"
            ),
            "tz.default_station_tz": (
                "YAML"
                if merge.get("tz", {}).get("default_station_tz") is not None
                else "DEFAULT"
            ),
            "tz.allow_missing_tz": (
                "YAML"
                if merge.get("tz", {}).get("allow_missing_tz") is not None
                else "DEFAULT"
            ),
            "tz.missing_tz_policy": (
                "YAML"
                if merge.get("tz", {}).get("missing_tz_policy") is not None
                else "DEFAULT"
            ),
        },
        "logging": {
            "level": src_yaml_only("level" in logging_cfg),
            "format": src_yaml_only("format" in logging_cfg),
            "routing": src_yaml_only("routing" in logging_cfg),
            "queue_handler": (
                "YAML"
                if (logging_cfg.get("performance", {}) or {}).get("queue_handler")
                is not None
                else "DEFAULT"
            ),
            "sql.text": (
                "YAML"
                if (logging_cfg.get("sql", {}) or {}).get("text") is not None
                else "DEFAULT"
            ),
            "sql.explain": (
                "YAML"
                if (logging_cfg.get("sql", {}) or {}).get("explain") is not None
                else "DEFAULT"
            ),
            "sampling.loop_log_every_n": (
                "YAML"
                if (logging_cfg.get("sampling", {}) or {}).get("loop_log_every_n")
                is not None
                else "DEFAULT"
            ),
            "redaction_enable": (
                "YAML"
                if (logging_cfg.get("redaction", {}) or {}).get("enable") is not None
                else "DEFAULT"
            ),
            "retention_days": (
                "YAML" if logging_cfg.get("retention_days") is not None else "DEFAULT"
            ),
        },
    }

    return settings, sources
