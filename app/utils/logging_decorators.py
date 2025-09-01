from __future__ import annotations

"""
增强日志装饰器（utils.logging_decorators）

提供函数级别的日志记录装饰器，支持：
- 函数进入/退出日志
- 参数和返回值记录
- 性能监控
- 异常捕获和详细错误信息
- 业务上下文记录
- 函数内部执行过程日志
- 条件分支和循环处理日志
- 关键检查点日志记录

根据 logging.yaml 配置控制日志记录的详细程度。
"""

import functools
import logging
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, Optional

# psutil 为可选依赖；仅在存在时用于增强日志。避免静态未使用告警。
try:  # pragma: no cover - optional dependency branch
    import importlib.util as _importlib_util

    if _importlib_util.find_spec("psutil"):
        PSUTIL_AVAILABLE = True
    else:
        PSUTIL_AVAILABLE = False
except Exception:
    PSUTIL_AVAILABLE = False


def get_logger_for_module(func: Callable) -> logging.Logger:
    """根据函数获取对应的logger"""
    return logging.getLogger(func.__module__)


def sanitize_value(value: Any, max_length: int = 100) -> str:
    """
    清理和格式化值用于日志记录

    Args:
        value: 要记录的值
        max_length: 最大长度

    Returns:
        清理后的字符串
    """
    try:
        if value is None:
            return "None"
        elif isinstance(value, (str, int, float, bool)):
            str_val = str(value)
            if len(str_val) > max_length:
                return str_val[:max_length] + "..."
            return str_val
        elif isinstance(value, (list, tuple)):
            return f"{type(value).__name__}(len={len(value)})"
        elif isinstance(value, dict):
            return f"dict(keys={len(value)})"
        elif isinstance(value, Path):
            return str(value)
        else:
            return f"{type(value).__name__}(...)"
    except Exception:
        return f"{type(value).__name__}(error_converting)"


def get_memory_usage() -> Dict[str, float]:
    """获取当前内存使用情况"""
    if not PSUTIL_AVAILABLE:
        return {}

    try:
        import psutil as ps  # 在函数内部重新导入避免未绑定问题

        process = ps.Process()
        memory_info = process.memory_info()
        return {
            "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
            "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
            "percent": round(process.memory_percent(), 2),
        }
    except Exception:
        return {}


