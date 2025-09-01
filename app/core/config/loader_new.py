"""
配置加载模块（app.core.config.loader_new）

本模块负责应用程序的配置管理，提供统一的配置加载和验证机制。

核心功能：
- Settings：应用全局配置（db/ingest/merge/logging/web/system）
- load_settings：按目录优先级与 YAML 合并规则加载配置
- load_settings_with_sources：提供配置来源追踪的加载函数
- 配置验证：确保配置的正确性和完整性
- 硬编码消除：所有配置均从配置文件读取

配置优先级：
1. CLI 参数 > 环境变量 > YAML 文件 > 默认值
2. 数据库配置仅允许来自 database.yaml，不允许通过 ENV/CLI 覆盖
3. 部分 ingest 配置支持环境变量覆盖（见白名单）
4. 系统配置提供全局默认值，避免硬编码

配置文件结构：
- configs/database.yaml：数据库连接和池配置
- configs/logging.yaml：日志格式、级别和路由配置
- configs/ingest.yaml：数据导入和处理配置
- configs/web.yaml：Web服务配置
- configs/system.yaml：系统通用配置
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Tuple

import yaml  # type: ignore[import-untyped]

# 导入拆分的配置模块
from .database import DbPoolSettings, DbRetrySettings, DbSettings, DbTimeoutSettings
from .ingest import (
    BackpressureThresholds,
    BatchSettingsExt,
    CsvSettings,
    DefaultPathSettings,
    DefaultWindowSettings,
    ErrorHandlingSettings,
    IngestBackpressure,
    IngestPerformance,
    IngestSettings,
)
from .logging import LoggingSettings
from .logging_advanced import (
    DetailedLoggingSettings,
    InternalExecutionSettings,
    KeyMetricsSettings,
    SqlExecutionSettings,
    StartupCleanupSettings,
)
from .logging_base import (
    LoggingFormatting,
    LoggingPerformance,
    LoggingRotation,
    LoggingSql,
    SamplingSettings,
)
from .logging_filters import LoggingFiltersSettings
from .logging_output import LoggingOutputSettings
from .merge import IngestWindow, MergeSettings, MergeTzPolicy, SegmentedMergeSettings
from .system import (
    SystemDirectoriesSettings,
    SystemGeneralSettings,
    SystemSettings,
    SystemTimezoneSettings,
)
from .validation import ConfigValidator, log_validation_result
from .web import (
    WebApiSettings,
    WebAppSettings,
    WebPerformanceSettings,
    WebServerSettings,
    WebSettings,
)

# 模块日志记录器
logger = logging.getLogger(__name__)


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
    - web: Web服务配置
    - system: 系统通用配置

    使用示例：
        settings = load_settings(Path("configs"))

        # 访问数据库配置
        db_host = settings.db.host
        pool_size = settings.db.pool.max_size

        # 访问Web服务配置
        port = settings.web.server.port

        # 访问系统配置
        timezone = settings.system.timezone.default
    """

    db: DbSettings = DbSettings()
    ingest: IngestSettings = IngestSettings()
    merge: MergeSettings = MergeSettings()
    logging: LoggingSettings = LoggingSettings()
    web: WebSettings = WebSettings()
    system: SystemSettings = SystemSettings()


def _first_existing_dir(config_dir: Path) -> Path:
    """返回第一个存在的配置目录（优先级：传入 → ./configs → ./config）。"""
    for d in [config_dir, Path("configs"), Path("config")]:
        if d.exists() and d.is_dir():
            return d
    return config_dir


