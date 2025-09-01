"""
数据导入配置模块（app.core.config.ingest）

本模块包含数据导入相关的配置类定义，包括：
- CSV解析配置
- 批处理配置
- 错误处理配置
- 性能配置
- 背压控制配置
"""

from dataclasses import dataclass


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
class CsvSettings:
    """
    CSV解析配置

    用于配置CSV文件的解析参数。

    属性：
        delimiter: 分隔符
        encoding: 编码格式
        quote_char: 引用字符
        escape_char: 转义字符
        allow_bom: 是否允许BOM标记
    """

    delimiter: str = ","
    encoding: str = "utf-8"
    quote_char: str = '"'
    escape_char: str = "\\"
    allow_bom: bool = True


@dataclass(frozen=True)
class BatchSettingsExt:
    """
    批处理配置

    用于配置数据批处理的参数。

    属性：
        size: 批次大小
        max_memory_mb: 最大内存使用量（MB）
        parallel_batches: 并行批次数量
    """

    size: int = 50_000
    max_memory_mb: int = 256
    parallel_batches: int = 2


@dataclass(frozen=True)
class ErrorHandlingSettings:
    """
    错误处理配置

    用于配置错误处理策略。

    属性：
        max_errors_per_file: 单文件最大错误数
        error_threshold_percent: 错误阈值百分比
        continue_on_error: 遇错是否继续
    """

    max_errors_per_file: int = 100
    error_threshold_percent: float = 5.0
    continue_on_error: bool = True


@dataclass(frozen=True)
class IngestPerformance:
    """
    数据导入性能配置

    用于配置数据导入过程的性能参数。

    属性：
        read_buffer_size: 读缓冲区大小
        write_buffer_size: 写缓冲区大小
        connection_pool_size: 连接池大小
    """

    read_buffer_size: int = 65_536
    write_buffer_size: int = 65_536
    connection_pool_size: int = 5


@dataclass(frozen=True)
class BackpressureThresholds:
    """
    背压阈值配置

    用于配置背压控制的阈值参数。

    属性：
        p95_ms: P95耗时阈值（毫秒）
        fail_rate: 失败率阈值
        min_batch: 最小批大小
        min_workers: 最小工作线程数
    """

    p95_ms: int = 2000
    fail_rate: float = 0.01
    min_batch: int = 1000
    min_workers: int = 1


@dataclass(frozen=True)
class IngestBackpressure:
    """
    数据导入背压控制配置

    用于配置数据导入过程的背压控制。

    属性：
        thresholds: 背压阈值配置
    """

    thresholds: BackpressureThresholds = BackpressureThresholds()


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
class IngestSettings:
    """
    数据导入完整配置

    集成所有数据导入相关配置，提供统一的配置访问接口。

    属性：
        base_dir: 基础数据目录
        workers: 工作线程数
        commit_interval: 提交间隔
        p95_window: P95窗口大小
        enhanced_source_hint: 是否启用增强源提示
        batch_id_mode: 批次ID模式
        csv: CSV解析配置
        batch: 批处理配置
        error_handling: 错误处理配置
        performance: 性能配置
        backpressure: 背压控制配置
        default_paths: 默认路径配置
        default_window: 默认窗口配置
    """

    base_dir: str = "data"
    workers: int = 6
    commit_interval: int = 1_000_000
    p95_window: int = 20
    enhanced_source_hint: bool = True
    batch_id_mode: str = "run_id"
    csv: CsvSettings = CsvSettings()
    batch: BatchSettingsExt = BatchSettingsExt()
    error_handling: ErrorHandlingSettings = ErrorHandlingSettings()
    performance: IngestPerformance = IngestPerformance()
    backpressure: IngestBackpressure = IngestBackpressure()
    default_paths: DefaultPathSettings = DefaultPathSettings()
    default_window: DefaultWindowSettings = DefaultWindowSettings()