def enhanced_logger(
    log_entry: bool = True,
    log_exit: bool = True,
    log_parameters: bool = True,
    log_return: bool = False,
    log_performance: bool = True,
    log_memory: bool = False,
    business_context: Optional[str] = None,
):
    """
    增强日志装饰器

    Args:
        log_entry: 记录函数进入
        log_exit: 记录函数退出
        log_parameters: 记录函数参数
        log_return: 记录返回值
        log_performance: 记录性能指标
        log_memory: 记录内存使用
        business_context: 业务上下文描述
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger_for_module(func)
            func_name = f"{func.__module__}.{func.__qualname__}"

            # 初始化局部变量
            _log_entry = log_entry
            _log_exit = log_exit
            _log_parameters = log_parameters
            _log_performance = log_performance
            _log_memory = log_memory

            # 获取配置（如果有的话）
            settings = getattr(wrapper, "_logging_settings", None)
            if settings and hasattr(settings, "logging"):
                detailed_config = settings.logging.detailed_logging
                key_metrics_config = settings.logging.key_metrics

                # 根据配置调整参数
                _log_entry = _log_entry and detailed_config.enable_function_entry
                _log_exit = _log_exit and detailed_config.enable_function_exit
                _log_parameters = (
                    _log_parameters and detailed_config.enable_parameter_logging
                )
                _log_performance = (
                    _log_performance and detailed_config.enable_performance_logging
                )
                _log_memory = _log_memory and key_metrics_config.enable_memory_usage

            start_time = time.time()
            start_memory = get_memory_usage() if _log_memory else {}

            # 记录函数进入
            if _log_entry:
                entry_extra = {
                    "event": "function.entry",
                    "function": func_name,
                    "business_context": business_context,
                }

                # 记录参数
                if _log_parameters and (args or kwargs):
                    params = {}
                    if args:
                        params["args"] = [sanitize_value(arg) for arg in args]
                    if kwargs:
                        params["kwargs"] = {
                            k: sanitize_value(v) for k, v in kwargs.items()
                        }
                    entry_extra["parameters"] = params

                if _log_memory and start_memory:
                    entry_extra["memory_start"] = start_memory

                logger.debug(f"进入函数 {func_name}", extra=entry_extra)

            try:
                # 执行函数
                result = func(*args, **kwargs)

                # 记录函数退出
                if _log_exit:
                    end_time = time.time()
                    duration = end_time - start_time

                    exit_extra = {
                        "event": "function.exit",
                        "function": func_name,
                        "success": True,
                        "business_context": business_context,
                    }

                    if _log_performance:
                        exit_extra["performance"] = {
                            "duration_seconds": round(duration, 4),
                            "duration_ms": round(duration * 1000, 2),
                        }

                    if log_return and result is not None:
                        exit_extra["return_value"] = sanitize_value(result)

                    if _log_memory:
                        end_memory = get_memory_usage()
                        if end_memory and start_memory:
                            memory_delta = {
                                "rss_delta_mb": round(
                                    end_memory.get("rss_mb", 0)
                                    - start_memory.get("rss_mb", 0),
                                    2,
                                ),
                                "end_memory": end_memory,
                            }
                            exit_extra["memory"] = memory_delta

                    logger.debug(f"退出函数 {func_name}", extra=exit_extra)

                return result

            except Exception as e:
                end_time = time.time()
                duration = end_time - start_time

                # 记录异常
                error_extra = {
                    "event": "function.error",
                    "function": func_name,
                    "success": False,
                    "business_context": business_context,
                    "error": {
                        "type": type(e).__name__,
                        "message": str(e),
                        "traceback": traceback.format_exc(),
                    },
                }

                if _log_performance:
                    error_extra["performance"] = {
                        "duration_seconds": round(duration, 4),
                        "duration_ms": round(duration * 1000, 2),
                    }

                logger.error(f"函数执行异常 {func_name}: {e}", extra=error_extra)
                raise

        return wrapper

    return decorator


# ===== 函数内部执行过程日志记录工具 =====


class InternalStepLogger:
    """
    函数内部执行步骤日志记录器

    用于记录函数内部的关键执行步骤、中间结果、条件分支等。
    """

    def __init__(
        self,
        function_name: str,
        logger: Optional[logging.Logger] = None,
        settings: Optional[Any] = None,
    ):
        self.function_name = function_name
        self.logger = logger or logging.getLogger(__name__)
        self.settings = settings
        self.step_count = 0
        self.start_time = time.time()
        self.last_checkpoint = self.start_time

        # 获取配置
        self.config = self._get_config()

    def _get_config(self):
        """获取内部执行配置"""
        if self.settings and hasattr(self.settings, "logging"):
            return {
                "enable_step_logging": self.settings.logging.internal_execution.enable_step_logging,
                "enable_checkpoint_logging": self.settings.logging.internal_execution.enable_checkpoint_logging,
                "enable_branch_logging": self.settings.logging.internal_execution.enable_branch_logging,
                "enable_iteration_logging": self.settings.logging.internal_execution.enable_iteration_logging,
                "enable_validation_logging": self.settings.logging.internal_execution.enable_validation_logging,
                "enable_transformation_logging": self.settings.logging.internal_execution.enable_transformation_logging,
                "step_detail_level": self.settings.logging.internal_execution.step_detail_level,
                "iteration_log_frequency": self.settings.logging.internal_execution.iteration_log_frequency,
                "checkpoint_auto_interval": self.settings.logging.internal_execution.checkpoint_auto_interval,
            }
        return {
            "enable_step_logging": True,
            "enable_checkpoint_logging": True,
            "enable_branch_logging": True,
            "enable_iteration_logging": True,
            "enable_validation_logging": True,
            "enable_transformation_logging": True,
            "step_detail_level": "medium",
            "iteration_log_frequency": 100,
            "checkpoint_auto_interval": 30,
        }

    def step(self, description: str, result: Any = None, **kwargs):
        """记录执行步骤"""
        if not self.config["enable_step_logging"]:
            return

        self.step_count += 1
        current_time = time.time()
        step_duration = current_time - self.last_checkpoint
        total_duration = current_time - self.start_time

        extra = {
            "event": "function.internal.step",
            "function": self.function_name,
            "step_number": self.step_count,
            "step_description": description,
            "step_duration_ms": round(step_duration * 1000, 2),
            "total_duration_ms": round(total_duration * 1000, 2),
        }

        # 添加结果信息
        if result is not None:
            extra["step_result"] = sanitize_value(result, max_length=200)

        # 添加扩展信息
        for key, value in kwargs.items():
            extra[f"step_{key}"] = sanitize_value(value, max_length=200)

        level_map = {"low": logging.DEBUG, "medium": logging.INFO, "high": logging.INFO}
        log_level = level_map.get(self.config["step_detail_level"], logging.INFO)

        self.logger.log(
            log_level, f"步骤 {self.step_count}: {description}", extra=extra
        )
        self.last_checkpoint = current_time

    def checkpoint(self, name: str, data: Optional[Dict[str, Any]] = None):
        """记录检查点"""
        if not self.config["enable_checkpoint_logging"]:
            return

        current_time = time.time()
        checkpoint_duration = current_time - self.last_checkpoint
        total_duration = current_time - self.start_time

        extra = {
            "event": "function.internal.checkpoint",
            "function": self.function_name,
            "checkpoint_name": name,
            "checkpoint_duration_ms": round(checkpoint_duration * 1000, 2),
            "total_duration_ms": round(total_duration * 1000, 2),
        }

        if data:
            extra["checkpoint_data"] = {
                k: sanitize_value(v, max_length=100) for k, v in data.items()
            }

        self.logger.info(f"检查点: {name}", extra=extra)
        self.last_checkpoint = current_time

    def branch(self, condition: str, taken: bool, result: Any = None):
        """记录条件分支"""
        if not self.config["enable_branch_logging"]:
            return

        extra = {
            "event": "function.internal.branch",
            "function": self.function_name,
            "condition": condition,
            "branch_taken": taken,
        }

        if result is not None:
            extra["branch_result"] = sanitize_value(result, max_length=200)

        self.logger.debug(
            f"分支条件: {condition} -> {'执行' if taken else '跳过'}", extra=extra
        )

    def iteration_start(self, loop_name: str, total_items: int):
        """记录循环开始"""
        if not self.config["enable_iteration_logging"]:
            return

        extra = {
            "event": "function.internal.iteration.start",
            "function": self.function_name,
            "loop_name": loop_name,
            "total_items": total_items,
        }

        self.logger.info(f"开始循环: {loop_name}, 总项数: {total_items}", extra=extra)
        return IterationLogger(
            self.function_name, loop_name, total_items, self.logger, self.config
        )

    def validation(
        self, check_name: str, is_valid: bool, details: Optional[str] = None
    ):
        """记录数据验证"""
        if not self.config["enable_validation_logging"]:
            return

        extra = {
            "event": "function.internal.validation",
            "function": self.function_name,
            "validation_name": check_name,
            "is_valid": is_valid,
        }

        if details:
            extra["validation_details"] = details

        level = logging.INFO if is_valid else logging.WARNING
        status = "通过" if is_valid else "失败"
        self.logger.log(level, f"数据验证: {check_name} - {status}", extra=extra)

    def transformation(self, transform_name: str, input_info: str, output_info: str):
        """记录数据转换"""
        if not self.config["enable_transformation_logging"]:
            return

        extra = {
            "event": "function.internal.transformation",
            "function": self.function_name,
            "transformation_name": transform_name,
            "input_info": input_info,
            "output_info": output_info,
        }

        self.logger.info(
            f"数据转换: {transform_name} ({input_info} -> {output_info})", extra=extra
        )


class IterationLogger:
    """循环迭代日志记录器"""

    def __init__(
        self,
        function_name: str,
        loop_name: str,
        total_items: int,
        logger: logging.Logger,
        config: dict,
    ):
        self.function_name = function_name
        self.loop_name = loop_name
        self.total_items = total_items
        self.logger = logger
        self.config = config
        self.current_iteration = 0
        self.start_time = time.time()
        self.last_log_time = self.start_time

    def update(self, count: int = 1, item_info: Optional[str] = None):
        """更新迭代进度"""
        self.current_iteration += count
        current_time = time.time()

        # 按频率记录迭代进度
        if (
            self.current_iteration % self.config["iteration_log_frequency"] == 0
            or self.current_iteration >= self.total_items
        ):

            elapsed_time = current_time - self.start_time
            progress_percent = (
                (self.current_iteration / self.total_items * 100)
                if self.total_items > 0
                else 0
            )

            extra = {
                "event": "function.internal.iteration.progress",
                "function": self.function_name,
                "loop_name": self.loop_name,
                "current_iteration": self.current_iteration,
                "total_items": self.total_items,
                "progress_percent": round(progress_percent, 2),
                "elapsed_time_ms": round(elapsed_time * 1000, 2),
            }

            if item_info:
                extra["current_item_info"] = item_info

            # 估算剩余时间
            if self.current_iteration > 0:
                items_per_second = self.current_iteration / elapsed_time
                remaining_items = self.total_items - self.current_iteration
                estimated_remaining_time = (
                    remaining_items / items_per_second if items_per_second > 0 else 0
                )
                extra["estimated_remaining_ms"] = round(
                    estimated_remaining_time * 1000, 2
                )
                extra["items_per_second"] = round(items_per_second, 2)

            self.logger.info(
                f"循环进度: {self.loop_name} {self.current_iteration}/{self.total_items} ({progress_percent:.1f}%)",
                extra=extra,
            )
            self.last_log_time = current_time

    def complete(self, summary: Optional[str] = None):
        """完成循环"""
        end_time = time.time()
        total_time = end_time - self.start_time

        extra = {
            "event": "function.internal.iteration.complete",
            "function": self.function_name,
            "loop_name": self.loop_name,
            "total_items": self.total_items,
            "total_time_ms": round(total_time * 1000, 2),
            "items_per_second": (
                round(self.total_items / total_time, 2) if total_time > 0 else 0
            ),
        }

        if summary:
            extra["loop_summary"] = summary

        self.logger.info(
            f"循环完成: {self.loop_name}, 耗时 {total_time:.2f}秒", extra=extra
        )


def create_internal_step_logger(
    function_name: str,
    logger: Optional[logging.Logger] = None,
    settings: Optional[Any] = None,
) -> InternalStepLogger:
    """创建内部步骤日志记录器"""
    return InternalStepLogger(function_name, logger, settings)


def log_business_milestone(
    milestone_name: str,
    details: Dict[str, Any],
    logger: Optional[logging.Logger] = None,
):
    """
    记录业务里程碑

    Args:
        milestone_name: 里程碑名称
        details: 里程碑详细信息
        logger: 日志记录器
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    logger.info(
        f"业务里程碑: {milestone_name}",
        extra={
            "event": "business.milestone",
            "milestone_name": milestone_name,
            "details": {
                k: sanitize_value(v, max_length=200) for k, v in details.items()
            },
        },
    )


