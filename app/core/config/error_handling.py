"""
错误处理配置模块（app.core.config.error_handling）

本模块包含错误处理相关的配置类定义，包括：
- 重试策略配置
- 断路器配置
- 错误分析配置
- 错误监控配置
"""

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass(frozen=True)
class RetryPolicyConfig:
    """重试策略配置"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    strategy: str = "exponential"


@dataclass(frozen=True)
class RetrySettings:
    """重试配置"""
    default: RetryPolicyConfig = RetryPolicyConfig()
    network_errors: RetryPolicyConfig = RetryPolicyConfig(
        max_retries=5,
        base_delay=0.5,
        max_delay=10.0,
        backoff_multiplier=1.5,
        strategy="exponential"
    )
    database_connection_errors: RetryPolicyConfig = RetryPolicyConfig(
        max_retries=5,
        base_delay=1.0,
        max_delay=30.0,
        backoff_multiplier=2.0,
        strategy="exponential"
    )
    high_priority_errors: RetryPolicyConfig = RetryPolicyConfig(
        max_retries=2,
        base_delay=0.1,
        max_delay=1.0,
        backoff_multiplier=1.2,
        jitter=False,
        strategy="linear"
    )
    degradable_errors: RetryPolicyConfig = RetryPolicyConfig(
        max_retries=2,
        base_delay=2.0,
        max_delay=10.0,
        backoff_multiplier=1.5,
        strategy="exponential"
    )
    resource_exhausted_errors: RetryPolicyConfig = RetryPolicyConfig(
        max_retries=3,
        base_delay=5.0,
        max_delay=60.0,
        backoff_multiplier=2.0,
        strategy="exponential"
    )


@dataclass(frozen=True)
class CircuitBreakerConfig:
    """断路器配置"""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3
    half_open_success_threshold: int = 2


@dataclass(frozen=True)
class CircuitBreakerSettings:
    """断路器配置集合"""
    default: CircuitBreakerConfig = CircuitBreakerConfig()
    database_operations: CircuitBreakerConfig = CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=30.0
    )
    database_connection_creation: CircuitBreakerConfig = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=60.0,
        half_open_max_calls=2,
        half_open_success_threshold=1
    )
    api_calls: CircuitBreakerConfig = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=45.0
    )
    file_operations: CircuitBreakerConfig = CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=30.0
    )
    network_operations: CircuitBreakerConfig = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=60.0,
        half_open_max_calls=2,
        half_open_success_threshold=1
    )


@dataclass(frozen=True)
class ErrorRecordingConfig:
    """错误记录配置"""
    max_records: int = 10000
    analysis_window: int = 3600
    cleanup_interval: int = 300
    auto_cleanup: bool = True


@dataclass(frozen=True)
class PatternDetectionConfig:
    """错误模式检测配置"""
    min_frequency: int = 3
    time_window: int = 1800
    similarity_threshold: float = 0.8
    enable_auto_detection: bool = True


@dataclass(frozen=True)
class TrendAnalysisConfig:
    """错误趋势分析配置"""
    analysis_interval: int = 300
    trend_window: int = 3600
    rate_threshold: float = 0.1
    enable_prediction: bool = True


@dataclass(frozen=True)
class ReportingConfig:
    """错误报告配置"""
    auto_generate: bool = True
    report_interval: int = 1800
    max_reports: int = 100
    include_patterns: bool = True
    include_trends: bool = True
    include_suggestions: bool = True


@dataclass(frozen=True)
class ErrorAnalysisSettings:
    """错误分析配置"""
    recording: ErrorRecordingConfig = ErrorRecordingConfig()
    pattern_detection: PatternDetectionConfig = PatternDetectionConfig()
    trend_analysis: TrendAnalysisConfig = TrendAnalysisConfig()
    reporting: ReportingConfig = ReportingConfig()


@dataclass(frozen=True)
class MonitoringDecoratorConfig:
    """监控装饰器配置"""
    enable_context_capture: bool = True
    max_context_size: int = 1000
    capture_args: bool = True
    capture_return: bool = False
    exclude_sensitive_keys: List[str] = None

    def __post_init__(self):
        if self.exclude_sensitive_keys is None:
            object.__setattr__(self, 'exclude_sensitive_keys', [
                "password", "token", "secret", "key", "auth"
            ])


@dataclass(frozen=True)
class PerformanceMonitoringConfig:
    """性能监控配置"""
    enable_timing: bool = True
    slow_threshold: float = 5.0
    memory_monitoring: bool = False


@dataclass(frozen=True)
class AlertingConfig:
    """告警配置"""
    enable_alerts: bool = False
    error_rate_threshold: float = 0.05
    consecutive_failures_threshold: int = 10
    circuit_breaker_open_alert: bool = True


@dataclass(frozen=True)
class MonitoringSettings:
    """监控配置"""
    decorator: MonitoringDecoratorConfig = MonitoringDecoratorConfig()
    performance: PerformanceMonitoringConfig = PerformanceMonitoringConfig()
    alerting: AlertingConfig = AlertingConfig()


@dataclass(frozen=True)
class RetryValidationConfig:
    """重试配置验证规则"""
    max_retries_limit: int = 10
    max_delay_limit: float = 300.0
    min_base_delay: float = 0.01
    valid_strategies: List[str] = None

    def __post_init__(self):
        if self.valid_strategies is None:
            object.__setattr__(self, 'valid_strategies', [
                "fixed", "linear", "exponential", "fibonacci"
            ])


@dataclass(frozen=True)
class CircuitBreakerValidationConfig:
    """断路器配置验证规则"""
    max_failure_threshold: int = 20
    max_recovery_timeout: float = 600.0
    min_recovery_timeout: float = 5.0
    max_half_open_calls: int = 10


@dataclass(frozen=True)
class AnalysisValidationConfig:
    """错误分析配置验证规则"""
    max_records_limit: int = 100000
    max_analysis_window: int = 86400
    min_analysis_window: int = 60
    max_context_size_limit: int = 10000


@dataclass(frozen=True)
class ValidationSettings:
    """配置验证规则"""
    retry_validation: RetryValidationConfig = RetryValidationConfig()
    circuit_breaker_validation: CircuitBreakerValidationConfig = CircuitBreakerValidationConfig()
    analysis_validation: AnalysisValidationConfig = AnalysisValidationConfig()


@dataclass(frozen=True)
class StartupConfig:
    """启动配置"""
    validate_config: bool = True
    initialize_components: bool = True
    fail_on_invalid_config: bool = True


@dataclass(frozen=True)
class HotReloadConfig:
    """热更新配置"""
    enable_hot_reload: bool = False
    watch_config_files: bool = False
    reload_interval: int = 60
    backup_on_reload: bool = True


@dataclass(frozen=True)
class InitializationSettings:
    """初始化配置"""
    startup: StartupConfig = StartupConfig()
    hot_reload: HotReloadConfig = HotReloadConfig()


@dataclass(frozen=True)
class ErrorHandlingSettings:
    """
    错误处理完整配置
    
    集成所有错误处理相关配置，提供统一的配置访问接口。
    
    属性：
        retry: 重试策略配置
        circuit_breaker: 断路器配置
        error_analysis: 错误分析配置
        monitoring: 监控配置
        validation: 配置验证规则
        initialization: 初始化配置
    """
    retry: RetrySettings = RetrySettings()
    circuit_breaker: CircuitBreakerSettings = CircuitBreakerSettings()
    error_analysis: ErrorAnalysisSettings = ErrorAnalysisSettings()
    monitoring: MonitoringSettings = MonitoringSettings()
    validation: ValidationSettings = ValidationSettings()
    initialization: InitializationSettings = InitializationSettings()