def load_settings(config_dir: Path) -> Settings:
    """
    加载配置（解决硬编码问题，支持配置外置化）。

    - 目录优先级：传入 config_dir → ./configs → ./config
    - 支持文件：database.yaml、logging.yaml、ingest.yaml、web.yaml、system.yaml
    - 合并策略：ingest 支持 CLI/ENV > YAML > 默认；db/logging 仅 YAML > 默认
    - 硬编码消除：所有默认值均从 system.yaml 读取

    参数：
        config_dir: 配置文件目录路径

    返回：
        Settings: 完整的应用配置对象
    """
    cdir = _first_existing_dir(config_dir)

    # 加载各个配置文件
    config_files = {
        "database": cdir / "database.yaml",
        "logging": cdir / "logging.yaml",
        "ingest": cdir / "ingest.yaml",
        "merge": cdir / "merge.yaml",
        "web": cdir / "web.yaml",
        "system": cdir / "system.yaml",
    }

    data: Dict[str, Any] = {}
    for config_name, config_path in config_files.items():
        if config_path.exists():
            try:
                with config_path.open("r", encoding="utf-8") as f:
                    loaded_data = yaml.safe_load(f)
                    data[config_name] = loaded_data or {}
                    logger.info(f"成功加载配置文件: {config_path}")
            except Exception as e:
                logger.error(f"加载配置文件失败 {config_path}: {e}")
                data[config_name] = {}
        else:
            logger.warning(f"配置文件不存在，使用默认配置: {config_path}")
            data[config_name] = {}

    # 验证配置
    validation_result = ConfigValidator.validate_complete_config(data)
    log_validation_result(validation_result, logger)

    if not validation_result.is_valid:
        raise ValueError(f"配置验证失败: {len(validation_result.errors)} 个错误")

    # 从系统配置中读取全局默认值，解决硬编码问题
    system_config = data.get("system", {})
    timezone_config = system_config.get("timezone", {})
    directories_config = system_config.get("directories", {})
    general_config = system_config.get("general", {})

    # 获取系统级别默认值
    default_timezone = timezone_config.get("default", "Asia/Shanghai")
    data_dir = directories_config.get("data", "data")
    logs_dir = directories_config.get("logs", "logs")
    # configs_dir 未直接使用，移除以降低未使用告警
    default_encoding = general_config.get("encoding", "utf-8")

    # 构建系统配置
    system_settings = _build_system_settings(system_config)

    # 构建数据库配置（仅从 YAML 加载）
    db_settings = _build_database_settings(data.get("database", {}))

    # 构建 Web 配置
    web_settings = _build_web_settings(data.get("web", {}))

    # 构建导入配置（支持 ENV 覆盖，使用系统默认值）
    ingest_settings = _build_ingest_settings(
        data.get("ingest", {}), data_dir, default_timezone, default_encoding
    )

    # 构建合并配置（使用系统默认时区）
    merge_settings = _build_merge_settings(data.get("merge", {}), default_timezone)

    # 构建日志配置（仅从 YAML 加载，使用系统默认值）
    logging_settings = _build_logging_settings(data.get("logging", {}), logs_dir)

    # 构建最终配置对象
    settings = Settings(
        db=db_settings,
        ingest=ingest_settings,
        merge=merge_settings,
        logging=logging_settings,
        web=web_settings,
        system=system_settings,
    )

    logger.info(
        f"配置加载完成，数据目录: {settings.system.directories.data}, "
        f"Web端口: {settings.web.server.port}, 默认时区: {settings.system.timezone.default}"
    )

    return settings


def load_settings_with_sources(config_dir: Path) -> Tuple[Settings, Dict[str, Any]]:
    """
    加载配置并返回配置来源信息。

    参数：
        config_dir: 配置文件目录路径

    返回：
        Tuple[Settings, Dict]: 配置对象和来源信息
    """
    settings = load_settings(config_dir)

    # 实现配置来源追踪逻辑
    sources = _build_config_sources(config_dir)

    return settings, sources


# ================================
# 配置构建辅助函数
# ================================


def _build_system_settings(system_config: Dict[str, Any]) -> SystemSettings:
    """构建系统配置"""
    directories = system_config.get("directories", {})
    timezone = system_config.get("timezone", {})
    general = system_config.get("general", {})

    return SystemSettings(
        directories=SystemDirectoriesSettings(
            data=str(directories.get("data", "data")),
            logs=str(directories.get("logs", "logs")),
            configs=str(directories.get("configs", "configs")),
            temp=str(directories.get("temp", "temp")),
            backup=str(directories.get("backup", "backup")),
        ),
        timezone=SystemTimezoneSettings(
            default=str(timezone.get("default", "Asia/Shanghai")),
            storage=str(timezone.get("storage", "UTC")),
            display=str(timezone.get("display", "Asia/Shanghai")),
        ),
        general=SystemGeneralSettings(
            encoding=str(general.get("encoding", "utf-8")),
            locale=str(general.get("locale", "zh_CN.UTF-8")),
            max_workers=int(general.get("max_workers", 4)),
        ),
    )


