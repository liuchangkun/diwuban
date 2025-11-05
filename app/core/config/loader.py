from __future__ import annotations

"""
配置加载（app.core.config.loader）

本模块负责应用程序的配置管理，提供统一的配置加载和验证机制：

核心功能：
- Settings：应用全局配置（db/ingest/merge/web）
- load_settings：按目录优先级与 YAML 合并规则加载配置，且强制 ingest.base_dir = data
- load_settings_with_sources：提供配置来源追踪的加载函数

配置优先级：
1. CLI 参数 > 环境变量 > YAML 文件 > 默认值
2. 数据库配置仅允许来自 database.yaml，不允许通过 ENV/CLI 覆盖
3. 部分 ingest 配置支持环境变量覆盖（见白名单）

配置文件结构：
- configs/database.yaml：数据库连接和池配置

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


注意事项：
- 修改配置字段需同步更新 docs/配置说明.md

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

    mapping_file: str = "configs/data_mapping.v2.json"  # 统一为 configs/

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


# 导入数据库配置类，避免重复定义
from .database import DbPoolSettings, DbRetrySettings, DbSettings, DbTimeoutSettings


# DbSettings 已在 database.py 中定义，此处移除重复定义


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

    - web: Web服务配置

    使用示例：
        settings = load_settings(Path("configs"))

        # 访问数据库配置
        db_host = settings.db.host
        pool_size = settings.db.pool.max_size

        # 访问导入配置
        workers = settings.ingest.workers
        batch_size = settings.ingest.batch.size

        # 访问Web配置
        host = settings.web.server.host
        port = settings.web.server.port
    """

    db: DbSettings = DbSettings()
    ingest: IngestSettings = IngestSettings()
    merge: MergeSettings = MergeSettings()

    web: WebSettings = WebSettings()


def _first_existing_dir(config_dir: Path) -> Path:
    """返回第一个存在的配置目录（优先级：传入 → ./configs → ./config）。"""
    for d in [config_dir, Path("configs"), Path("config")]:
        if d.exists() and d.is_dir():
            return d
    return config_dir


