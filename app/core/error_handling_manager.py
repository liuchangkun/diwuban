"""
错误处理管理器（app.core.error_handling_manager）

本模块负责统一管理错误处理机制的初始化和配置：
- 重试管理器初始化
- 断路器管理器初始化
- 错误分析器初始化
- 配置验证和热更新
- 优雅的重新初始化机制

使用方式：
1. 在应用启动时调用 initialize_error_handling()
2. 在配置更新时调用 reinitialize_error_handling()
3. 在应用关闭时调用 shutdown_error_handling()
"""

import threading
import time
from pathlib import Path
from typing import Optional

from app.core.config.loader_new import load_settings
from app.core.config.validation import ConfigValidator


import logging

_act = logging.getLogger(__name__)

# 全局状态管理
_error_handling_initialized = False
_initialization_lock = threading.Lock()
_current_settings = None
_last_config_check = 0.0
_config_check_interval = 60.0  # 配置检查间隔（秒）


class ErrorHandlingManager:
    """错误处理管理器"""

    def __init__(self):
        self.retry_manager = None
        self.circuit_breaker_registry = None
        self.error_analyzer = None
        self.settings = None
        self.initialized = False

    def initialize(self, settings=None, config_dir: Optional[Path] = None):
        """初始化错误处理机制"""
        try:
            # 加载配置
            if settings is None and config_dir is not None:
                settings = load_settings(config_dir)

            if settings is None:
                return False

            self.settings = settings
            error_config = settings.error_handling

            # 验证配置
            if error_config.initialization.startup.validate_config:
                validation_result = self._validate_config(error_config)
                if not validation_result.is_valid:
                    if error_config.initialization.startup.fail_on_invalid_config:
                        return False
                    else:
                        pass

            # 初始化各个组件
            if error_config.initialization.startup.initialize_components:
                _act.info("[核心-初始化] [组件初始化开始]")
                self._initialize_retry_manager(error_config.retry)
                self._initialize_circuit_breaker_registry(error_config.circuit_breaker)
                self._initialize_error_analyzer(error_config.error_analysis)
                _act.info("[核心-初始化] [组件初始化完成]")

            self.initialized = True
            _act.info("[核心-初始化] [管理器初始化成功]")
            return True

        except Exception as e:
            _act.error(
                "[核心-错误] [管理器初始化失败]",
                extra={"extra_data": {"error": str(e)}},
                exc_info=True,
            )
            return False

    def _validate_config(self, error_config):
        """验证错误处理配置"""
        from app.core.config.validation import ValidationResult

        result = ValidationResult(True, [], [])

        # 验证重试配置
        retry_validation = error_config.validation.retry_validation
        for policy_name in [
            "default",
            "network_errors",
            "database_connection_errors",
            "high_priority_errors",
            "degradable_errors",
            "resource_exhausted_errors",
        ]:
            policy = getattr(error_config.retry, policy_name)

            if policy.max_retries > retry_validation.max_retries_limit:
                result.add_error(
                    f"retry.{policy_name}.max_retries",
                    policy.max_retries,
                    f"超过最大重试次数限制 {retry_validation.max_retries_limit}",
                )

            if policy.max_delay > retry_validation.max_delay_limit:
                result.add_error(
                    f"retry.{policy_name}.max_delay",
                    policy.max_delay,
                    f"超过最大延迟时间限制 {retry_validation.max_delay_limit}",
                )

            if policy.base_delay < retry_validation.min_base_delay:
                result.add_error(
                    f"retry.{policy_name}.base_delay",
                    policy.base_delay,
                    f"低于最小基础延迟 {retry_validation.min_base_delay}",
                )

            if policy.strategy not in retry_validation.valid_strategies:
                result.add_error(
                    f"retry.{policy_name}.strategy",
                    policy.strategy,
                    f"无效的重试策略，有效值: {retry_validation.valid_strategies}",
                )

        # 验证断路器配置
        cb_validation = error_config.validation.circuit_breaker_validation
        for breaker_name in [
            "default",
            "database_operations",
            "database_connection_creation",
            "api_calls",
            "file_operations",
            "network_operations",
        ]:
            breaker = getattr(error_config.circuit_breaker, breaker_name)

            if breaker.failure_threshold > cb_validation.max_failure_threshold:
                result.add_error(
                    f"circuit_breaker.{breaker_name}.failure_threshold",
                    breaker.failure_threshold,
                    f"超过最大失败阈值 {cb_validation.max_failure_threshold}",
                )

            if breaker.recovery_timeout > cb_validation.max_recovery_timeout:
                result.add_error(
                    f"circuit_breaker.{breaker_name}.recovery_timeout",
                    breaker.recovery_timeout,
                    f"超过最大恢复超时 {cb_validation.max_recovery_timeout}",
                )

            if breaker.recovery_timeout < cb_validation.min_recovery_timeout:
                result.add_error(
                    f"circuit_breaker.{breaker_name}.recovery_timeout",
                    breaker.recovery_timeout,
                    f"低于最小恢复超时 {cb_validation.min_recovery_timeout}",
                )

        # 验证错误分析配置
        analysis_validation = error_config.validation.analysis_validation
        recording = error_config.error_analysis.recording

        if recording.max_records > analysis_validation.max_records_limit:
            result.add_error(
                "error_analysis.recording.max_records",
                recording.max_records,
                f"超过最大记录数限制 {analysis_validation.max_records_limit}",
            )

        if recording.analysis_window > analysis_validation.max_analysis_window:
            result.add_error(
                "error_analysis.recording.analysis_window",
                recording.analysis_window,
                f"超过最大分析窗口 {analysis_validation.max_analysis_window}",
            )

        if recording.analysis_window < analysis_validation.min_analysis_window:
            result.add_error(
                "error_analysis.recording.analysis_window",
                recording.analysis_window,
                f"低于最小分析窗口 {analysis_validation.min_analysis_window}",
            )

        return result

    def _initialize_retry_manager(self, retry_settings):
        """初始化重试管理器"""
        try:
            from app.core.retry import initialize_retry_manager

            initialize_retry_manager(retry_settings)
        except Exception:
            pass

    def _initialize_circuit_breaker_registry(self, circuit_breaker_settings):
        """初始化断路器注册表"""
        try:
            from app.core.circuit_breaker import initialize_circuit_breaker_registry

            initialize_circuit_breaker_registry(circuit_breaker_settings)
        except Exception:
            pass

    def _initialize_error_analyzer(self, error_analysis_settings):
        """初始化错误分析器"""
        try:
            from app.core.error_analysis import initialize_error_analyzer

            initialize_error_analyzer(error_analysis_settings)
        except Exception:
            pass

    def reinitialize(self, settings=None, config_dir: Optional[Path] = None):
        """重新初始化错误处理机制"""

        # 备份当前配置
        old_settings = self.settings

        try:
            # 重新初始化
            success = self.initialize(settings, config_dir)
            if not success:
                # 恢复旧配置
                if old_settings:
                    self.initialize(old_settings)
            return success
        except Exception as e:
            # 恢复旧配置
            if old_settings:
                try:
                    self.initialize(old_settings)
                except Exception:
                    pass
            return False

    def shutdown(self):
        """关闭错误处理机制"""
        try:

            # 关闭各个组件
            if self.error_analyzer:
                try:
                    from app.core.error_analysis import shutdown_error_analyzer

                    shutdown_error_analyzer()
                except Exception:
                    pass

            # 重置状态
            self.retry_manager = None
            self.circuit_breaker_registry = None
            self.error_analyzer = None
            self.settings = None
            self.initialized = False

        except Exception:
            pass