def _build_database_settings(db_config: Dict[str, Any]) -> DbSettings:
    """构建数据库配置（仅从 YAML 加载）"""
    pool_config = db_config.get("pool", {})
    timeouts_config = db_config.get("timeouts", {})
    retry_config = db_config.get("retry", {})

    return DbSettings(
        host=str(db_config.get("host", "localhost")),
        name=str(db_config.get("dbname", "pump_station_optimization")),
        user=str(db_config.get("user", "postgres")),
        dsn_read=db_config.get("dsn_read"),
        dsn_write=db_config.get("dsn_write"),
        pool=DbPoolSettings(
            min_size=int(pool_config.get("min_size", 1)),
            max_size=int(pool_config.get("max_size", 10)),
            max_inactive_connection_lifetime=int(
                pool_config.get("max_inactive_connection_lifetime", 3600)
            ),
        ),
        timeouts=DbTimeoutSettings(
            connect_timeout_ms=int(timeouts_config.get("connect_timeout_ms", 5000)),
            statement_timeout_ms=int(
                timeouts_config.get("statement_timeout_ms", 30000)
            ),
            query_timeout_ms=int(timeouts_config.get("query_timeout_ms", 60000)),
        ),
        retry=DbRetrySettings(
            max_retries=int(retry_config.get("max_retries", 3)),
            retry_delay_ms=int(retry_config.get("retry_delay_ms", 1000)),
            backoff_multiplier=float(retry_config.get("backoff_multiplier", 2.0)),
        ),
    )


def _build_web_settings(web_config: Dict[str, Any]) -> WebSettings:
    """构建 Web 服务配置"""
    server_config = web_config.get("server", {})
    api_config = web_config.get("api", {})
    app_config = web_config.get("app", {})
    performance_config = web_config.get("performance", {})

    return WebSettings(
        server=WebServerSettings(
            host=str(server_config.get("host", "127.0.0.1")),
            port=int(server_config.get("port", 8000)),
            reload=bool(server_config.get("reload", True)),
            workers=int(server_config.get("workers", 1)),
        ),
        api=WebApiSettings(
            title=str(api_config.get("title", "Pump Station Optimization API")),
            description=str(api_config.get("description", "泵站运行数据优化系统 API")),
            version=str(api_config.get("version", "1.0.0")),
            docs_url=str(api_config.get("docs_url", "/docs")),
            redoc_url=str(api_config.get("redoc_url", "/redoc")),
            # 新增：从配置读取最小默认时间窗（分钟），默认 60
            minimal_window_minutes=int(api_config.get("minimal_window_minutes", 60)),
        ),
        app=WebAppSettings(
            debug=bool(app_config.get("debug", False)),
            log_requests=bool(app_config.get("log_requests", True)),
            cors_enabled=bool(app_config.get("cors_enabled", False)),
            cors_origins=list(app_config.get("cors_origins", [])),
        ),
        performance=WebPerformanceSettings(
            request_timeout=int(performance_config.get("request_timeout", 30)),
            max_request_size=int(performance_config.get("max_request_size", 16777216)),
            keepalive_timeout=int(performance_config.get("keepalive_timeout", 65)),
        ),
    )