def log_data_quality_check(
    check_name: str,
    passed: bool,
    metrics: Dict[str, Any],
    logger: Optional[logging.Logger] = None,
):
    """
    记录数据质量检查结果

    Args:
        check_name: 检查名称
        passed: 检查是否通过
        metrics: 检查指标
        logger: 日志记录器
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    level = logging.INFO if passed else logging.WARNING
    status = "通过" if passed else "失败"

    logger.log(
        level,
        f"数据质量检查: {check_name} - {status}",
        extra={
            "event": "data.quality.check",
            "check_name": check_name,
            "passed": passed,
            "metrics": {
                k: sanitize_value(v, max_length=100) for k, v in metrics.items()
            },
        },
    )


def business_logger(context: str, enable_progress: bool = True):
    """
    业务日志装饰器

    Args:
        context: 业务上下文描述
        enable_progress: 是否启用进度记录
    """
    return enhanced_logger(
        log_entry=True,
        log_exit=True,
        log_parameters=True,
        log_performance=True,
        business_context=context,
    )


def performance_logger(enable_memory: bool = True):
    """
    性能监控装饰器

    Args:
        enable_memory: 是否启用内存监控
    """
    return enhanced_logger(
        log_entry=False,
        log_exit=True,
        log_parameters=False,
        log_performance=True,
        log_memory=enable_memory,
        business_context="性能监控",
    )


def key_metrics_logger(metrics_type: str):
    """
    关键指标日志装饰器

    Args:
        metrics_type: 指标类型（文件处理, 数据处理, 合并操作等）
    """
    return enhanced_logger(
        log_entry=True,
        log_exit=True,
        log_parameters=True,
        log_performance=True,
        log_memory=True,
        business_context=f"关键指标.{metrics_type}",
    )


def database_operation_logger():
    """数据库操作日志装饰器"""
    return enhanced_logger(
        log_entry=True,
        log_exit=True,
        log_parameters=False,  # 数据库参数可能包含敏感信息
        log_performance=True,
        business_context="数据库操作",
    )


def file_operation_logger():
    """文件操作日志装饰器"""
    return enhanced_logger(
        log_entry=True,
        log_exit=True,
        log_parameters=True,
        log_performance=True,
        business_context="文件操作",
    )


def data_processing_logger():
    """数据处理日志装饰器"""
    return enhanced_logger(
        log_entry=True,
        log_exit=True,
        log_parameters=True,
        log_performance=True,
        log_memory=True,
        business_context="数据处理",
    )


def sql_execution_logger():
    """
    SQL执行日志装饰器

        专门用于记录SQL执行相关的日志，包括：
        - SQL语句内容
        - 执行参数
        - 执行耗时
        - 影响行数
        - 错误信息
    """
    return enhanced_logger(
        log_entry=True,
        log_exit=True,
        log_parameters=False,  # SQL参数可能包含敏感信息，由专门函数处理
        log_performance=True,
        log_memory=False,
        business_context="SQL执行",
    )


class ProgressLogger:
    """进度日志记录器"""

    def __init__(
        self, operation: str, total: int, logger: Optional[logging.Logger] = None
    ):
        self.operation = operation
        self.total = total
        self.current = 0
        self.logger = logger or logging.getLogger(__name__)
        self.start_time = time.time()
        self.last_log_time = self.start_time
        self.log_interval = 5.0  # 每5秒记录一次进度

        # 记录开始
        self.logger.info(
            f"开始{operation}",
            extra={"event": "progress.start", "operation": operation, "total": total},
        )

    def update(self, count: int = 1, message: str = ""):
        """更新进度"""
        self.current += count
        current_time = time.time()

        # 检查是否需要记录进度
        if (
            current_time - self.last_log_time >= self.log_interval
            or self.current >= self.total
        ):

            progress_percent = (
                (self.current / self.total * 100) if self.total > 0 else 0
            )
            elapsed_time = current_time - self.start_time

            # 估算剩余时间
            if self.current > 0:
                estimated_total_time = elapsed_time * self.total / self.current
                remaining_time = estimated_total_time - elapsed_time
            else:
                remaining_time = 0

            extra = {
                "event": "progress.update",
                "operation": self.operation,
                "current": self.current,
                "total": self.total,
                "progress_percent": round(progress_percent, 2),
                "elapsed_seconds": round(elapsed_time, 2),
                "estimated_remaining_seconds": (
                    round(remaining_time, 2) if remaining_time > 0 else 0
                ),
            }

            if message:
                extra["message"] = message

            self.logger.info(
                f"{self.operation}进度: {self.current}/{self.total} ({progress_percent:.1f}%)",
                extra=extra,
            )

            self.last_log_time = current_time

    def complete(self, message: str = ""):
        """完成进度记录"""
        end_time = time.time()
        total_time = end_time - self.start_time

        extra = {
            "event": "progress.complete",
            "operation": self.operation,
            "total": self.total,
            "total_time_seconds": round(total_time, 2),
            "items_per_second": (
                round(self.total / total_time, 2) if total_time > 0 else 0
            ),
        }

        if message:
            extra["message"] = message

        self.logger.info(
            f"{self.operation}完成: {self.total}项, 耗时{total_time:.2f}秒", extra=extra
        )


def create_progress_logger(
    operation: str, total: int, logger: Optional[logging.Logger] = None
) -> ProgressLogger:
    """创建进度日志记录器"""
    return ProgressLogger(operation, total, logger)


def log_key_metrics(
    operation: str, metrics: Dict[str, Any], logger: Optional[logging.Logger] = None
):
    """
    记录关键指标

    Args:
        operation: 操作名称
        metrics: 指标字典
        logger: 日志记录器
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    logger.info(
        f"关键指标 - {operation}",
        extra={"event": f"key_metrics.{operation}", "metrics": metrics},
    )


