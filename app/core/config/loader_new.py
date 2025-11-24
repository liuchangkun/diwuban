"""
配置加载模块（app.core.config.loader_new）

本模块负责应用程序的配置管理，提供统一的配置加载和验证机制。

核心功能：
- Settings：应用全局配置（db/ingest/merge/system）
- load_settings：按目录优先级与 YAML 合并规则加载配置
- load_settings_with_sources：提供配置来源追踪的加载函数
- 配置验证：确保配置的正确性和完整性
- 硬编码消除：所有配置均从配置文件读取

配置优先级：
1. CLI 参数 > 环境变量 > YAML 文件 > 默认值
2. 数据库配置仅允许来自 database.yaml，不允许通过 ENV/CLI 覆盖
3. 部分 ingest 配置支持环境变量覆盖（见白名单）
4. 系统配置提供全局默认值，避免硬编码
5. 已移除日志配置，所有日志相关功能不再加载

配置文件结构：
- configs/database.yaml：数据库连接和池配置
- configs/ingest.yaml：数据导入和处理配置
- configs/system.yaml：系统通用配置
"""

import os
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Tuple

import yaml  # type: ignore[import-untyped]

# 导入拆分的配置模块
from .database import DbPoolSettings, DbRetrySettings, DbSettings, DbTimeoutSettings
from .error_handling import ErrorHandlingSettings as ErrorHandlingConfig
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
from .merge import IngestWindow, MergeSettings, MergeTzPolicy, SegmentedMergeSettings
from .system import (
    SystemDirectoriesSettings,
    SystemGeneralSettings,
    SystemSettings,
    SystemTimezoneSettings,
)
from .validation import ConfigValidator

