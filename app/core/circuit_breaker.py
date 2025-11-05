"""
断路器模式实现（app.core.circuit_breaker）

本模块实现断路器模式，用于防止级联故障和提高系统稳定性：
- 三种状态：CLOSED（正常）、OPEN（断开）、HALF_OPEN（半开）
- 失败阈值和恢复超时配置
- 自动状态转换和监控
- 与重试机制集成

使用方式：
1. 使用 @circuit_breaker 装饰器保护关键函数
2. 使用 CircuitBreaker 类进行手动控制
3. 监控断路器状态和统计信息

设计原则：
- 快速失败，避免长时间等待
- 自动恢复，减少人工干预
- 详细监控，便于问题诊断
- 灵活配置，适应不同场景
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar

from app.core.exceptions import BaseAppException, ErrorSeverity

# 类型变量定义
F = TypeVar("F", bound=Callable[..., Any])


import logging

_act = logging.getLogger(__name__)


class CircuitState(Enum):
    """断路器状态"""

    CLOSED = "closed"  # 正常状态，允许请求通过
    OPEN = "open"  # 断开状态，拒绝请求
    HALF_OPEN = "half_open"  # 半开状态，允许少量请求测试


@dataclass
class CircuitBreakerConfig:
    """断路器配置"""

    failure_threshold: int = 5  # 失败阈值
    recovery_timeout: float = 60.0  # 恢复超时时间（秒）
    expected_exception: type = Exception  # 预期的异常类型
    name: str = "default"  # 断路器名称

    # 半开状态配置
    half_open_max_calls: int = 3  # 半开状态最大调用次数
    half_open_success_threshold: int = 2  # 半开状态成功阈值


@dataclass
class CircuitBreakerStats:
    """断路器统计信息"""

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    state_changes: int = 0
    last_failure_time: float = 0.0
    last_success_time: float = 0.0
    current_consecutive_failures: int = 0
    current_consecutive_successes: int = 0
    state_durations: Dict[str, float] = field(default_factory=dict)


class CircuitBreakerError(BaseAppException):
    """断路器错误"""

    def __init__(self, message: str, circuit_name: str, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            context={"circuit_name": circuit_name},
            **kwargs,
        )


class CircuitBreaker:
    """断路器实现"""

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self.last_failure_time = 0.0
        self.half_open_calls = 0
        self.half_open_successes = 0
        self._lock = threading.RLock()
        self._state_change_time = time.time()

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """通过断路器调用函数"""
        with self._lock:
            self.stats.total_calls += 1

            # 检查断路器状态
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to_half_open()
                else:
                    self._record_blocked_call()
                    _act.warning(
                        "[核心-熔断] [拒绝调用]",
                        extra={
                            "extra_data": {
                                "circuit_name": self.config.name,
                                "state": self.state.value,
                                "total_calls": self.stats.total_calls,
                                "failed_calls": self.stats.failed_calls,
                            }
                        },
                    )
                    raise CircuitBreakerError(
                        f"断路器 '{self.config.name}' 处于开启状态，拒绝调用",
                        circuit_name=self.config.name,
                    )

            elif self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls >= self.config.half_open_max_calls:
                    self._record_blocked_call()
                    raise CircuitBreakerError(
                        f"断路器 '{self.config.name}' 半开状态调用次数已达上限",
                        circuit_name=self.config.name,
                    )

        # 执行函数调用
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result

        except Exception:
            self._record_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """检查是否应该尝试重置断路器"""
        return time.time() - self.last_failure_time >= self.config.recovery_timeout

    def _transition_to_half_open(self):
        """转换到半开状态"""
        old_state = self.state
        self.state = CircuitState.HALF_OPEN
        self.half_open_calls = 0
        self.half_open_successes = 0
        _act.info(
            "[核心-熔断] [状态转换-半开]",
            extra={
                "extra_data": {
                    "circuit_name": self.config.name,
                    "from_state": old_state.value,
                    "to_state": CircuitState.HALF_OPEN.value,
                    "total_calls": self.stats.total_calls,
                    "failed_calls": self.stats.failed_calls,
                }
            },
        )
        self._record_state_change(old_state, CircuitState.HALF_OPEN)

    def _transition_to_open(self):
        """转换到开启状态"""
        old_state = self.state
        self.state = CircuitState.OPEN
        self.last_failure_time = time.time()
        _act.warning(
            "[核心-熔断] [状态转换-开启]",
            extra={
                "extra_data": {
                    "circuit_name": self.config.name,
                    "from_state": old_state.value,
                    "consecutive_failures": self.stats.current_consecutive_failures,
                    "failure_threshold": self.config.failure_threshold,
                    "total_calls": self.stats.total_calls,
                    "failed_calls": self.stats.failed_calls,
                }
            },
        )
        self._record_state_change(old_state, CircuitState.OPEN)

    def _transition_to_closed(self):
        """转换到关闭状态"""
        old_state = self.state
        self.state = CircuitState.CLOSED
        self.stats.current_consecutive_failures = 0
        _act.info(
            "[核心-熔断] [状态转换-关闭]",
            extra={
                "extra_data": {
                    "circuit_name": self.config.name,
                    "from_state": old_state.value,
                    "half_open_successes": self.half_open_successes,
                    "success_threshold": self.config.half_open_success_threshold,
                    "total_calls": self.stats.total_calls,
                    "successful_calls": self.stats.successful_calls,
                }
            },
        )
        self._record_state_change(old_state, CircuitState.CLOSED)

    def _record_success(self):
        """记录成功调用"""
        with self._lock:
            self.stats.successful_calls += 1
            self.stats.current_consecutive_successes += 1
            self.stats.current_consecutive_failures = 0
            self.stats.last_success_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                self.half_open_calls += 1
                self.half_open_successes += 1

                # 检查是否应该关闭断路器
                if self.half_open_successes >= self.config.half_open_success_threshold:
                    self._transition_to_closed()

    def _record_failure(self):
        """记录失败调用"""
        with self._lock:
            self.stats.failed_calls += 1
            self.stats.current_consecutive_failures += 1
            self.stats.current_consecutive_successes = 0
            self.stats.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                self.half_open_calls += 1
                # 半开状态下的失败直接转换到开启状态
                self._transition_to_open()
            elif self.state == CircuitState.CLOSED:
                # 检查是否应该开启断路器
                if (
                    self.stats.current_consecutive_failures
                    >= self.config.failure_threshold
                ):
                    self._transition_to_open()

    def _record_blocked_call(self):
        """记录被阻止的调用"""

    def _record_state_change(self, old_state: CircuitState, new_state: CircuitState):
        """记录状态变化"""
        current_time = time.time()
        duration = current_time - self._state_change_time

        self.stats.state_changes += 1
        self.stats.state_durations[old_state.value] = (
            self.stats.state_durations.get(old_state.value, 0) + duration
        )
        self._state_change_time = current_time

    def get_state(self) -> CircuitState:
        """获取当前状态"""
        return self.state

    def get_stats(self) -> CircuitBreakerStats:
        """获取统计信息"""
        return self.stats

    def reset(self):
        """手动重置断路器"""
        with self._lock:
            old_state = self.state
            self.state = CircuitState.CLOSED
            self.stats.current_consecutive_failures = 0
            self.half_open_calls = 0
            self.half_open_successes = 0
            self._record_state_change(old_state, CircuitState.CLOSED)


# 全局断路器注册表
_circuit_breakers: Dict[str, CircuitBreaker] = {}
_circuit_breaker_settings = None
_registry_lock = threading.RLock()


def get_circuit_breaker(
    name: str, config: Optional[CircuitBreakerConfig] = None
) -> CircuitBreaker:
    """获取或创建断路器"""
    with _registry_lock:
        if name not in _circuit_breakers:
            if config is None:
                # 尝试从全局配置获取
                config = _get_config_for_breaker(name)
            _circuit_breakers[name] = CircuitBreaker(config)
        return _circuit_breakers[name]


def _get_config_for_breaker(name: str) -> CircuitBreakerConfig:
    """根据断路器名称获取配置"""
    if _circuit_breaker_settings:
        # 根据名称映射到配置
        config_map = {
            "database_operations": _circuit_breaker_settings.database_operations,
            "database_connection_creation": _circuit_breaker_settings.database_connection_creation,
            "api_calls": _circuit_breaker_settings.api_calls,
            "file_operations": _circuit_breaker_settings.file_operations,
            "network_operations": _circuit_breaker_settings.network_operations,
        }

        if name in config_map:
            settings_config = config_map[name]
            return CircuitBreakerConfig(
                failure_threshold=settings_config.failure_threshold,
                recovery_timeout=settings_config.recovery_timeout,
                half_open_max_calls=settings_config.half_open_max_calls,
                half_open_success_threshold=settings_config.half_open_success_threshold,
                name=name,
            )
        else:
            # 使用默认配置
            default_config = _circuit_breaker_settings.default
            return CircuitBreakerConfig(
                failure_threshold=default_config.failure_threshold,
                recovery_timeout=default_config.recovery_timeout,
                half_open_max_calls=default_config.half_open_max_calls,
                half_open_success_threshold=default_config.half_open_success_threshold,
                name=name,
            )
    else:
        # 使用硬编码默认配置（向后兼容）
        return CircuitBreakerConfig(name=name)


def initialize_circuit_breaker_registry(circuit_breaker_settings=None):
    """初始化断路器注册表"""
    global _circuit_breaker_settings
    _circuit_breaker_settings = circuit_breaker_settings


def get_circuit_breaker_registry():
    """获取断路器注册表"""
    return _circuit_breakers.copy()


def clear_circuit_breaker_registry():
    """清空断路器注册表"""
    global _circuit_breakers
    with _registry_lock:
        _circuit_breakers.clear()


def circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None,
) -> Callable[[F], F]:
    """
    断路器装饰器

    参数：
        name: 断路器名称
        config: 断路器配置，如果不提供则使用默认配置

    使用示例：
        @circuit_breaker("database_operations")
        def database_query():
            # 数据库查询操作
            pass

        @circuit_breaker("api_calls", CircuitBreakerConfig(failure_threshold=3))
        def api_call():
            # API调用操作
            pass
    """

    def decorator(func: F) -> F:
        breaker = get_circuit_breaker(name, config)

        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def get_all_circuit_breakers() -> Dict[str, CircuitBreaker]:
    """获取所有断路器"""
    return _circuit_breakers.copy()


def reset_all_circuit_breakers():
    """重置所有断路器"""
    with _registry_lock:
        for breaker in _circuit_breakers.values():
            breaker.reset()
