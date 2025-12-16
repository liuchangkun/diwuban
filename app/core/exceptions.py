"""
统一异常定义和错误处理机制（app.core.exceptions）

本模块定义了项目中使用的标准异常类型和错误处理装饰器，确保：
- 异常信息结构化和标准化
- 错误处理逻辑统一化
- 日志记录的一致性
- 调试信息的完整性

使用方式：
1. 业务异常继承对应的基础异常类
2. 使用 @error_handler 装饰器包装关键函数
3. 在边界层（CLI/API）进行统一异常捕获和处理
"""

from __future__ import annotations

import time
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union

# 类型变量定义
F = TypeVar("F", bound=Callable[..., Any])


class _NoopLogger:
    def __getattr__(self, name):
        return lambda *a, **k: None


logger = _NoopLogger()


class ErrorSeverity(Enum):
    """错误严重程度分级"""

    LOW = "low"  # 可忽略的错误，不影响主要功能
    MEDIUM = "medium"  # 需要重试的错误，可能影响性能
    HIGH = "high"  # 需要立即处理的错误，影响功能
    CRITICAL = "critical"  # 系统级错误，可能导致服务不可用


class RecoveryAction(Enum):
    """错误恢复动作"""

    RETRY = "retry"  # 重试操作
    FALLBACK = "fallback"  # 使用备用方案
    DEGRADE = "degrade"  # 降级服务
    RESTART = "restart"  # 重启组件
    MANUAL_INTERVENTION = "manual"  # 需要人工干预
    IGNORE = "ignore"  # 忽略错误


class BaseAppException(Exception):
    """
    应用程序基础异常类

    所有业务异常都应该继承此类，提供：
    - 结构化的错误信息
    - 错误代码支持
    - 上下文信息记录
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        recovery_action: RecoveryAction = RecoveryAction.RETRY,
        recovery_suggestion: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}
        self.cause = cause
        self.severity = severity
        self.recovery_action = recovery_action
        self.recovery_suggestion = (
            recovery_suggestion or self._get_default_recovery_suggestion()
        )
        self.timestamp = time.time()

    def _get_default_recovery_suggestion(self) -> str:
        """获取默认的恢复建议"""
        suggestions = {
            RecoveryAction.RETRY: "请稍后重试操作",
            RecoveryAction.FALLBACK: "系统将使用备用方案",
            RecoveryAction.DEGRADE: "系统将降级运行",
            RecoveryAction.RESTART: "建议重启相关组件",
            RecoveryAction.MANUAL_INTERVENTION: "需要人工检查和处理",
            RecoveryAction.IGNORE: "此错误可以忽略",
        }
        return suggestions.get(self.recovery_action, "请联系系统管理员")

    def to_dict(self) -> Dict[str, Any]:
        """将异常信息转换为字典格式，便于日志记录和API返回"""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context,
            "timestamp": self.timestamp,
            "cause": str(self.cause) if self.cause else None,
            "severity": self.severity.value,
            "recovery_action": self.recovery_action.value,
            "recovery_suggestion": self.recovery_suggestion,
        }


class ConfigurationError(BaseAppException):
    """配置相关错误"""

    pass


class DatabaseError(BaseAppException):
    """数据库操作错误"""

    pass


class DatabaseConnectionError(DatabaseError):
    """数据库连接错误"""

    def __init__(self, message: str, **kwargs):
        # 设置默认值，但允许被 kwargs 覆盖
        defaults = {
            "severity": ErrorSeverity.HIGH,
            "recovery_action": RecoveryAction.RETRY,
            "recovery_suggestion": "检查数据库连接配置和网络状态",
        }
        # 合并默认值和传入的参数，传入的参数优先
        merged_kwargs = {**defaults, **kwargs}
        super().__init__(message, **merged_kwargs)


class DatabaseTimeoutError(DatabaseError):
    """数据库超时错误"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            recovery_action=RecoveryAction.RETRY,
            recovery_suggestion="增加超时时间或优化查询性能",
            **kwargs,
        )