# 全局错误处理管理器实例
_error_handling_manager = ErrorHandlingManager()


def initialize_error_handling(settings=None, config_dir: Optional[Path] = None) -> bool:
    """初始化全局错误处理机制"""
    global _error_handling_initialized, _current_settings

    with _initialization_lock:
        if _error_handling_initialized:
            return True

        success = _error_handling_manager.initialize(settings, config_dir)
        if success:
            _error_handling_initialized = True
            _current_settings = _error_handling_manager.settings

        return success


def reinitialize_error_handling(
    settings=None, config_dir: Optional[Path] = None
) -> bool:
    """重新初始化全局错误处理机制"""
    global _current_settings

    with _initialization_lock:
        success = _error_handling_manager.reinitialize(settings, config_dir)
        if success:
            _current_settings = _error_handling_manager.settings

        return success


def shutdown_error_handling():
    """关闭全局错误处理机制"""
    global _error_handling_initialized, _current_settings

    with _initialization_lock:
        _error_handling_manager.shutdown()
        _error_handling_initialized = False
        _current_settings = None


def is_error_handling_initialized() -> bool:
    """检查错误处理机制是否已初始化"""
    return _error_handling_initialized


def get_current_error_handling_settings():
    """获取当前错误处理配置"""
    return _current_settings


def check_config_updates(config_dir: Path) -> bool:
    """检查配置文件更新"""
    global _last_config_check

    current_time = time.time()
    if current_time - _last_config_check < _config_check_interval:
        return False

    _last_config_check = current_time

    try:
        # 检查配置文件修改时间
        error_handling_config_path = config_dir / "error_handling.yaml"
        if error_handling_config_path.exists():
            config_mtime = error_handling_config_path.stat().st_mtime
            if _current_settings and hasattr(_current_settings, "_config_mtime"):
                if config_mtime > _current_settings._config_mtime:
                    return True

        return False
    except Exception:
        return False
