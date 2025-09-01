"""
日志高级配置模块（app.core.config.logging_advanced）

本模块包含日志系统的高级配置类定义，包括：
- 启动清理配置
- 详细日志配置
- 关键指标配置
- SQL执行日志配置
- 内部执行日志配置
"""

from dataclasses import dataclass


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
    关键指标日志配置
    
    用于配置关键业务指标的日志记录。
    
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
    
    用于配置SQL执行过程的详细日志记录。
    
    属性：
        enable_statement_logging: 记录完整SQL语句
        enable_execution_metrics: 记录执行指标
        enable_parameter_logging: 记录参数信息
        enable_result_summary: 记录结果摘要
        enable_slow_query_detection: 启用慢查询检测
        slow_query_threshold_ms: 慢查询阈值（毫秒）
        max_sql_length: SQL语句最大记录长度
        sensitive_fields: 敏感字段列表（用于脱敏）
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
    内部执行日志配置
    
    用于配置程序内部执行过程的详细日志记录。
    
    属性：
        enable_step_logging: 记录执行步骤
        enable_checkpoint_logging: 记录检查点
        enable_branch_logging: 记录分支执行
        enable_iteration_logging: 记录迭代过程
        enable_validation_logging: 记录验证过程
        enable_transformation_logging: 记录数据转换
        step_detail_level: 步骤详细级别 ("basic" | "detailed" | "verbose")
        iteration_log_frequency: 迭代日志频率
        checkpoint_auto_interval: 自动检查点间隔
    """
    enable_step_logging: bool = True
    enable_checkpoint_logging: bool = True
    enable_branch_logging: bool = True
    enable_iteration_logging: bool = True
    enable_validation_logging: bool = True
    enable_transformation_logging: bool = True
    step_detail_level: str = "detailed"
    iteration_log_frequency: int = 100
    checkpoint_auto_interval: int = 1000