def log_file_processing_metrics(
    file_count: int,
    total_size_mb: float,
    processing_time_seconds: float,
    success_count: int,
    error_count: int,
    logger: Optional[logging.Logger] = None,
):
    """记录文件处理指标"""
    metrics = {
        "file_count": file_count,
        "total_size_mb": total_size_mb,
        "processing_time_seconds": processing_time_seconds,
        "success_count": success_count,
        "error_count": error_count,
        "files_per_second": (
            round(file_count / processing_time_seconds, 2)
            if processing_time_seconds > 0
            else 0
        ),
        "mb_per_second": (
            round(total_size_mb / processing_time_seconds, 2)
            if processing_time_seconds > 0
            else 0
        ),
    }
    log_key_metrics("文件处理", metrics, logger)


def log_data_processing_metrics(
    rows_processed: int,
    rows_valid: int,
    rows_invalid: int,
    processing_time_seconds: float,
    data_time_range: Dict[str, str],
    logger: Optional[logging.Logger] = None,
):
    """记录数据处理指标"""
    metrics = {
        "rows_processed": rows_processed,
        "rows_valid": rows_valid,
        "rows_invalid": rows_invalid,
        "processing_time_seconds": processing_time_seconds,
        "rows_per_second": (
            round(rows_processed / processing_time_seconds, 2)
            if processing_time_seconds > 0
            else 0
        ),
        "success_rate": (
            round(rows_valid / rows_processed * 100, 2) if rows_processed > 0 else 0
        ),
        "data_time_range": data_time_range,
    }
    log_key_metrics("数据处理", metrics, logger)


