"""
改进错误处理机制测试

测试新的错误处理功能：
- 增强的异常分类
- 智能重试机制
- 断路器模式
- 错误分析和监控
"""

import pytest
import time
from unittest.mock import Mock, patch

from app.core.exceptions import (
    BaseAppException,
    ErrorSeverity,
    RecoveryAction,
    DatabaseConnectionError,
    DatabaseNetworkError,
    DatabaseAuthenticationError,
    DatabaseResourceExhaustedError,
    PoolExhaustedError,
    PoolValidationError,
)
from app.core.retry import (
    smart_retry,
    RetryPolicy,
    RetryStrategy,
    get_retry_stats,
    reset_retry_stats,
)
from app.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    circuit_breaker,
    get_circuit_breaker,
    reset_all_circuit_breakers,
)
from app.core.error_analysis import (
    ErrorAnalyzer,
    error_monitor,
    get_error_analyzer,
    generate_error_report,
)


class TestEnhancedExceptions:
    """测试增强的异常类"""

    def test_base_exception_with_severity(self):
        """测试基础异常的严重程度和恢复建议"""
        error = BaseAppException(
            "测试错误",
            severity=ErrorSeverity.HIGH,
            recovery_action=RecoveryAction.RESTART,
            recovery_suggestion="重启服务",
        )

        assert error.severity == ErrorSeverity.HIGH
        assert error.recovery_action == RecoveryAction.RESTART
        assert error.recovery_suggestion == "重启服务"

        error_dict = error.to_dict()
        assert error_dict["severity"] == "high"
        assert error_dict["recovery_action"] == "restart"
        assert error_dict["recovery_suggestion"] == "重启服务"

    def test_database_connection_error_defaults(self):
        """测试数据库连接错误的默认设置"""
        error = DatabaseConnectionError("连接失败")

        assert error.severity == ErrorSeverity.HIGH
        assert error.recovery_action == RecoveryAction.RETRY
        assert "数据库连接配置" in error.recovery_suggestion

    def test_database_network_error_defaults(self):
        """测试数据库网络错误的默认设置"""
        error = DatabaseNetworkError("网络连接失败")

        assert error.severity == ErrorSeverity.HIGH
        assert error.recovery_action == RecoveryAction.RETRY
        assert "网络连接" in error.recovery_suggestion

    def test_database_authentication_error_defaults(self):
        """测试数据库认证错误的默认设置"""
        error = DatabaseAuthenticationError("认证失败")

        assert error.severity == ErrorSeverity.CRITICAL
        assert error.recovery_action == RecoveryAction.MANUAL_INTERVENTION
        assert "用户名" in error.recovery_suggestion

    def test_pool_exhausted_error_defaults(self):
        """测试连接池耗尽错误的默认设置"""
        error = PoolExhaustedError("连接池耗尽")

        assert error.severity == ErrorSeverity.HIGH
        assert error.recovery_action == RecoveryAction.DEGRADE
        assert "连接池大小" in error.recovery_suggestion


class TestSmartRetry:
    """测试智能重试机制"""

    def setup_method(self):
        """测试前重置统计"""
        reset_retry_stats()

    def test_smart_retry_success_after_failure(self):
        """测试重试成功的情况"""
        call_count = 0

        @smart_retry()
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise DatabaseConnectionError("连接失败")
            return "success"

        result = failing_function()
        assert result == "success"
        assert call_count == 3

        stats = get_retry_stats()
        assert stats.total_attempts > 0
        assert stats.successful_retries > 0

    def test_smart_retry_with_non_retryable_exception(self):
        """测试不可重试异常的处理"""
        call_count = 0

        @smart_retry()
        def failing_function():
            nonlocal call_count
            call_count += 1
            raise DatabaseAuthenticationError("认证失败")

        with pytest.raises(DatabaseAuthenticationError):
            failing_function()

        # 不可重试异常应该只调用一次
        assert call_count == 1

    def test_smart_retry_with_custom_policy(self):
        """测试自定义重试策略"""
        call_count = 0
        custom_policy = RetryPolicy(
            max_retries=2, base_delay=0.1, strategy=RetryStrategy.FIXED
        )

        @smart_retry(policy=custom_policy)
        def failing_function():
            nonlocal call_count
            call_count += 1
            raise DatabaseConnectionError("连接失败")

        with pytest.raises(DatabaseConnectionError):
            failing_function()

        # 应该尝试 1 + 2 = 3 次
        assert call_count == 3

    def test_retry_delay_calculation(self):
        """测试重试延迟计算"""
        from app.core.retry import RetryManager

        manager = RetryManager()
        policy = RetryPolicy(
            base_delay=1.0, backoff_multiplier=2.0, strategy=RetryStrategy.EXPONENTIAL
        )

        # 测试指数退避
        delay1 = manager.calculate_delay(0, policy)
        delay2 = manager.calculate_delay(1, policy)
        delay3 = manager.calculate_delay(2, policy)

        assert delay1 >= 1.0
        assert delay2 >= 2.0
        assert delay3 >= 4.0