def _build_ingest_settings(
    ingest_config: Dict[str, Any],
    data_dir: str,
    default_timezone: str,
    default_encoding: str,
) -> IngestSettings:
    """构建导入配置（支持 ENV 覆盖，使用系统默认值）"""
    # CSV 配置
    csv_config = ingest_config.get("csv", {})
    csv_settings = CsvSettings(
        delimiter=str(csv_config.get("delimiter", ",")),
        encoding=str(csv_config.get("encoding", default_encoding)),
        quote_char=str(csv_config.get("quote_char", '"')),
        escape_char=str(csv_config.get("escape_char", "\\")),
        allow_bom=bool(csv_config.get("allow_bom", True)),
    )

    # 批处理配置
    batch_config = ingest_config.get("batch", {})
    batch_settings = BatchSettingsExt(
        size=int(batch_config.get("size", 50000)),
        max_memory_mb=int(batch_config.get("max_memory_mb", 256)),
        parallel_batches=int(batch_config.get("parallel_batches", 2)),
    )

    # 错误处理配置
    error_config = ingest_config.get("error_handling", {})
    error_settings = ErrorHandlingSettings(
        max_errors_per_file=int(error_config.get("max_errors_per_file", 100)),
        error_threshold_percent=float(error_config.get("error_threshold_percent", 5.0)),
        continue_on_error=bool(error_config.get("continue_on_error", True)),
    )

    # 性能配置
    performance_config = ingest_config.get("performance", {})
    performance_settings = IngestPerformance(
        read_buffer_size=int(performance_config.get("read_buffer_size", 65536)),
        write_buffer_size=int(performance_config.get("write_buffer_size", 65536)),
        connection_pool_size=int(performance_config.get("connection_pool_size", 5)),
    )

    # 背压配置
    backpressure_config = ingest_config.get("backpressure", {})
    thresholds_config = backpressure_config.get("thresholds", {})
    backpressure_settings = IngestBackpressure(
        thresholds=BackpressureThresholds(
            p95_ms=int(thresholds_config.get("p95_ms", 2000)),
            fail_rate=float(thresholds_config.get("fail_rate", 0.01)),
            min_batch=int(thresholds_config.get("min_batch", 1000)),
            min_workers=int(thresholds_config.get("min_workers", 1)),
        )
    )

    # 默认路径配置（解决硬编码问题）
    paths_config = ingest_config.get("default_paths", {})
    paths_settings = DefaultPathSettings(
        mapping_file=str(
            paths_config.get(
                "mapping_file", "configs/data_mapping.v2.json"
            )  # 默认路径统一至 configs/
        ),
        dim_metric_config=str(
            paths_config.get("dim_metric_config", "config/dim_metric_config.json")
        ),
    )

    # 默认窗口配置
    window_config = ingest_config.get("default_window", {})
    window_settings = DefaultWindowSettings(
        process_all_data=bool(window_config.get("process_all_data", True)),
        start_utc=str(window_config.get("start_utc", "2025-02-27T18:00:00Z")),
        end_utc=str(window_config.get("end_utc", "2025-02-27T19:59:59Z")),
    )

    return IngestSettings(
        base_dir=data_dir,  # 使用系统配置中的值，解决硬编码
        # 支持环境变量覆盖的字段
        workers=int(os.getenv("INGEST_WORKERS", ingest_config.get("workers", 6))),
        commit_interval=int(
            os.getenv(
                "INGEST_COMMIT_INTERVAL", ingest_config.get("commit_interval", 1000000)
            )
        ),
        p95_window=int(
            os.getenv("INGEST_P95_WINDOW", ingest_config.get("p95_window", 20))
        ),
        enhanced_source_hint=_get_bool_env(
            "INGEST_ENHANCED_SOURCE_HINT",
            ingest_config.get("enhanced_source_hint", True),
        ),
        batch_id_mode=str(
            os.getenv(
                "INGEST_BATCH_ID_MODE", ingest_config.get("batch_id_mode", "run_id")
            )
        ),
        csv=csv_settings,
        batch=batch_settings,
        error_handling=error_settings,
        performance=performance_settings,
        backpressure=backpressure_settings,
        default_paths=paths_settings,
        default_window=window_settings,
    )


def _build_merge_settings(
    merge_config: Dict[str, Any], default_timezone: str
) -> MergeSettings:
    """构建合并配置（使用系统默认时区）"""
    window_config = merge_config.get("window", {})
    tz_config = merge_config.get("tz", {})
    segmented_config = merge_config.get("segmented", {})

    return MergeSettings(
        window=IngestWindow(
            size=window_config.get("size", "7d"),
            start=window_config.get("start"),
            end=window_config.get("end"),
        ),
        tz=MergeTzPolicy(
            default_station_tz=str(
                tz_config.get("default_station_tz", default_timezone)
            ),  # 使用系统默认时区
            allow_missing_tz=bool(tz_config.get("allow_missing_tz", True)),
            missing_tz_policy=str(tz_config.get("missing_tz_policy", "default")),
        ),
        segmented=SegmentedMergeSettings(
            enabled=bool(segmented_config.get("enabled", True)),
            granularity=str(segmented_config.get("granularity", "1h")),
        ),
    )