def log_merge_statistics(
    input_rows: int,
    output_rows: int,
    duplicates_removed: int,
    merge_time_seconds: float,
    data_time_range: Dict[str, str],
    logger: Optional[logging.Logger] = None,
):
    """记录合并统计指标"""
    metrics = {
        "input_rows": input_rows,
        "output_rows": output_rows,
        "duplicates_removed": duplicates_removed,
        "merge_time_seconds": merge_time_seconds,
        "deduplication_rate": (
            round(duplicates_removed / input_rows * 100, 2) if input_rows > 0 else 0
        ),
        "rows_per_second": (
            round(output_rows / merge_time_seconds, 2) if merge_time_seconds > 0 else 0
        ),
        "data_time_range": data_time_range,
    }
    log_key_metrics("合并统计", metrics, logger)


def log_sql_execution(
    sql_type: str,
    sql_summary: str,
    execution_time_ms: float,
    affected_rows: int = 0,
    table_name: str = "",
    parameters: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
):
    """
    记录SQL执行日志

    Args:
        sql_type: SQL类型（SELECT, INSERT, UPDATE, DELETE, MERGE等）
        sql_summary: SQL语句摘要（去除敏感信息后的简要描述）
        execution_time_ms: 执行耗时（毫秒）
        affected_rows: 影响行数
        table_name: 目标表名
        parameters: SQL参数（会进行清理处理）
        error: 错误信息
        logger: 日志记录器
    """
    if logger is None:
        logger = logging.getLogger("sql")

    log_data = {
        "sql_type": sql_type,
        "sql_summary": sql_summary,
        "execution_time_ms": round(execution_time_ms, 2),
        "affected_rows": affected_rows,
        "table_name": table_name,
        "success": error is None,
    }

    # 清理和添加参数（去除敏感信息）
    if parameters:
        safe_params = {}
        for key, value in parameters.items():
            # 对于敏感参数进行脱敏处理
            if any(
                sensitive in key.lower()
                for sensitive in ["password", "token", "secret", "key"]
            ):
                safe_params[key] = "***"
            else:
                safe_params[key] = sanitize_value(value, max_length=200)
        log_data["parameters"] = safe_params

    if error:
        log_data["error"] = error
        logger.error(
            f"SQL执行失败 - {sql_type}: {sql_summary}",
            extra={"event": "sql.execution.failed", **log_data},
        )
    else:
        logger.info(
            f"SQL执行成功 - {sql_type}: {sql_summary}",
            extra={"event": "sql.execution.success", **log_data},
        )