class TestCircuitBreaker:
    """测试断路器模式"""

    def setup_method(self):
        """测试前重置断路器"""
        reset_all_circuit_breakers()

    def test_circuit_breaker_normal_operation(self):
        """测试断路器正常操作"""
        config = CircuitBreakerConfig(
            failure_threshold=3, recovery_timeout=1.0, name="test_breaker"
        )
        breaker = CircuitBreaker(config)

        # 正常调用应该成功
        result = breaker.call(lambda: "success")
        assert result == "success"
        assert breaker.get_state() == CircuitState.CLOSED

    def test_circuit_breaker_opens_after_failures(self):
        """测试断路器在失败后开启"""
        config = CircuitBreakerConfig(
            failure_threshold=2, recovery_timeout=1.0, name="test_breaker"
        )
        breaker = CircuitBreaker(config)

        # 连续失败应该开启断路器
        for _ in range(2):
            with pytest.raises(Exception):
                breaker.call(lambda: (_ for _ in ()).throw(Exception("失败")))

        assert breaker.get_state() == CircuitState.OPEN

        # 断路器开启后应该拒绝调用
        from app.core.circuit_breaker import CircuitBreakerError

        with pytest.raises(CircuitBreakerError):
            breaker.call(lambda: "success")

    def test_circuit_breaker_half_open_recovery(self):
        """测试断路器半开状态恢复"""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.1,  # 短恢复时间
            half_open_success_threshold=1,
            name="test_breaker",
        )
        breaker = CircuitBreaker(config)

        # 触发断路器开启
        for _ in range(2):
            with pytest.raises(Exception):
                breaker.call(lambda: (_ for _ in ()).throw(Exception("失败")))

        assert breaker.get_state() == CircuitState.OPEN

        # 等待恢复时间
        time.sleep(0.2)

        # 成功调用应该关闭断路器
        result = breaker.call(lambda: "success")
        assert result == "success"
        assert breaker.get_state() == CircuitState.CLOSED

    def test_circuit_breaker_decorator(self):
        """测试断路器装饰器"""
        call_count = 0

        @circuit_breaker("test_decorator", CircuitBreakerConfig(failure_threshold=2))
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("失败")
            return "success"

        # 前两次调用失败，断路器开启
        with pytest.raises(Exception):
            test_function()
        with pytest.raises(Exception):
            test_function()

        # 断路器开启后拒绝调用
        from app.core.circuit_breaker import CircuitBreakerError

        with pytest.raises(CircuitBreakerError):
            test_function()


