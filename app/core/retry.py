"""
智能重试机制模块（app.core.retry）

本模块提供智能的重试策略，根据错误类型和严重程度自动调整重试参数：
- 基于错误类型的重试策略
- 指数退避和抖动算法
- 重试统计和监控
- 断路器模式集成

使用方式：
1. 使用 @smart_retry 装饰器进行智能重试
2. 使用 RetryManager 进行复杂的重试管理
3. 使用 RetryPolicy 定义自定义重试策略

设计原则：
- 根据错误类型智能调整重试策略
- 提供详细的重试统计和监控
- 支持断路器模式防止级联故障
- 向后兼容现有重试机制
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union

from app.core.exceptions import (
    BaseAppException,
    ErrorSeverity,
    RecoveryAction,
    RETRYABLE_EXCEPTIONS,
    NON_RETRYABLE_EXCEPTIONS,
    HIGH_PRIORITY_EXCEPTIONS,
    DEGRADABLE_EXCEPTIONS,
)

# 类型变量定义
F = TypeVar("F", bound=Callable[..., Any])


import logging

_act = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """重试策略类型"""

    FIXED = "fixed"  # 固定延迟
    LINEAR = "linear"  # 线性增长
    EXPONENTIAL = "exponential"  # 指数退避
    FIBONACCI = "fibonacci"  # 斐波那契序列


@dataclass
class RetryPolicy:
    """重试策略配置"""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    retry_on: tuple[Type[Exception], ...] = RETRYABLE_EXCEPTIONS
    stop_on: tuple[Type[Exception], ...] = NON_RETRYABLE_EXCEPTIONS


@dataclass
class RetryStats:
    """重试统计信息"""

    total_attempts: int = 0
    successful_retries: int = 0
    failed_retries: int = 0
    total_delay: float = 0.0
    error_counts: Dict[str, int] = None

    def __post_init__(self):
        if self.error_counts is None:
            self.error_counts = {}


class RetryManager:
    """重试管理器"""

    def __init__(self, retry_settings=None):
        self.stats = RetryStats()
        self.retry_settings = retry_settings
        self.policies = self._get_default_policies()

    def _get_default_policies(self) -> Dict[Type[Exception], RetryPolicy]:
        """获取默认的重试策略"""
        if self.retry_settings:
            # 从配置文件加载策略
            return {
                Exception: self._config_to_policy(self.retry_settings.default),
                BaseAppException: self._config_to_policy(
                    self.retry_settings.database_connection_errors
                ),
            }
        else:
            # 使用硬编码的默认策略（向后兼容）
            return {
                # 网络相关错误：快速重试
                Exception: RetryPolicy(
                    max_retries=3,
                    base_delay=0.5,
                    max_delay=10.0,
                    backoff_multiplier=1.5,
                    strategy=RetryStrategy.EXPONENTIAL,
                ),
                # 数据库连接错误：中等重试
                BaseAppException: RetryPolicy(
                    max_retries=5,
                    base_delay=1.0,
                    max_delay=30.0,
                    backoff_multiplier=2.0,
                    strategy=RetryStrategy.EXPONENTIAL,
                ),
            }

    def _config_to_policy(self, config) -> RetryPolicy:
        """将配置转换为重试策略"""
        strategy_map = {
            "fixed": RetryStrategy.FIXED,
            "linear": RetryStrategy.LINEAR,
            "exponential": RetryStrategy.EXPONENTIAL,
            "fibonacci": RetryStrategy.FIBONACCI,
        }

        return RetryPolicy(
            max_retries=config.max_retries,
            base_delay=config.base_delay,
            max_delay=config.max_delay,
            backoff_multiplier=config.backoff_multiplier,
            jitter=config.jitter,
            strategy=strategy_map.get(config.strategy, RetryStrategy.EXPONENTIAL),
            retry_on=RETRYABLE_EXCEPTIONS,
            stop_on=NON_RETRYABLE_EXCEPTIONS,
        )

    def get_policy_for_exception(self, exception: Exception) -> RetryPolicy:
        """根据异常类型获取重试策略"""
        # 检查是否为不可重试异常
        if isinstance(exception, NON_RETRYABLE_EXCEPTIONS):
            return RetryPolicy(max_retries=0)

        # 检查是否为高优先级异常（需要快速处理）
        if isinstance(exception, HIGH_PRIORITY_EXCEPTIONS):
            if self.retry_settings:
                return self._config_to_policy(self.retry_settings.high_priority_errors)
            else:
                return RetryPolicy(
                    max_retries=2, base_delay=0.1, max_delay=1.0, backoff_multiplier=1.2
                )

        # 检查是否为可降级异常
        if isinstance(exception, DEGRADABLE_EXCEPTIONS):
            if self.retry_settings:
                return self._config_to_policy(self.retry_settings.degradable_errors)
            else:
                return RetryPolicy(
                    max_retries=2,
                    base_delay=2.0,
                    max_delay=10.0,
                    backoff_multiplier=1.5,
                )

        # 根据异常类型查找策略
        for exc_type, policy in self.policies.items():
            if isinstance(exception, exc_type):
                return policy

        # 默认策略
        return self.policies[Exception]

    def calculate_delay(self, attempt: int, policy: RetryPolicy) -> float:
        """计算延迟时间"""
        if policy.strategy == RetryStrategy.FIXED:
            delay = policy.base_delay
        elif policy.strategy == RetryStrategy.LINEAR:
            delay = policy.base_delay * (attempt + 1)
        elif policy.strategy == RetryStrategy.EXPONENTIAL:
            delay = policy.base_delay * (policy.backoff_multiplier**attempt)
        elif policy.strategy == RetryStrategy.FIBONACCI:
            delay = policy.base_delay * self._fibonacci(attempt + 1)
        else:
            delay = policy.base_delay

        # 应用最大延迟限制
        delay = min(delay, policy.max_delay)

        # 添加抖动
        if policy.jitter:
            jitter_amount = delay * 0.1 * random.random()
            delay += jitter_amount

        return delay

    def _fibonacci(self, n: int) -> int:
        """计算斐波那契数列"""
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b

    def record_attempt(self, exception: Exception, success: bool, delay: float = 0.0):
        """记录重试尝试"""
        self.stats.total_attempts += 1
        self.stats.total_delay += delay

        error_type = type(exception).__name__
        self.stats.error_counts[error_type] = (
            self.stats.error_counts.get(error_type, 0) + 1
        )

        if success:
            self.stats.successful_retries += 1
        else:
            self.stats.failed_retries += 1


# 全局重试管理器实例
_retry_manager = RetryManager()


def smart_retry(
    policy: Optional[RetryPolicy] = None,
    logger_name: Optional[str] = None,
) -> Callable[[F], F]:
    """
    智能重试装饰器

    根据异常类型自动选择重试策略，提供详细的重试统计和监控。

    参数：
        policy: 自定义重试策略，如果不提供则根据异常类型自动选择
        logger_name: 自定义日志记录器名称

    使用示例：
        @smart_retry()
        def database_operation():
            # 数据库操作
            pass

        @smart_retry(policy=RetryPolicy(max_retries=5))
        def custom_operation():
            # 自定义重试策略的操作
            pass
    """

    def decorator(func: F) -> F:
        class _Noop:
            def __getattr__(self, name):
                return lambda *a, **k: None

        func_logger = _Noop()

        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            used_policy = None

            # 第一次尝试（不算重试）
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                # 确定重试策略
                if policy is not None:
                    used_policy = policy
                else:
                    used_policy = _retry_manager.get_policy_for_exception(e)

                # 如果不允许重试，直接抛出异常
                if used_policy.max_retries == 0:
                    raise

            # 开始重试
            for attempt in range(used_policy.max_retries):
                try:
                    # 计算延迟时间
                    delay = _retry_manager.calculate_delay(attempt, used_policy)

                    _act.info(
                        "[核心-重试] [重试尝试]",
                        extra={
                            "extra_data": {
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "max_retries": used_policy.max_retries,
                                "delay_seconds": delay,
                                "exception_type": type(last_exception).__name__,
                                "strategy": used_policy.strategy.value,
                            }
                        },
                    )

                    # 等待延迟时间
                    time.sleep(delay)

                    # 记录重试尝试
                    _retry_manager.record_attempt(last_exception, False, delay)

                    # 重试执行
                    result = func(*args, **kwargs)

                    # 重试成功
                    _retry_manager.record_attempt(last_exception, True)
                    _act.info(
                        "[核心-重试] [重试成功]",
                        extra={
                            "extra_data": {
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "total_attempts": attempt + 2,
                            }
                        },
                    )
                    return result

                except Exception as e:
                    last_exception = e

                    # 检查是否为不可重试异常
                    if isinstance(e, used_policy.stop_on):
                        _act.warning(
                            "[核心-重试] [不可重试异常]",
                            extra={
                                "extra_data": {
                                    "function": func.__name__,
                                    "exception_type": type(e).__name__,
                                    "attempt": attempt + 1,
                                }
                            },
                        )
                        break

            # 重试次数耗尽
            _retry_manager.record_attempt(last_exception, False)
            _act.error(
                "[核心-重试] [重试耗尽]",
                extra={
                    "extra_data": {
                        "function": func.__name__,
                        "max_retries": used_policy.max_retries,
                        "exception_type": type(last_exception).__name__ if last_exception else None,
                    }
                },
            )

            # 抛出最后的异常
            if last_exception:
                raise last_exception

        return wrapper  # type: ignore

    return decorator


# 全局重试管理器实例
_retry_manager = RetryManager()


def initialize_retry_manager(retry_settings=None):
    """初始化全局重试管理器"""
    global _retry_manager
    _retry_manager = RetryManager(retry_settings)


def get_retry_manager() -> RetryManager:
    """获取全局重试管理器"""
    return _retry_manager


def get_retry_stats() -> RetryStats:
    """获取全局重试统计信息"""
    return _retry_manager.stats


def reset_retry_stats():
    """重置重试统计信息"""
    _retry_manager.stats = RetryStats()