def log_sql_statement(
    sql: str,
    parameters: Optional[Dict[str, Any]] = None,
    logger: Optional[logging.Logger] = None,
):
    """
    记录完整的SQL语句（仅在DEBUG级别）

    Args:
        sql: 完整的SQL语句
        parameters: SQL参数
        logger: 日志记录器
    """
    if logger is None:
        logger = logging.getLogger("sql")

    # 仅在DEBUG级别输出完整SQL
    if logger.isEnabledFor(logging.DEBUG):
        log_data = {
            "sql_statement": sql.strip(),
            "parameter_count": len(parameters) if parameters else 0,
        }

        if parameters:
            # 对参数进行脱敏处理
            safe_params = {}
            for key, value in parameters.items():
                if any(
                    sensitive in str(key).lower()
                    for sensitive in ["password", "token", "secret"]
                ):
                    safe_params[key] = "***"
                else:
                    safe_params[key] = sanitize_value(value, max_length=100)
            log_data["parameters"] = safe_params

        logger.debug("执行SQL语句", extra={"event": "sql.statement.debug", **log_data})


def create_sql_logger(operation: str) -> Callable:
    """
    创建一个SQL执行日志装饰器

    Args:
        operation: 操作名称（如"合并数据"、"查询用户"等）

    Returns:
        装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger("sql")
            func_name = f"{func.__module__}.{func.__qualname__}"

            logger.debug(
                f"开始{operation} - {func_name}",
                extra={
                    "event": "sql.operation.start",
                    "operation": operation,
                    "function": func_name,
                },
            )

            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000

                logger.info(
                    f"{operation}成功 - {func_name}",
                    extra={
                        "event": "sql.operation.success",
                        "operation": operation,
                        "function": func_name,
                        "duration_ms": round(duration, 2),
                    },
                )

                return result
            except Exception as e:
                duration = (time.time() - start_time) * 1000

                logger.error(
                    f"{operation}失败 - {func_name}: {e}",
                    extra={
                        "event": "sql.operation.failed",
                        "operation": operation,
                        "function": func_name,
                        "duration_ms": round(duration, 2),
                        "error": str(e),
                    },
                )
                raise

        return wrapper

    return decorator