class TestErrorAnalysis:
    """测试错误分析和监控"""

    def setup_method(self):
        """测试前重置错误分析器"""
        analyzer = get_error_analyzer()
        analyzer.error_records.clear()
        analyzer.error_counts.clear()
        analyzer.severity_counts.clear()
        analyzer.function_error_counts.clear()
        analyzer.patterns.clear()

    def test_error_monitor_decorator(self):
        """测试错误监控装饰器"""

        @error_monitor
        def test_function():
            raise DatabaseConnectionError("连接失败")

        with pytest.raises(DatabaseConnectionError):
            test_function()

        analyzer = get_error_analyzer()
        assert len(analyzer.error_records) == 1
        assert analyzer.error_counts["DatabaseConnectionError"] == 1

    def test_error_analysis_trends(self):
        """测试错误趋势分析"""
        analyzer = get_error_analyzer()

        # 模拟一些错误
        for i in range(10):
            error = DatabaseConnectionError(f"错误 {i}")
            analyzer.record_error(
                error=error,
                context={"test": True},
                function_name="test_function",
                module_name="test_module",
            )

        trends = analyzer.analyze_trends(3600)
        assert trends.total_errors == 10
        assert trends.error_rate > 0
        assert "DatabaseConnectionError" in [et[0] for et in trends.top_error_types]

    def test_error_report_generation(self):
        """测试错误报告生成"""
        analyzer = get_error_analyzer()

        # 添加一些错误记录
        for severity in [
            ErrorSeverity.HIGH,
            ErrorSeverity.CRITICAL,
            ErrorSeverity.MEDIUM,
        ]:
            error = BaseAppException("测试错误", severity=severity)
            analyzer.record_error(
                error=error,
                context={"severity": severity.value},
                function_name="test_function",
            )

        report = analyzer.generate_report(3600)
        assert report.summary.total_errors == 3
        assert len(report.recommendations) > 0
        assert report.generated_at is not None

    def test_error_pattern_detection(self):
        """测试错误模式识别"""
        analyzer = get_error_analyzer()

        # 模拟重复错误模式
        for _ in range(5):
            error = DatabaseConnectionError("连接失败")
            analyzer.record_error(
                error=error,
                context={"pattern": "connection_failure"},
                function_name="database_operation",
            )

        # 手动触发模式分析
        analyzer._analyze_patterns()

        assert len(analyzer.patterns) > 0
        pattern = analyzer.patterns[0]
        assert pattern.frequency >= 5
        assert "DatabaseConnectionError" in pattern.error_types


class TestIntegratedErrorHandling:
    """测试集成的错误处理"""

    def setup_method(self):
        """测试前重置所有组件"""
        reset_retry_stats()
        reset_all_circuit_breakers()
        analyzer = get_error_analyzer()
        analyzer.error_records.clear()
        analyzer.error_counts.clear()

    def test_retry_with_circuit_breaker_and_monitoring(self):
        """测试重试、断路器和监控的集成"""
        call_count = 0

        @smart_retry(policy=RetryPolicy(max_retries=5, base_delay=0.1))
        @circuit_breaker("integrated_test", CircuitBreakerConfig(failure_threshold=10))
        @error_monitor
        def integrated_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:  # 减少失败次数，确保重试能成功
                raise DatabaseConnectionError("连接失败")
            return "success"

        result = integrated_function()
        assert result == "success"

        # 检查重试统计
        retry_stats = get_retry_stats()
        assert retry_stats.total_attempts > 0

        # 检查断路器状态
        breaker = get_circuit_breaker("integrated_test")
        assert breaker.get_state() == CircuitState.CLOSED

        # 检查错误监控
        analyzer = get_error_analyzer()
        assert len(analyzer.error_records) > 0

    def test_pool_exhausted_error_handling(self):
        """测试连接池耗尽错误的处理"""
        error = PoolExhaustedError(
            "连接池耗尽", context={"pool_size": 10, "active_connections": 10}
        )

        # 验证错误属性
        assert error.severity == ErrorSeverity.HIGH
        assert error.recovery_action == RecoveryAction.DEGRADE
        assert "连接池大小" in error.recovery_suggestion

        # 验证上下文信息
        assert error.context["pool_size"] == 10
        assert error.context["active_connections"] == 10

    def test_database_network_error_handling(self):
        """测试数据库网络错误的处理"""
        error = DatabaseNetworkError(
            "网络连接失败", context={"host": "localhost", "port": 5432}
        )

        # 验证错误属性
        assert error.severity == ErrorSeverity.HIGH
        assert error.recovery_action == RecoveryAction.RETRY
        assert "网络连接" in error.recovery_suggestion

        # 验证继承关系
        assert isinstance(error, DatabaseConnectionError)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