class DatabaseNetworkError(DatabaseConnectionError):
    """数据库网络连接错误"""

    def __init__(self, message: str, **kwargs):
        # 设置默认值，但允许被 kwargs 覆盖
        defaults = {
            "recovery_suggestion": "检查网络连接和数据库服务状态",
        }
        # 合并默认值和传入的参数，传入的参数优先
        merged_kwargs = {**defaults, **kwargs}
        super().__init__(message, **merged_kwargs)


class DatabaseAuthenticationError(DatabaseError):
    """数据库认证错误"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.CRITICAL,
            recovery_action=RecoveryAction.MANUAL_INTERVENTION,
            recovery_suggestion="检查数据库用户名、密码和权限配置",
            **kwargs,
        )


class DatabaseResourceExhaustedError(DatabaseError):
    """数据库资源耗尽错误（连接数、内存等）"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            recovery_action=RecoveryAction.DEGRADE,
            recovery_suggestion="减少并发连接数或增加数据库资源",
            **kwargs,
        )


class DatabaseSchemaError(DatabaseError):
    """数据库模式错误（表不存在、字段错误等）"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.CRITICAL,
            recovery_action=RecoveryAction.MANUAL_INTERVENTION,
            recovery_suggestion="检查数据库模式和表结构",
            **kwargs,
        )


class PoolError(DatabaseError):
    """连接池错误基类"""

    def __init__(self, message: str, **kwargs):
        # 设置默认值，但允许被 kwargs 覆盖
        defaults = {
            "severity": ErrorSeverity.HIGH,
            "recovery_action": RecoveryAction.RESTART,
            "recovery_suggestion": "重启连接池或检查连接池配置",
        }
        # 合并默认值和传入的参数，传入的参数优先
        merged_kwargs = {**defaults, **kwargs}
        super().__init__(message, **merged_kwargs)


class PoolExhaustedError(PoolError):
    """连接池耗尽错误"""

    def __init__(self, message: str, **kwargs):
        # 设置默认值，但允许被 kwargs 覆盖
        defaults = {
            "recovery_action": RecoveryAction.DEGRADE,
            "recovery_suggestion": "增加连接池大小或减少并发请求",
        }
        # 合并默认值和传入的参数，传入的参数优先
        merged_kwargs = {**defaults, **kwargs}
        super().__init__(message, **merged_kwargs)


class PoolShutdownError(PoolError):
    """连接池关闭错误"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.CRITICAL,
            recovery_action=RecoveryAction.RESTART,
            recovery_suggestion="重新初始化连接池",
            **kwargs,
        )


class PoolValidationError(PoolError):
    """连接池验证错误"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            recovery_action=RecoveryAction.RETRY,
            recovery_suggestion="检查连接健康状态和验证逻辑",
            **kwargs,
        )


class DataValidationError(BaseAppException):
    """数据验证错误"""

    pass


class FileProcessingError(BaseAppException):
    """文件处理错误"""

    pass


class DataImportError(BaseAppException):
    """数据导入错误"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            recovery_action=RecoveryAction.RETRY,
            recovery_suggestion="检查数据格式和完整性后重试",
            **kwargs,
        )


class OptimizationError(BaseAppException):
    """优化计算错误"""

    pass


class CurveFittingError(BaseAppException):
    """曲线拟合错误"""

    pass


# 可重试的异常类型（主要是临时性错误）
RETRYABLE_EXCEPTIONS = (
    DatabaseConnectionError,
    DatabaseTimeoutError,
    DatabaseNetworkError,
    DatabaseResourceExhaustedError,
    PoolExhaustedError,
    PoolValidationError,
)

# 不可重试的异常类型（主要是逻辑错误或配置错误）
NON_RETRYABLE_EXCEPTIONS = (
    ConfigurationError,
    DataValidationError,
    DatabaseAuthenticationError,
    DatabaseSchemaError,
    PoolShutdownError,
)

# 需要立即处理的异常类型（高优先级）
HIGH_PRIORITY_EXCEPTIONS = (
    DatabaseAuthenticationError,
    DatabaseSchemaError,
    PoolShutdownError,
)