def _build_logging_settings(
    logging_config: Dict[str, Any], logs_dir: str
) -> LoggingSettings:
    """构建日志配置（仅从 YAML 加载，使用系统默认值）"""
    # SQL 配置
    sql_config = logging_config.get("sql", {})
    sql_settings = LoggingSql(
        text=str(sql_config.get("text", "ERROR")),
        explain=str(sql_config.get("explain", "ERROR")),
        top_n_slow=int(sql_config.get("top_n_slow", 10)),
    )

    # 采样配置
    sampling_config = logging_config.get("sampling", {})
    sampling_settings = SamplingSettings(
        loop_log_every_n=int(sampling_config.get("loop_log_every_n", 1000)),
        min_interval_sec=float(sampling_config.get("min_interval_sec", 1.0)),
        default_rate=float(sampling_config.get("default_rate", 1.0)),
        high_frequency_events=sampling_config.get("high_frequency_events", {}),
        burst_limit=int(sampling_config.get("burst_limit", 10)),
    )

    # 轮转配置
    rotation_config = logging_config.get("rotation", {})
    rotation_settings = LoggingRotation(
        max_bytes=int(rotation_config.get("max_bytes", 10485760)),  # 10MB
        backup_count=int(rotation_config.get("backup_count", 5)),
        rotation_interval=int(rotation_config.get("rotation_interval", 3600)),  # 1小时
    )

    # 格式化配置
    formatting_config = logging_config.get("formatting", {})
    formatting_settings = LoggingFormatting(
        timestamp_format=str(
            formatting_config.get("timestamp_format", "%Y-%m-%d %H:%M:%S")
        ),
        max_message_length=int(formatting_config.get("max_message_length", 1000)),
        field_order=tuple(
            formatting_config.get(
                "field_order", ["timestamp", "level", "logger", "message", "run_id"]
            )
        ),
    )

    # 性能配置
    performance_config = logging_config.get("performance", {})
    performance_settings = LoggingPerformance(
        buffer_size=int(performance_config.get("buffer_size", 8192)),
        flush_interval=float(performance_config.get("flush_interval", 1.0)),
        async_handler_queue_size=int(
            performance_config.get("async_handler_queue_size", 1000)
        ),
    )

    # 启动清理配置
    startup_config = logging_config.get("startup_cleanup", {})
    startup_settings = StartupCleanupSettings(
        clear_logs=bool(startup_config.get("clear_logs", True)),
        clear_database=bool(startup_config.get("clear_database", True)),
        logs_backup_count=int(startup_config.get("logs_backup_count", 3)),
        confirm_clear=bool(startup_config.get("confirm_clear", False)),
    )

    # 详细日志配置
    detailed_config = logging_config.get("detailed_logging", {})
    detailed_settings = DetailedLoggingSettings(
        enable_function_entry=bool(detailed_config.get("enable_function_entry", True)),
        enable_function_exit=bool(detailed_config.get("enable_function_exit", True)),
        enable_parameter_logging=bool(
            detailed_config.get("enable_parameter_logging", True)
        ),
        enable_context_logging=bool(
            detailed_config.get("enable_context_logging", True)
        ),
        enable_business_logging=bool(
            detailed_config.get("enable_business_logging", True)
        ),
        enable_progress_logging=bool(
            detailed_config.get("enable_progress_logging", True)
        ),
        enable_performance_logging=bool(
            detailed_config.get("enable_performance_logging", True)
        ),
        enable_error_details=bool(detailed_config.get("enable_error_details", True)),
        enable_internal_steps=bool(detailed_config.get("enable_internal_steps", True)),
        enable_condition_branches=bool(
            detailed_config.get("enable_condition_branches", True)
        ),
        enable_loop_iterations=bool(
            detailed_config.get("enable_loop_iterations", True)
        ),
        enable_intermediate_results=bool(
            detailed_config.get("enable_intermediate_results", True)
        ),
        enable_data_validation=bool(
            detailed_config.get("enable_data_validation", True)
        ),
        enable_resource_usage=bool(detailed_config.get("enable_resource_usage", True)),
        enable_timing_details=bool(detailed_config.get("enable_timing_details", True)),
        internal_steps_interval=int(detailed_config.get("internal_steps_interval", 10)),
        loop_log_interval=int(detailed_config.get("loop_log_interval", 100)),
    )

    # 关键指标配置
    metrics_config = logging_config.get("key_metrics", {})
    metrics_settings = KeyMetricsSettings(
        enable_file_count=bool(metrics_config.get("enable_file_count", True)),
        enable_data_time_range=bool(metrics_config.get("enable_data_time_range", True)),
        enable_processing_progress=bool(
            metrics_config.get("enable_processing_progress", True)
        ),
        enable_merge_statistics=bool(
            metrics_config.get("enable_merge_statistics", True)
        ),
        enable_performance_metrics=bool(
            metrics_config.get("enable_performance_metrics", True)
        ),
        enable_memory_usage=bool(metrics_config.get("enable_memory_usage", True)),
        enable_database_stats=bool(metrics_config.get("enable_database_stats", True)),
        enable_file_size_info=bool(metrics_config.get("enable_file_size_info", True)),
        enable_throughput_metrics=bool(
            metrics_config.get("enable_throughput_metrics", True)
        ),
        enable_error_statistics=bool(
            metrics_config.get("enable_error_statistics", True)
        ),
        enable_quality_metrics=bool(metrics_config.get("enable_quality_metrics", True)),
        enable_pipeline_stages=bool(metrics_config.get("enable_pipeline_stages", True)),
        enable_batch_statistics=bool(
            metrics_config.get("enable_batch_statistics", True)
        ),
        enable_resource_consumption=bool(
            metrics_config.get("enable_resource_consumption", True)
        ),
        enable_data_distribution=bool(
            metrics_config.get("enable_data_distribution", True)
        ),
        progress_report_interval=int(
            metrics_config.get("progress_report_interval", 1000)
        ),
        metrics_summary_interval=int(
            metrics_config.get("metrics_summary_interval", 300)
        ),
    )

    # SQL 执行配置
    sql_exec_config = logging_config.get("sql_execution", {})
    sql_exec_settings = SqlExecutionSettings(
        enable_statement_logging=bool(
            sql_exec_config.get("enable_statement_logging", True)
        ),
        enable_execution_metrics=bool(
            sql_exec_config.get("enable_execution_metrics", True)
        ),
        enable_parameter_logging=bool(
            sql_exec_config.get("enable_parameter_logging", True)
        ),
        enable_result_summary=bool(sql_exec_config.get("enable_result_summary", True)),
        enable_slow_query_detection=bool(
            sql_exec_config.get("enable_slow_query_detection", True)
        ),
        slow_query_threshold_ms=int(
            sql_exec_config.get("slow_query_threshold_ms", 1000)
        ),
        max_sql_length=int(sql_exec_config.get("max_sql_length", 2000)),
        sensitive_fields=tuple(
            sql_exec_config.get(
                "sensitive_fields", ["password", "token", "secret", "key"]
            )
        ),
    )

    # 内部执行配置
    internal_exec_config = logging_config.get("internal_execution", {})
    internal_exec_settings = InternalExecutionSettings(
        enable_step_logging=bool(internal_exec_config.get("enable_step_logging", True)),
        enable_checkpoint_logging=bool(
            internal_exec_config.get("enable_checkpoint_logging", True)
        ),
        enable_branch_logging=bool(
            internal_exec_config.get("enable_branch_logging", True)
        ),
        enable_iteration_logging=bool(
            internal_exec_config.get("enable_iteration_logging", True)
        ),
        enable_validation_logging=bool(
            internal_exec_config.get("enable_validation_logging", True)
        ),
        enable_transformation_logging=bool(
            internal_exec_config.get("enable_transformation_logging", True)
        ),
        step_detail_level=str(
            internal_exec_config.get("step_detail_level", "detailed")
        ),
        iteration_log_frequency=int(
            internal_exec_config.get("iteration_log_frequency", 100)
        ),
        checkpoint_auto_interval=int(
            internal_exec_config.get("checkpoint_auto_interval", 1000)
        ),
    )

    # 输出配置
    output_settings = LoggingOutputSettings()  # 使用默认值，后续可从 YAML 加载

    # 过滤配置
    filters_settings = LoggingFiltersSettings()  # 使用默认值，后续可从 YAML 加载

    return LoggingSettings(
        level=str(logging_config.get("level", "INFO")),
        format=str(logging_config.get("format", "json")),
        routing=str(logging_config.get("routing", "by_run")),
        queue_handler=bool(performance_config.get("queue_handler", True)),
        sql=sql_settings,
        sampling=sampling_settings,
        rotation=rotation_settings,
        formatting=formatting_settings,
        performance=performance_settings,
        redaction_enable=bool(logging_config.get("redaction", {}).get("enable", False)),
        retention_days=int(logging_config.get("retention_days", 14)),
        startup_cleanup=startup_settings,
        detailed_logging=detailed_settings,
        key_metrics=metrics_settings,
        sql_execution=sql_exec_settings,
        internal_execution=internal_exec_settings,
        output=output_settings,
        filters=filters_settings,
    )


