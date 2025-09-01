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

import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union

# 类型变量定义
F = TypeVar('F', bound=Callable[..., Any])

logger = logging.getLogger(__name__)


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
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}
        self.cause = cause
        self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """将异常信息转换为字典格式，便于日志记录和API返回"""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context,
            "timestamp": self.timestamp,
            "cause": str(self.cause) if self.cause else None
        }


class ConfigurationError(BaseAppException):
    """配置相关错误"""
    pass


class DatabaseError(BaseAppException):
    """数据库操作错误"""
    pass


class DatabaseConnectionError(DatabaseError):
    """数据库连接错误"""
    pass


class DatabaseTimeoutError(DatabaseError):
    """数据库超时错误"""
    pass


class DataValidationError(BaseAppException):
    """数据验证错误"""
    pass


class FileProcessingError(BaseAppException):
    """文件处理错误"""
    pass


class ImportError(BaseAppException):
    """数据导入错误"""
    pass


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
)

# 不可重试的异常类型（主要是逻辑错误或配置错误）
NON_RETRYABLE_EXCEPTIONS = (
    ConfigurationError,
    DataValidationError,
)


def error_handler(
    logger_name: Optional[str] = None,
    log_level: int = logging.ERROR,
    reraise: bool = True,
    context_fields: Optional[list[str]] = None
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
        func_logger = logging.getLogger(logger_name or func.__module__)
        
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
                func_logger.log(
                    log_level,
                    f"应用异常: {e.message}",
                    extra={
                        "event": "app.error",
                        "extra": {
                            **context,
                            **e.to_dict()
                        }
                    },
                    exc_info=log_level >= logging.ERROR
                )
                if reraise:
                    raise
                
            except Exception as e:
                # 未预期的异常，包装为应用异常
                func_logger.log(
                    log_level,
                    f"未预期异常: {str(e)}",
                    extra={
                        "event": "app.unexpected_error",
                        "extra": {
                            **context,
                            "error_type": type(e).__name__,
                            "error_message": str(e)
                        }
                    },
                    exc_info=True
                )
                if reraise:
                    raise BaseAppException(
                        f"函数 {func.__name__} 执行失败: {str(e)}",
                        error_code="UNEXPECTED_ERROR",
                        context=context,
                        cause=e
                    ) from e
        
        return wrapper  # type: ignore
    
    return decorator


def retry_on_error(
    exceptions: Union[Type[Exception], tuple[Type[Exception], ...]] = RETRYABLE_EXCEPTIONS,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_multiplier: float = 2.0,
    jitter: bool = True
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
        func_logger = logging.getLogger(func.__module__)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        func_logger.error(
                            f"函数 {func.__name__} 重试失败，已达最大重试次数",
                            extra={
                                "event": "retry.exhausted",
                                "extra": {
                                    "function": func.__name__,
                                    "max_retries": max_retries,
                                    "final_error": str(e),
                                    "error_type": type(e).__name__
                                }
                            }
                        )
                        break
                    
                    # 计算延迟时间
                    delay = min(
                        base_delay * (backoff_multiplier ** attempt),
                        max_delay
                    )
                    
                    if jitter:
                        delay += random.uniform(0, delay * 0.1)  # 添加10%的抖动
                    
                    func_logger.warning(
                        f"函数 {func.__name__} 执行失败，准备重试",
                        extra={
                            "event": "retry.attempt",
                            "extra": {
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "max_retries": max_retries,
                                "delay_seconds": delay,
                                "error": str(e),
                                "error_type": type(e).__name__
                            }
                        }
                    )
                    
                    time.sleep(delay)
                except Exception as e:
                    # 非可重试异常，直接抛出
                    func_logger.error(
                        f"函数 {func.__name__} 遇到不可重试异常",
                        extra={
                            "event": "retry.non_retryable",
                            "extra": {
                                "function": func.__name__,
                                "error": str(e),
                                "error_type": type(e).__name__
                            }
                        },
                        exc_info=True
                    )
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
    **kwargs
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
            logger.warning(
                f"安全执行函数 {func.__name__} 失败",
                extra={
                    "event": "safe_execute.error",
                    "extra": {
                        "function": func.__name__,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "default_return": default_return
                    }
                }
            )
        return default_return