# 进程内缓存：避免重复加载配置；按规范化目录键控
_SETTINGS_CACHE: dict[str, "Settings"] = {}
_SETTINGS_CACHE_LOCK = RLock()


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
    - system: 系统通用配置
    - error_handling: 错误处理配置

    使用示例：
        settings = load_settings(Path("configs"))

        # 访问数据库配置
        db_host = settings.db.host
        pool_size = settings.db.pool.max_size

        # 访问系统配置
        timezone = settings.system.timezone.default
    """

    db: DbSettings = DbSettings()
    ingest: IngestSettings = IngestSettings()
    merge: MergeSettings = MergeSettings()
    system: SystemSettings = SystemSettings()
    error_handling: ErrorHandlingConfig = ErrorHandlingConfig()


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
    - 支持文件：database.yaml、ingest.yaml、merge.yaml、system.yaml、error_handling.yaml
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
        "ingest": cdir / "ingest.yaml",
        "merge": cdir / "merge.yaml",
        "system": cdir / "system.yaml",
        "error_handling": cdir / "error_handling.yaml",
    }

    data: Dict[str, Any] = {}
    for config_name, config_path in config_files.items():
        if config_path.exists():
            try:
                with config_path.open("r", encoding="utf-8") as f:
                    loaded_data = yaml.safe_load(f)
                    data[config_name] = loaded_data or {}
            except Exception:
                data[config_name] = {}
        else:
            data[config_name] = {}

    # 验证配置
    validation_result = ConfigValidator.validate_complete_config(data)
    # 跳过日志记录

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

    # 构建导入配置（支持 ENV 覆盖，使用系统默认值）
    ingest_settings = _build_ingest_settings(
        data.get("ingest", {}), data_dir, default_timezone, default_encoding
    )

    # 构建合并配置（使用系统默认时区）
    merge_settings = _build_merge_settings(data.get("merge", {}), default_timezone)

    # 构建错误处理配置（仅从 YAML 加载）
    error_handling_settings = _build_error_handling_settings(
        data.get("error_handling", {})
    )

    # 构建最终配置对象
    settings = Settings(
        db=db_settings,
        ingest=ingest_settings,
        merge=merge_settings,
        system=system_settings,
        error_handling=error_handling_settings,
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
        password=db_config.get("password"),  # 读取密码字段
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
            connection_acquire_timeout_ms=int(
                timeouts_config.get("connection_acquire_timeout_ms", 10000)
            ),
            connection_validation_timeout_ms=int(
                timeouts_config.get("connection_validation_timeout_ms", 1000)
            ),
            pool_shutdown_timeout_ms=int(
                timeouts_config.get("pool_shutdown_timeout_ms", 30000)
            ),
        ),
        retry=DbRetrySettings(
            max_retries=int(retry_config.get("max_retries", 3)),
            retry_delay_ms=int(retry_config.get("retry_delay_ms", 1000)),
            backoff_multiplier=float(retry_config.get("backoff_multiplier", 2.0)),
        ),
        staging_unlogged=bool(db_config.get("staging_unlogged", False)),
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


# 已移除日志相关配置构建函数


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
    for config_name in ["database", "logging", "ingest", "merge", "system"]:
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
    }

    return sources


def _build_error_handling_settings(
    error_handling_config: Dict[str, Any],
) -> ErrorHandlingConfig:
    """构建错误处理配置（仅从 YAML 加载）"""
    from .error_handling import (
        AlertingConfig,
        AnalysisValidationConfig,
        CircuitBreakerSettings,
        CircuitBreakerValidationConfig,
        ErrorAnalysisSettings,
        ErrorRecordingConfig,
        HotReloadConfig,
        InitializationSettings,
        MonitoringDecoratorConfig,
        MonitoringSettings,
        PatternDetectionConfig,
        PerformanceMonitoringConfig,
        ReportingConfig,
        RetrySettings,
        RetryValidationConfig,
        StartupConfig,
        TrendAnalysisConfig,
        ValidationSettings,
    )

    # 构建重试配置
    retry_config = error_handling_config.get("retry", {})
    retry_settings = RetrySettings(
        default=_build_retry_policy_config(retry_config.get("default", {})),
        network_errors=_build_retry_policy_config(
            retry_config.get("network_errors", {})
        ),
        database_connection_errors=_build_retry_policy_config(
            retry_config.get("database_connection_errors", {})
        ),
        high_priority_errors=_build_retry_policy_config(
            retry_config.get("high_priority_errors", {})
        ),
        degradable_errors=_build_retry_policy_config(
            retry_config.get("degradable_errors", {})
        ),
        resource_exhausted_errors=_build_retry_policy_config(
            retry_config.get("resource_exhausted_errors", {})
        ),
    )

    # 构建断路器配置
    circuit_breaker_config = error_handling_config.get("circuit_breaker", {})
    circuit_breaker_settings = CircuitBreakerSettings(
        default=_build_circuit_breaker_config(
            circuit_breaker_config.get("default", {})
        ),
        database_operations=_build_circuit_breaker_config(
            circuit_breaker_config.get("database_operations", {})
        ),
        database_connection_creation=_build_circuit_breaker_config(
            circuit_breaker_config.get("database_connection_creation", {})
        ),
        api_calls=_build_circuit_breaker_config(
            circuit_breaker_config.get("api_calls", {})
        ),
        file_operations=_build_circuit_breaker_config(
            circuit_breaker_config.get("file_operations", {})
        ),
        network_operations=_build_circuit_breaker_config(
            circuit_breaker_config.get("network_operations", {})
        ),
    )

    # 构建错误分析配置
    analysis_config = error_handling_config.get("error_analysis", {})
    error_analysis_settings = ErrorAnalysisSettings(
        recording=ErrorRecordingConfig(
            max_records=int(
                analysis_config.get("recording", {}).get("max_records", 10000)
            ),
            analysis_window=int(
                analysis_config.get("recording", {}).get("analysis_window", 3600)
            ),
            cleanup_interval=int(
                analysis_config.get("recording", {}).get("cleanup_interval", 300)
            ),
            auto_cleanup=bool(
                analysis_config.get("recording", {}).get("auto_cleanup", True)
            ),
        ),
        pattern_detection=PatternDetectionConfig(
            min_frequency=int(
                analysis_config.get("pattern_detection", {}).get("min_frequency", 3)
            ),
            time_window=int(
                analysis_config.get("pattern_detection", {}).get("time_window", 1800)
            ),
            similarity_threshold=float(
                analysis_config.get("pattern_detection", {}).get(
                    "similarity_threshold", 0.8
                )
            ),
            enable_auto_detection=bool(
                analysis_config.get("pattern_detection", {}).get(
                    "enable_auto_detection", True
                )
            ),
        ),
        trend_analysis=TrendAnalysisConfig(
            analysis_interval=int(
                analysis_config.get("trend_analysis", {}).get("analysis_interval", 300)
            ),
            trend_window=int(
                analysis_config.get("trend_analysis", {}).get("trend_window", 3600)
            ),
            rate_threshold=float(
                analysis_config.get("trend_analysis", {}).get("rate_threshold", 0.1)
            ),
            enable_prediction=bool(
                analysis_config.get("trend_analysis", {}).get("enable_prediction", True)
            ),
        ),
        reporting=ReportingConfig(
            auto_generate=bool(
                analysis_config.get("reporting", {}).get("auto_generate", True)
            ),
            report_interval=int(
                analysis_config.get("reporting", {}).get("report_interval", 1800)
            ),
            max_reports=int(
                analysis_config.get("reporting", {}).get("max_reports", 100)
            ),
            include_patterns=bool(
                analysis_config.get("reporting", {}).get("include_patterns", True)
            ),
            include_trends=bool(
                analysis_config.get("reporting", {}).get("include_trends", True)
            ),
            include_suggestions=bool(
                analysis_config.get("reporting", {}).get("include_suggestions", True)
            ),
        ),
    )

    # 构建监控配置
    monitoring_config = error_handling_config.get("monitoring", {})
    monitoring_settings = MonitoringSettings(
        decorator=MonitoringDecoratorConfig(
            enable_context_capture=bool(
                monitoring_config.get("decorator", {}).get(
                    "enable_context_capture", True
                )
            ),
            max_context_size=int(
                monitoring_config.get("decorator", {}).get("max_context_size", 1000)
            ),
            capture_args=bool(
                monitoring_config.get("decorator", {}).get("capture_args", True)
            ),
            capture_return=bool(
                monitoring_config.get("decorator", {}).get("capture_return", False)
            ),
            exclude_sensitive_keys=monitoring_config.get("decorator", {}).get(
                "exclude_sensitive_keys", ["password", "token", "secret", "key", "auth"]
            ),
        ),
        performance=PerformanceMonitoringConfig(
            enable_timing=bool(
                monitoring_config.get("performance", {}).get("enable_timing", True)
            ),
            slow_threshold=float(
                monitoring_config.get("performance", {}).get("slow_threshold", 5.0)
            ),
            memory_monitoring=bool(
                monitoring_config.get("performance", {}).get("memory_monitoring", False)
            ),
        ),
        alerting=AlertingConfig(
            enable_alerts=bool(
                monitoring_config.get("alerting", {}).get("enable_alerts", False)
            ),
            error_rate_threshold=float(
                monitoring_config.get("alerting", {}).get("error_rate_threshold", 0.05)
            ),
            consecutive_failures_threshold=int(
                monitoring_config.get("alerting", {}).get(
                    "consecutive_failures_threshold", 10
                )
            ),
            circuit_breaker_open_alert=bool(
                monitoring_config.get("alerting", {}).get(
                    "circuit_breaker_open_alert", True
                )
            ),
        ),
    )

    # 构建验证配置
    validation_config = error_handling_config.get("validation", {})
    validation_settings = ValidationSettings(
        retry_validation=RetryValidationConfig(
            max_retries_limit=int(
                validation_config.get("retry_validation", {}).get(
                    "max_retries_limit", 10
                )
            ),
            max_delay_limit=float(
                validation_config.get("retry_validation", {}).get(
                    "max_delay_limit", 300.0
                )
            ),
            min_base_delay=float(
                validation_config.get("retry_validation", {}).get(
                    "min_base_delay", 0.01
                )
            ),
            valid_strategies=validation_config.get("retry_validation", {}).get(
                "valid_strategies", ["fixed", "linear", "exponential", "fibonacci"]
            ),
        ),
        circuit_breaker_validation=CircuitBreakerValidationConfig(
            max_failure_threshold=int(
                validation_config.get("circuit_breaker_validation", {}).get(
                    "max_failure_threshold", 20
                )
            ),
            max_recovery_timeout=float(
                validation_config.get("circuit_breaker_validation", {}).get(
                    "max_recovery_timeout", 600.0
                )
            ),
            min_recovery_timeout=float(
                validation_config.get("circuit_breaker_validation", {}).get(
                    "min_recovery_timeout", 5.0
                )
            ),
            max_half_open_calls=int(
                validation_config.get("circuit_breaker_validation", {}).get(
                    "max_half_open_calls", 10
                )
            ),
        ),
        analysis_validation=AnalysisValidationConfig(
            max_records_limit=int(
                validation_config.get("analysis_validation", {}).get(
                    "max_records_limit", 100000
                )
            ),
            max_analysis_window=int(
                validation_config.get("analysis_validation", {}).get(
                    "max_analysis_window", 86400
                )
            ),
            min_analysis_window=int(
                validation_config.get("analysis_validation", {}).get(
                    "min_analysis_window", 60
                )
            ),
            max_context_size_limit=int(
                validation_config.get("analysis_validation", {}).get(
                    "max_context_size_limit", 10000
                )
            ),
        ),
    )

    # 构建初始化配置
    initialization_config = error_handling_config.get("initialization", {})
    initialization_settings = InitializationSettings(
        startup=StartupConfig(
            validate_config=bool(
                initialization_config.get("startup", {}).get("validate_config", True)
            ),
            initialize_components=bool(
                initialization_config.get("startup", {}).get(
                    "initialize_components", True
                )
            ),
            fail_on_invalid_config=bool(
                initialization_config.get("startup", {}).get(
                    "fail_on_invalid_config", True
                )
            ),
        ),
        hot_reload=HotReloadConfig(
            enable_hot_reload=bool(
                initialization_config.get("hot_reload", {}).get(
                    "enable_hot_reload", False
                )
            ),
            watch_config_files=bool(
                initialization_config.get("hot_reload", {}).get(
                    "watch_config_files", False
                )
            ),
            reload_interval=int(
                initialization_config.get("hot_reload", {}).get("reload_interval", 60)
            ),
            backup_on_reload=bool(
                initialization_config.get("hot_reload", {}).get(
                    "backup_on_reload", True
                )
            ),
        ),
    )

    return ErrorHandlingConfig(
        retry=retry_settings,
        circuit_breaker=circuit_breaker_settings,
        error_analysis=error_analysis_settings,
        monitoring=monitoring_settings,
        validation=validation_settings,
        initialization=initialization_settings,
    )


def _build_retry_policy_config(policy_config: Dict[str, Any]):
    """构建重试策略配置"""
    from .error_handling import RetryPolicyConfig

    return RetryPolicyConfig(
        max_retries=int(policy_config.get("max_retries", 3)),
        base_delay=float(policy_config.get("base_delay", 1.0)),
        max_delay=float(policy_config.get("max_delay", 60.0)),
        backoff_multiplier=float(policy_config.get("backoff_multiplier", 2.0)),
        jitter=bool(policy_config.get("jitter", True)),
        strategy=str(policy_config.get("strategy", "exponential")),
    )


def _build_circuit_breaker_config(
    breaker_config: Dict[str, Any],
):
    """构建断路器配置"""
    from .error_handling import CircuitBreakerConfig

    return CircuitBreakerConfig(
        failure_threshold=int(breaker_config.get("failure_threshold", 5)),
        recovery_timeout=float(breaker_config.get("recovery_timeout", 60.0)),
        half_open_max_calls=int(breaker_config.get("half_open_max_calls", 3)),
        half_open_success_threshold=int(
            breaker_config.get("half_open_success_threshold", 2)
        ),
    )


def _get_bool_env(env_key: str, default_value: bool) -> bool:
    """从环境变量获取布尔值"""
    env_value = os.getenv(env_key)
    if env_value is None:
        return default_value
    return env_value.lower() in ("1", "true", "yes", "on")