def _build_config_sources(config_dir: Path) -> Dict[str, Any]:
    """构建配置来源信息"""
    cdir = _first_existing_dir(config_dir)

    def _get_source_info(file_name: str) -> str:
        config_path = cdir / file_name
        return "YAML" if config_path.exists() else "DEFAULT"

    def _get_env_source(env_key: str, yaml_exists: bool) -> str:
        return (
            "ENV"
            if os.getenv(env_key) is not None
            else ("YAML" if yaml_exists else "DEFAULT")
        )

    def _get_yaml_field_source(yaml_data: Dict[str, Any], field_path: str) -> str:
        """检查YAML中的字段是否存在"""
        keys = field_path.split(".")
        current = yaml_data
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return "DEFAULT"
            current = current[key]
        return "YAML"

    # 加载YAML数据用于来源追踪
    yaml_data = {}
    for config_name in ["database", "logging", "ingest", "merge", "web", "system"]:
        config_path = cdir / f"{config_name}.yaml"
        if config_path.exists():
            try:
                with config_path.open("r", encoding="utf-8") as f:
                    yaml_data[config_name] = yaml.safe_load(f) or {}
            except Exception:
                yaml_data[config_name] = {}
        else:
            yaml_data[config_name] = {}

    sources = {
        "database": {
            "host": _get_yaml_field_source(yaml_data.get("database", {}), "host"),
            "dbname": _get_yaml_field_source(yaml_data.get("database", {}), "dbname"),
            "user": _get_yaml_field_source(yaml_data.get("database", {}), "user"),
            "dsn_read": _get_yaml_field_source(
                yaml_data.get("database", {}), "dsn_read"
            ),
            "dsn_write": _get_yaml_field_source(
                yaml_data.get("database", {}), "dsn_write"
            ),
            "pool.min_size": _get_yaml_field_source(
                yaml_data.get("database", {}), "pool.min_size"
            ),
            "pool.max_size": _get_yaml_field_source(
                yaml_data.get("database", {}), "pool.max_size"
            ),
            "timeouts.connect_timeout_ms": _get_yaml_field_source(
                yaml_data.get("database", {}), "timeouts.connect_timeout_ms"
            ),
            "retry.max_retries": _get_yaml_field_source(
                yaml_data.get("database", {}), "retry.max_retries"
            ),
        },
        "web": {
            "server.host": _get_yaml_field_source(
                yaml_data.get("web", {}), "server.host"
            ),
            "server.port": _get_yaml_field_source(
                yaml_data.get("web", {}), "server.port"
            ),
            "server.reload": _get_yaml_field_source(
                yaml_data.get("web", {}), "server.reload"
            ),
            "api.title": _get_yaml_field_source(yaml_data.get("web", {}), "api.title"),
            "api.version": _get_yaml_field_source(
                yaml_data.get("web", {}), "api.version"
            ),
            "app.debug": _get_yaml_field_source(yaml_data.get("web", {}), "app.debug"),
            "performance.request_timeout": _get_yaml_field_source(
                yaml_data.get("web", {}), "performance.request_timeout"
            ),
        },
        "system": {
            "timezone.default": _get_yaml_field_source(
                yaml_data.get("system", {}), "timezone.default"
            ),
            "timezone.storage": _get_yaml_field_source(
                yaml_data.get("system", {}), "timezone.storage"
            ),
            "directories.data": _get_yaml_field_source(
                yaml_data.get("system", {}), "directories.data"
            ),
            "directories.logs": _get_yaml_field_source(
                yaml_data.get("system", {}), "directories.logs"
            ),
            "directories.configs": _get_yaml_field_source(
                yaml_data.get("system", {}), "directories.configs"
            ),
            "general.encoding": _get_yaml_field_source(
                yaml_data.get("system", {}), "general.encoding"
            ),
            "general.max_workers": _get_yaml_field_source(
                yaml_data.get("system", {}), "general.max_workers"
            ),
        },
        "ingest": {
            "base_dir": "SYSTEM",  # 来自系统配置
            "workers": _get_env_source(
                "INGEST_WORKERS",
                _get_yaml_field_source(yaml_data.get("ingest", {}), "workers")
                == "YAML",
            ),
            "commit_interval": _get_env_source(
                "INGEST_COMMIT_INTERVAL",
                _get_yaml_field_source(yaml_data.get("ingest", {}), "commit_interval")
                == "YAML",
            ),
            "p95_window": _get_env_source(
                "INGEST_P95_WINDOW",
                _get_yaml_field_source(yaml_data.get("ingest", {}), "p95_window")
                == "YAML",
            ),
            "enhanced_source_hint": _get_env_source(
                "INGEST_ENHANCED_SOURCE_HINT",
                _get_yaml_field_source(
                    yaml_data.get("ingest", {}), "enhanced_source_hint"
                )
                == "YAML",
            ),
            "batch_id_mode": _get_env_source(
                "INGEST_BATCH_ID_MODE",
                _get_yaml_field_source(yaml_data.get("ingest", {}), "batch_id_mode")
                == "YAML",
            ),
            "csv.delimiter": _get_yaml_field_source(
                yaml_data.get("ingest", {}), "csv.delimiter"
            ),
            "csv.encoding": _get_yaml_field_source(
                yaml_data.get("ingest", {}), "csv.encoding"
            ),
            "batch.size": _get_yaml_field_source(
                yaml_data.get("ingest", {}), "batch.size"
            ),
            "default_paths.mapping_file": _get_yaml_field_source(
                yaml_data.get("ingest", {}), "default_paths.mapping_file"
            ),
        },
        "merge": {
            "tz.default_station_tz": "SYSTEM",  # 来自系统时区配置
            "window.size": _get_yaml_field_source(
                yaml_data.get("merge", {}), "window.size"
            ),
            "window.start": _get_yaml_field_source(
                yaml_data.get("merge", {}), "window.start"
            ),
            "window.end": _get_yaml_field_source(
                yaml_data.get("merge", {}), "window.end"
            ),
            "tz.allow_missing_tz": _get_yaml_field_source(
                yaml_data.get("merge", {}), "tz.allow_missing_tz"
            ),
            "segmented.enabled": _get_yaml_field_source(
                yaml_data.get("merge", {}), "segmented.enabled"
            ),
            "segmented.granularity": _get_yaml_field_source(
                yaml_data.get("merge", {}), "segmented.granularity"
            ),
        },
        "logging": {
            "level": _get_yaml_field_source(yaml_data.get("logging", {}), "level"),
            "format": _get_yaml_field_source(yaml_data.get("logging", {}), "format"),
            "routing": _get_yaml_field_source(yaml_data.get("logging", {}), "routing"),
            "queue_handler": _get_yaml_field_source(
                yaml_data.get("logging", {}), "performance.queue_handler"
            ),
            "sql.text": _get_yaml_field_source(
                yaml_data.get("logging", {}), "sql.text"
            ),
            "sql.explain": _get_yaml_field_source(
                yaml_data.get("logging", {}), "sql.explain"
            ),
            "sampling.loop_log_every_n": _get_yaml_field_source(
                yaml_data.get("logging", {}), "sampling.loop_log_every_n"
            ),
            "redaction.enable": _get_yaml_field_source(
                yaml_data.get("logging", {}), "redaction.enable"
            ),
            "retention_days": _get_yaml_field_source(
                yaml_data.get("logging", {}), "retention_days"
            ),
            "startup_cleanup.clear_logs": _get_yaml_field_source(
                yaml_data.get("logging", {}), "startup_cleanup.clear_logs"
            ),
            "detailed_logging.enable_function_entry": _get_yaml_field_source(
                yaml_data.get("logging", {}), "detailed_logging.enable_function_entry"
            ),
            "key_metrics.enable_file_count": _get_yaml_field_source(
                yaml_data.get("logging", {}), "key_metrics.enable_file_count"
            ),
            "sql_execution.enable_statement_logging": _get_yaml_field_source(
                yaml_data.get("logging", {}), "sql_execution.enable_statement_logging"
            ),
            "internal_execution.enable_step_logging": _get_yaml_field_source(
                yaml_data.get("logging", {}), "internal_execution.enable_step_logging"
            ),
        },
    }

    return sources


def _get_bool_env(env_key: str, default_value: bool) -> bool:
    """从环境变量获取布尔值"""
    env_value = os.getenv(env_key)
    if env_value is None:
        return default_value
    return env_value.lower() in ("1", "true", "yes", "on")