def load_settings(config_dir: Path) -> Settings:
    """加载配置（强制 ingest.base_dir 固定为 data）。

    - 目录优先级：传入 config_dir → ./configs → ./config
    - 支持文件：ingest.yaml、database.yaml、web.yaml
    - 合并策略：ingest 支持 CLI/ENV > YAML > 默认；db 仅 YAML > 默认；仅白名单字段；不允许覆盖 ingest.base_dir
    """
    cfg = Settings()

    def _first_existing_dir_compat() -> Path:
        # 兼容旧实现内部函数引用
        return _first_existing_dir(config_dir)

    cdir = _first_existing_dir(config_dir)
    ingest_path = cdir / "ingest.yaml"

    database_path = cdir / "database.yaml"
    web_path = cdir / "web.yaml"  # 添加web.yaml路径

    data: dict[str, dict] = {}
    if ingest_path.exists():
        with ingest_path.open("r", encoding="utf-8") as f:
            data["ingest"] = yaml.safe_load(f) or {}

    if database_path.exists():
        with database_path.open("r", encoding="utf-8") as f:
            data["db"] = yaml.safe_load(f) or {}
    if web_path.exists():  # 添加web.yaml加载逻辑
        with web_path.open("r", encoding="utf-8") as f:
            data["web"] = yaml.safe_load(f) or {}

    # 合并：仅合并允许的键；ingest.base_dir 强制为 data
    db: dict = data.get("db", {})
    ingest: dict = data.get("ingest", {})
    merge: dict = data.get("merge", {})
    web_cfg: dict = data.get("web", {})  # 获取web配置

    cfg = Settings(
        db=DbSettings(
            # 严格按 YAML 加载，不读取 ENV/CLI
            host=str(db.get("host", cfg.db.host)),
            name=str(db.get("dbname", cfg.db.name)),
            user=str(db.get("user", cfg.db.user)),
            password=db.get("password"),  # 读取密码字段
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
                    ),
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
        web=WebSettings(  # 添加web配置处理逻辑
            server=WebServerSettings(
                host=str(web_cfg.get("server", {}).get("host", cfg.web.server.host)),
                port=int(web_cfg.get("server", {}).get("port", cfg.web.server.port)),
                reload=bool(
                    web_cfg.get("server", {}).get("reload", cfg.web.server.reload)
                ),
                workers=int(
                    web_cfg.get("server", {}).get("workers", cfg.web.server.workers)
                ),
            ),
            api=WebApiSettings(
                title=str(web_cfg.get("api", {}).get("title", cfg.web.api.title)),
                description=str(
                    web_cfg.get("api", {}).get("description", cfg.web.api.description)
                ),
                version=str(web_cfg.get("api", {}).get("version", cfg.web.api.version)),
                docs_url=str(
                    web_cfg.get("api", {}).get("docs_url", cfg.web.api.docs_url)
                ),
                redoc_url=str(
                    web_cfg.get("api", {}).get("redoc_url", cfg.web.api.redoc_url)
                ),
            ),
            app=WebAppSettings(
                debug=bool(web_cfg.get("app", {}).get("debug", cfg.web.app.debug)),
                log_requests=bool(
                    web_cfg.get("app", {}).get("log_requests", cfg.web.app.log_requests)
                ),
                cors_enabled=bool(
                    web_cfg.get("app", {}).get("cors_enabled", cfg.web.app.cors_enabled)
                ),
                cors_origins=list(
                    web_cfg.get("app", {}).get("cors_origins", cfg.web.app.cors_origins)
                ),
            ),
            performance=WebPerformanceSettings(
                request_timeout=int(
                    web_cfg.get("performance", {}).get(
                        "request_timeout", cfg.web.performance.request_timeout
                    )
                ),
                max_request_size=int(
                    web_cfg.get("performance", {}).get(
                        "max_request_size", cfg.web.performance.max_request_size
                    )
                ),
                keepalive_timeout=int(
                    web_cfg.get("performance", {}).get(
                        "keepalive_timeout", cfg.web.performance.keepalive_timeout
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

    database_path = cdir / "database.yaml"
    web_path = cdir / "web.yaml"  # 添加web.yaml路径

    data: dict[str, dict] = {}
    if ingest_path.exists():
        with ingest_path.open("r", encoding="utf-8") as f:
            data["ingest"] = yaml.safe_load(f) or {}

    if database_path.exists():
        with database_path.open("r", encoding="utf-8") as f:
            data["db"] = yaml.safe_load(f) or {}
    if web_path.exists():  # 添加web.yaml加载逻辑
        with web_path.open("r", encoding="utf-8") as f:
            data["web"] = yaml.safe_load(f) or {}

    db = data.get("db", {})
    ingest = data.get("ingest", {})
    merge = data.get("merge", {})

    web_cfg = data.get("web", {})  # 获取web配置

    def src_yaml_only(yaml_has: bool) -> str:
        return "YAML" if yaml_has else "DEFAULT"

    def src_env_or_yaml(env_key: str, yaml_has: bool) -> str:
        # 仅用于 ingest（允许 ENV 覆盖）；db 禁止 ENV
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
        "web": {  # 添加web配置的来源追踪
            "server.host": src_yaml_only("host" in web_cfg.get("server", {})),
            "server.port": src_yaml_only("port" in web_cfg.get("server", {})),
            "server.reload": src_yaml_only("reload" in web_cfg.get("server", {})),
            "server.workers": src_yaml_only("workers" in web_cfg.get("server", {})),
            "api.title": src_yaml_only("title" in web_cfg.get("api", {})),
            "api.description": src_yaml_only("description" in web_cfg.get("api", {})),
            "api.version": src_yaml_only("version" in web_cfg.get("api", {})),
            "api.docs_url": src_yaml_only("docs_url" in web_cfg.get("api", {})),
            "api.redoc_url": src_yaml_only("redoc_url" in web_cfg.get("api", {})),
            "app.debug": src_yaml_only("debug" in web_cfg.get("app", {})),
            "app.log_requests": src_yaml_only("log_requests" in web_cfg.get("app", {})),
            "app.cors_enabled": src_yaml_only("cors_enabled" in web_cfg.get("app", {})),
            "performance.request_timeout": src_yaml_only(
                "request_timeout" in web_cfg.get("performance", {})
            ),
            "performance.max_request_size": src_yaml_only(
                "max_request_size" in web_cfg.get("performance", {})
            ),
            "performance.keepalive_timeout": src_yaml_only(
                "keepalive_timeout" in web_cfg.get("performance", {})
            ),
        },
    }

    return settings, sources