# 需要降级处理的异常类型
DEGRADABLE_EXCEPTIONS = (
    DatabaseResourceExhaustedError,
    PoolExhaustedError,
)


def error_handler(
    logger_name: Optional[str] = None,
    log_level: int = 40,
    reraise: bool = True,
    context_fields: Optional[list[str]] = None,
) -> Callable[[F], F]:
    """
    统一错误处理装饰器

    功能：
    - 自动记录异常信息到日志
    - 提供结构化的上下文信息
    - 支持异常转换和重新抛出
    - 支持自定义日志记录器和级别

    参数：
        logger_name: 自定义日志记录器名称，默认使用被装饰函数的模块名
        log_level: 日志级别，默认为 ERROR
        reraise: 是否重新抛出异常，默认为 True
        context_fields: 从函数参数中提取的上下文字段列表

    使用示例：
        @error_handler(context_fields=['file_path', 'station_id'])
        def process_file(file_path: str, station_id: int) -> None:
            # 函数实现
            pass
    """

    def decorator(func: F) -> F:
        class _Noop:
            def __getattr__(self, name):
                return lambda *a, **k: None

        func_logger = _Noop()

        @wraps(func)
        def wrapper(*args, **kwargs):
            # 构建上下文信息
            context = {
                "function": func.__name__,
                "module": func.__module__,
            }

            # 提取指定的上下文字段
            if context_fields:
                import inspect

                sig = inspect.signature(func)
                bound_args = sig.bind_partial(*args, **kwargs)
                bound_args.apply_defaults()

                for field in context_fields:
                    if field in bound_args.arguments:
                        context[field] = bound_args.arguments[field]

            try:
                return func(*args, **kwargs)
            except BaseAppException as e:
                # 应用程序异常，已经结构化，直接记录
                context.update(e.context)
                pass
                if reraise:
                    raise

            except Exception as e:
                # 未预期的异常，包装为应用异常
                pass
                if reraise:
                    raise BaseAppException(
                        f"函数 {func.__name__} 执行失败: {str(e)}",
                        error_code="UNEXPECTED_ERROR",
                        context=context,
                        cause=e,
                    ) from e

        return wrapper  # type: ignore

    return decorator


def retry_on_error(
    exceptions: Union[
        Type[Exception], tuple[Type[Exception], ...]
    ] = RETRYABLE_EXCEPTIONS,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_multiplier: float = 2.0,
    jitter: bool = True,
) -> Callable[[F], F]:
    """
    带指数退避的重试装饰器

    参数：
        exceptions: 需要重试的异常类型
        max_retries: 最大重试次数
        base_delay: 基础延迟时间（秒）
        max_delay: 最大延迟时间（秒）
        backoff_multiplier: 退避倍数
        jitter: 是否添加随机抖动
    """
    import random

    if isinstance(exceptions, type):
        exceptions = (exceptions,)

    def decorator(func: F) -> F:
        class _Noop:
            def __getattr__(self, name):
                return lambda *a, **k: None

        func_logger = _Noop()

        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        break

                    # 计算延迟时间
                    delay = min(base_delay * (backoff_multiplier**attempt), max_delay)

                    if jitter:
                        delay += random.uniform(0, delay * 0.1)  # 添加10%的抖动

                    pass

                    time.sleep(delay)
                except Exception as e:
                    # 非可重试异常，直接抛出
                    pass
                    raise

            # 重试次数耗尽，抛出最后的异常
            if last_exception:
                raise last_exception

        return wrapper  # type: ignore

    return decorator


def safe_execute(
    func: Callable[..., Any],
    *args,
    default_return: Any = None,
    log_errors: bool = True,
    **kwargs,
) -> Any:
    """
    安全执行函数，捕获所有异常并返回默认值

    适用于非关键路径的操作，如统计信息收集、缓存更新等

    参数：
        func: 要执行的函数
        *args: 函数位置参数
        default_return: 异常时的默认返回值
        log_errors: 是否记录错误日志
        **kwargs: 函数关键字参数

    返回：
        函数执行结果或默认值
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            pass
        return default_return
