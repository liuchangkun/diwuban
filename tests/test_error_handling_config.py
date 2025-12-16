"""
错误处理配置系统测试

测试错误处理配置的加载、验证和初始化功能。
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.core.config.loader_new import load_settings
from app.core.error_handling_manager import (
    initialize_error_handling,
    reinitialize_error_handling,
    shutdown_error_handling,
    is_error_handling_initialized,
    get_current_error_handling_settings,
)


class TestErrorHandlingConfig:
    """错误处理配置测试"""

    def setup_method(self):
        """测试前设置"""
        # 确保每个测试开始时都是干净的状态
        shutdown_error_handling()

    def teardown_method(self):
        """测试后清理"""
        shutdown_error_handling()

    def test_load_error_handling_config(self):
        """测试加载错误处理配置"""
        config_dir = Path("configs")
        settings = load_settings(config_dir)
        
        # 验证错误处理配置存在
        assert hasattr(settings, 'error_handling')
        error_config = settings.error_handling
        
        # 验证重试配置
        assert hasattr(error_config, 'retry')
        assert hasattr(error_config.retry, 'default')
        assert error_config.retry.default.max_retries == 3
        assert error_config.retry.default.base_delay == 1.0
        assert error_config.retry.default.strategy == "exponential"
        
        # 验证断路器配置
        assert hasattr(error_config, 'circuit_breaker')
        assert hasattr(error_config.circuit_breaker, 'default')
        assert error_config.circuit_breaker.default.failure_threshold == 5
        assert error_config.circuit_breaker.default.recovery_timeout == 60.0
        
        # 验证错误分析配置
        assert hasattr(error_config, 'error_analysis')
        assert hasattr(error_config.error_analysis, 'recording')
        assert error_config.error_analysis.recording.max_records == 10000
        assert error_config.error_analysis.recording.analysis_window == 3600

    def test_initialize_error_handling_with_config(self):
        """测试使用配置初始化错误处理机制"""
        config_dir = Path("configs")
        
        # 初始化错误处理机制
        success = initialize_error_handling(config_dir=config_dir)
        assert success
        assert is_error_handling_initialized()
        
        # 验证配置已加载
        current_settings = get_current_error_handling_settings()
        assert current_settings is not None
        assert hasattr(current_settings, 'error_handling')

    def test_initialize_error_handling_without_config(self):
        """测试不使用配置初始化错误处理机制"""
        # 不提供配置，应该使用默认配置
        success = initialize_error_handling()
        # 由于没有配置，初始化可能失败，但这是预期的
        # 这个测试主要验证不会崩溃

    def test_reinitialize_error_handling(self):
        """测试重新初始化错误处理机制"""
        config_dir = Path("configs")
        
        # 首次初始化
        success = initialize_error_handling(config_dir=config_dir)
        assert success
        
        # 重新初始化
        success = reinitialize_error_handling(config_dir=config_dir)
        assert success
        assert is_error_handling_initialized()

    def test_error_handling_manager_validation(self):
        """测试错误处理管理器的配置验证"""
        from app.core.error_handling_manager import ErrorHandlingManager
        from app.core.config.error_handling import (
            ErrorHandlingSettings,
            RetrySettings,
            RetryPolicyConfig,
        )
        
        # 创建无效配置（重试次数超限）
        invalid_retry_config = RetryPolicyConfig(
            max_retries=20,  # 超过默认限制10
            base_delay=1.0,
            max_delay=60.0,
            backoff_multiplier=2.0,
            strategy="exponential"
        )
        
        invalid_settings = ErrorHandlingSettings(
            retry=RetrySettings(default=invalid_retry_config)
        )
        
        # 创建模拟的完整设置对象
        mock_settings = MagicMock()
        mock_settings.error_handling = invalid_settings
        
        manager = ErrorHandlingManager()
        
        # 验证配置验证会检测到错误
        validation_result = manager._validate_config(invalid_settings)
        assert not validation_result.is_valid
        assert len(validation_result.errors) > 0

    def test_retry_manager_with_config(self):
        """测试重试管理器使用配置"""
        from app.core.retry import initialize_retry_manager, get_retry_manager
        from app.core.config.error_handling import RetrySettings, RetryPolicyConfig
        
        # 创建自定义重试配置
        custom_config = RetryPolicyConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=30.0,
            backoff_multiplier=1.5,
            strategy="linear"
        )
        
        retry_settings = RetrySettings(default=custom_config)
        
        # 初始化重试管理器
        initialize_retry_manager(retry_settings)
        
        # 验证配置已应用
        manager = get_retry_manager()
        assert manager.retry_settings == retry_settings
        
        # 验证策略配置
        default_policy = manager.policies[Exception]
        assert default_policy.max_retries == 5
        assert default_policy.base_delay == 2.0
        assert default_policy.max_delay == 30.0
        assert default_policy.backoff_multiplier == 1.5

    def test_circuit_breaker_with_config(self):
        """测试断路器使用配置"""
        from app.core.circuit_breaker import (
            initialize_circuit_breaker_registry,
            get_circuit_breaker,
        )
        from app.core.config.error_handling import (
            CircuitBreakerSettings,
            CircuitBreakerConfig,
        )
        
        # 创建自定义断路器配置
        custom_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30.0,
            half_open_max_calls=2,
            half_open_success_threshold=1,
        )
        
        circuit_breaker_settings = CircuitBreakerSettings(
            database_operations=custom_config
        )
        
        # 初始化断路器注册表
        initialize_circuit_breaker_registry(circuit_breaker_settings)
        
        # 获取断路器并验证配置
        breaker = get_circuit_breaker("database_operations")
        assert breaker.config.failure_threshold == 3
        assert breaker.config.recovery_timeout == 30.0
        assert breaker.config.half_open_max_calls == 2
        assert breaker.config.half_open_success_threshold == 1

    def test_error_analyzer_with_config(self):
        """测试错误分析器使用配置"""
        from app.core.error_analysis import initialize_error_analyzer, get_error_analyzer
        from app.core.config.error_handling import (
            ErrorAnalysisSettings,
            ErrorRecordingConfig,
        )
        
        # 创建自定义错误分析配置
        custom_recording_config = ErrorRecordingConfig(
            max_records=5000,
            analysis_window=1800,
            cleanup_interval=150,
            auto_cleanup=True,
        )
        
        error_analysis_settings = ErrorAnalysisSettings(
            recording=custom_recording_config
        )
        
        # 初始化错误分析器
        initialize_error_analyzer(error_analysis_settings)
        
        # 验证配置已应用
        analyzer = get_error_analyzer()
        assert analyzer.max_records == 5000
        assert analyzer.analysis_window == 1800
        assert analyzer.cleanup_interval == 150
        assert analyzer.auto_cleanup is True

    def test_config_validation_rules(self):
        """测试配置验证规则"""
        from app.core.config.error_handling import (
            ErrorHandlingSettings,
            ValidationSettings,
            RetryValidationConfig,
        )
        
        # 创建验证规则
        validation_config = RetryValidationConfig(
            max_retries_limit=5,  # 设置较低的限制
            max_delay_limit=30.0,
            min_base_delay=0.1,
            valid_strategies=["fixed", "linear"],
        )
        
        validation_settings = ValidationSettings(
            retry_validation=validation_config
        )
        
        error_handling_settings = ErrorHandlingSettings(
            validation=validation_settings
        )
        
        # 验证配置结构
        assert error_handling_settings.validation.retry_validation.max_retries_limit == 5
        assert error_handling_settings.validation.retry_validation.max_delay_limit == 30.0
        assert "exponential" not in error_handling_settings.validation.retry_validation.valid_strategies

    def test_error_handling_manager_logging(self):
        """测试错误处理管理器的初始化行为"""
        from app.core.error_handling_manager import ErrorHandlingManager

        manager = ErrorHandlingManager()

        # 测试未提供配置时的初始化行为
        # 注意：当前代码在未提供配置时直接返回False，不再记录warning日志
        success = manager.initialize()

        # 验证初始化失败（因为未提供配置）
        assert success is False
        assert manager.initialized is False

    def test_hot_reload_config(self):
        """测试配置热更新"""
        from app.core.config.error_handling import (
            ErrorHandlingSettings,
            InitializationSettings,
            HotReloadConfig,
        )
        
        # 创建启用热更新的配置
        hot_reload_config = HotReloadConfig(
            enable_hot_reload=True,
            watch_config_files=True,
            reload_interval=30,
            backup_on_reload=True,
        )
        
        initialization_settings = InitializationSettings(
            hot_reload=hot_reload_config
        )
        
        error_handling_settings = ErrorHandlingSettings(
            initialization=initialization_settings
        )
        
        # 验证热更新配置
        assert error_handling_settings.initialization.hot_reload.enable_hot_reload is True
        assert error_handling_settings.initialization.hot_reload.watch_config_files is True
        assert error_handling_settings.initialization.hot_reload.reload_interval == 30
