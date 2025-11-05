"""
异常处理测试：app/services/ 模块异常处理

测试各种异常场景：
- 数据库连接错误
- 数据验证错误
- 参数错误
- 资源不可用错误
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import numpy as np
from datetime import datetime

from app.services.calculation.dependency_analyzer import DependencyAnalyzer
from app.services.calculation.method_selector import MethodSelector
from app.services.calculation.validator import PhysicsValidator
from app.services.calculation.orchestrator import CalculationOrchestrator
from app.services.calculation.domain import CalculationContext
from app.services.ingest.create_staging import create_staging
from app.services.ingest.merge_service import _parse_granularity, _split_window
from app.core.config.loader_new import Settings


class TestDatabaseConnectionErrors:
    """数据库连接错误测试"""

    @patch('app.services.calculation.dependency_analyzer.get_connection')
    def test_dependency_analyzer_connection_failure(self, mock_conn):
        """场景1: DependencyAnalyzer数据库连接失败"""
        mock_conn.side_effect = Exception("Connection refused")
        
        with pytest.raises(Exception) as exc_info:
            DependencyAnalyzer()
        
        assert "Connection refused" in str(exc_info.value)

    @patch('app.services.calculation.method_selector.get_connection')
    def test_method_selector_connection_failure(self, mock_conn):
        """场景2: MethodSelector数据库连接失败"""
        mock_conn.side_effect = Exception("Connection timeout")
        
        with pytest.raises(Exception) as exc_info:
            MethodSelector()
        
        assert "Connection timeout" in str(exc_info.value)

    @patch('app.services.ingest.create_staging.get_conn')
    def test_create_staging_connection_failure(self, mock_conn):
        """场景3: create_staging数据库连接失败"""
        mock_conn.side_effect = Exception("Database unavailable")
        
        settings = Mock(spec=Settings)
        
        with pytest.raises(Exception) as exc_info:
            create_staging(settings)
        
        assert "Database unavailable" in str(exc_info.value)


class TestDataValidationErrors:
    """数据验证错误测试"""

    @patch('app.services.calculation.validator.get_connection')
    @patch('app.services.calculation.validator.CharacteristicCurveManager')
    def test_validator_out_of_range_values(self, mock_curve_mgr, mock_conn):
        """场景4: 验证器检测超出范围的值"""
        # Mock数据库连接
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn_obj = MagicMock()
        mock_conn_obj.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_conn_obj
        
        validator = PhysicsValidator()
        
        # 测试超出范围的值
        values = np.array([150.0, 200.0, 250.0])
        mask, errors = validator.validate_range(values, 0.0, 100.0)
        
        # 验证所有值都被标记为无效
        assert not mask.any()
        assert len(errors) > 0

    @patch('app.services.calculation.validator.get_connection')
    @patch('app.services.calculation.validator.CharacteristicCurveManager')
    def test_validator_negative_values(self, mock_curve_mgr, mock_conn):
        """场景5: 验证器检测负值"""
        # Mock数据库连接
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn_obj = MagicMock()
        mock_conn_obj.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_conn_obj
        
        validator = PhysicsValidator()
        
        # 测试负值
        values = np.array([-10.0, -20.0, -30.0])
        mask, errors = validator.validate_range(values, 0.0, 100.0)
        
        # 验证所有值都被标记为无效
        assert not mask.any()
        assert len(errors) > 0


class TestParameterErrors:
    """参数错误测试"""

    def test_calculation_context_missing_required_fields(self):
        """场景6: CalculationContext缺少必需字段"""
        # 缺少必需参数应该失败
        with pytest.raises(TypeError):
            CalculationContext()

    def test_calculation_context_invalid_time_range(self):
        """场景7: CalculationContext无效时间范围"""
        # 创建结束时间早于开始时间的上下文（不会抛出异常，但逻辑上无效）
        ctx = CalculationContext(
            station_id=1,
            device_id=1,
            start_ts=datetime(2025, 1, 1, 12, 0, 0),
            end_ts=datetime(2025, 1, 1, 0, 0, 0)  # 早于start_ts
        )
        
        # 验证上下文创建成功（数据类不验证业务逻辑）
        assert ctx.start_ts > ctx.end_ts

    def test_split_window_invalid_step(self):
        """场景8: _split_window无效步长"""
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 1, 1, 0, 0)
        
        # 使用0步长（会导致无限循环，但实际上_parse_granularity会确保最小值）
        # 这里测试非常大的步长
        segments = _split_window(start, end, 999999999)
        
        # 验证只有一段
        assert len(segments) == 1


class TestResourceUnavailableErrors:
    """资源不可用错误测试"""

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    @patch('app.services.calculation.orchestrator.get_connection')
    def test_orchestrator_device_type_not_found(self, mock_get_conn, mock_validator, mock_selector, mock_analyzer):
        """场景9: Orchestrator设备类型未找到"""
        # Mock数据库连接返回None
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        orchestrator = CalculationOrchestrator()
        
        # 获取不存在的设备类型
        device_type = orchestrator._get_device_type(999, 999)
        
        # 验证返回None
        assert device_type is None

    @patch('app.services.ingest.create_staging.get_conn')
    @patch('app.services.ingest.create_staging.create_staging_if_not_exists')
    def test_create_staging_table_creation_failure(self, mock_create_fn, mock_get_conn):
        """场景10: create_staging表创建失败"""
        # Mock数据库连接
        mock_conn = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        # Mock表创建失败
        mock_create_fn.side_effect = Exception("Table already exists")
        
        settings = Mock(spec=Settings)
        
        with pytest.raises(Exception) as exc_info:
            create_staging(settings)
        
        assert "Table already exists" in str(exc_info.value)


class TestConcurrencyErrors:
    """并发错误测试"""

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    @patch('app.services.calculation.orchestrator.get_connection')
    def test_orchestrator_concurrent_cache_access(self, mock_get_conn, mock_validator, mock_selector, mock_analyzer):
        """场景11: Orchestrator并发缓存访问"""
        # Mock数据库连接
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ('pump',)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        orchestrator = CalculationOrchestrator()
        
        # 模拟并发访问（多次调用）
        results = []
        for _ in range(10):
            device_type = orchestrator._get_device_type(1, 1)
            results.append(device_type)
        
        # 验证所有结果一致
        assert all(r == 'pump' for r in results)


class TestMemoryErrors:
    """内存错误测试"""

    @patch('app.services.calculation.validator.get_connection')
    @patch('app.services.calculation.validator.CharacteristicCurveManager')
    def test_validator_large_array_handling(self, mock_curve_mgr, mock_conn):
        """场景12: 验证器处理大数组"""
        # Mock数据库连接
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn_obj = MagicMock()
        mock_conn_obj.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_conn_obj
        
        validator = PhysicsValidator()
        
        # 测试大数组（10000个值）
        values = np.random.uniform(0, 100, 10000)
        mask, errors = validator.validate_range(values, 0.0, 100.0)
        
        # 验证处理成功
        assert len(mask) == 10000


class TestTypeErrors:
    """类型错误测试"""

    def test_parse_granularity_non_string_input(self):
        """场景13: _parse_granularity非字符串输入"""
        # 测试None输入
        assert _parse_granularity(None) == 3600

        # 测试数字输入（会导致AttributeError，因为int没有strip方法）
        with pytest.raises(AttributeError):
            _parse_granularity(123)

    def test_split_window_invalid_datetime_type(self):
        """场景14: _split_window无效datetime类型"""
        # 使用字符串而不是datetime（会导致TypeError）
        with pytest.raises(TypeError):
            _split_window("2025-01-01", "2025-01-02", 3600)


class TestStateErrors:
    """状态错误测试"""

    @patch('app.services.calculation.dependency_analyzer.get_connection')
    def test_dependency_analyzer_empty_registry(self, mock_conn):
        """场景15: DependencyAnalyzer空注册表"""
        # Mock数据库连接返回空结果
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn_obj = MagicMock()
        mock_conn_obj.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_conn_obj
        
        # 创建分析器（空注册表）
        analyzer = DependencyAnalyzer()
        
        # 验证创建成功
        assert analyzer is not None

    @patch('app.services.calculation.method_selector.get_connection')
    def test_method_selector_empty_registry(self, mock_conn):
        """场景16: MethodSelector空注册表"""
        # Mock数据库连接返回空结果
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn_obj = MagicMock()
        mock_conn_obj.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_conn_obj
        
        # 创建选择器（空注册表）
        selector = MethodSelector()
        
        # 验证创建成功
        assert selector is not None


class TestTimeoutErrors:
    """超时错误测试"""

    @patch('app.services.ingest.create_staging.get_conn')
    @patch('app.services.ingest.create_staging.create_staging_if_not_exists')
    def test_create_staging_operation_timeout(self, mock_create_fn, mock_get_conn):
        """场景17: create_staging操作超时"""
        # Mock数据库连接
        mock_conn = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        # Mock操作超时
        mock_create_fn.side_effect = Exception("Operation timeout")
        
        settings = Mock(spec=Settings)
        
        with pytest.raises(Exception) as exc_info:
            create_staging(settings)
        
        assert "Operation timeout" in str(exc_info.value)


class TestPermissionErrors:
    """权限错误测试"""

    @patch('app.services.ingest.create_staging.get_conn')
    def test_create_staging_permission_denied(self, mock_get_conn):
        """场景18: create_staging权限拒绝"""
        # Mock权限错误
        mock_get_conn.side_effect = Exception("Permission denied")
        
        settings = Mock(spec=Settings)
        
        with pytest.raises(Exception) as exc_info:
            create_staging(settings)
        
        assert "Permission denied" in str(exc_info.value)


class TestDataIntegrityErrors:
    """数据完整性错误测试"""

    @patch('app.services.calculation.validator.get_connection')
    @patch('app.services.calculation.validator.CharacteristicCurveManager')
    def test_validator_nan_values(self, mock_curve_mgr, mock_conn):
        """场景19: 验证器处理NaN值"""
        # Mock数据库连接
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn_obj = MagicMock()
        mock_conn_obj.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_conn_obj
        
        validator = PhysicsValidator()
        
        # 测试包含NaN的值
        values = np.array([50.0, np.nan, 70.0])
        mask, errors = validator.validate_range(values, 0.0, 100.0)
        
        # 验证NaN被标记为无效
        assert not mask[1]

    @patch('app.services.calculation.validator.get_connection')
    @patch('app.services.calculation.validator.CharacteristicCurveManager')
    def test_validator_inf_values(self, mock_curve_mgr, mock_conn):
        """场景20: 验证器处理Inf值"""
        # Mock数据库连接
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn_obj = MagicMock()
        mock_conn_obj.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_conn_obj
        
        validator = PhysicsValidator()
        
        # 测试包含Inf的值
        values = np.array([50.0, np.inf, 70.0])
        mask, errors = validator.validate_range(values, 0.0, 100.0)
        
        # 验证Inf被标记为无效
        assert not mask[1]


class TestConfigurationErrors:
    """配置错误测试"""

    def test_parse_granularity_invalid_format(self):
        """场景21: _parse_granularity无效格式"""
        # 测试无效格式
        assert _parse_granularity("invalid") == 3600
        assert _parse_granularity("30x") == 3600
        assert _parse_granularity("abc") == 3600


class TestCircularDependencyErrors:
    """循环依赖错误测试"""

    @patch('app.services.calculation.dependency_analyzer.get_connection')
    def test_dependency_analyzer_circular_dependency(self, mock_conn):
        """场景22: DependencyAnalyzer循环依赖"""
        # Mock数据库连接
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn_obj = MagicMock()
        mock_conn_obj.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_conn_obj

        analyzer = DependencyAnalyzer()

        # 构建循环依赖图
        graph = {
            'metric_a': ['metric_b'],
            'metric_b': ['metric_c'],
            'metric_c': ['metric_a']  # 循环
        }

        # 拓扑排序（应该抛出CircularDependencyError）
        from app.services.calculation.dependency_analyzer import CircularDependencyError

        with pytest.raises(CircularDependencyError) as exc_info:
            analyzer.topological_sort(graph)

        # 验证错误消息包含循环依赖信息
        assert "循环依赖" in str(exc_info.value)


class TestEdgeCaseErrors:
    """边缘情况错误测试"""

    def test_split_window_zero_duration(self):
        """场景23: _split_window零时长"""
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 1, 0, 0, 0)
        
        segments = _split_window(start, end, 3600)
        
        # 验证返回空列表
        assert len(segments) == 0

    @patch('app.services.calculation.validator.get_connection')
    @patch('app.services.calculation.validator.CharacteristicCurveManager')
    def test_validator_empty_array(self, mock_curve_mgr, mock_conn):
        """场景24: 验证器空数组"""
        # Mock数据库连接
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn_obj = MagicMock()
        mock_conn_obj.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_conn_obj
        
        validator = PhysicsValidator()
        
        # 测试空数组
        values = np.array([])
        mask, errors = validator.validate_range(values, 0.0, 100.0)
        
        # 验证返回空结果
        assert len(mask) == 0


class TestRecoveryMechanisms:
    """恢复机制测试"""

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    @patch('app.services.calculation.orchestrator.get_connection')
    def test_orchestrator_cache_recovery_after_error(self, mock_get_conn, mock_validator, mock_selector, mock_analyzer):
        """场景25: Orchestrator缓存错误后恢复"""
        # Mock数据库连接（第一次失败，第二次成功）
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [Exception("Temporary error"), ('pump',)]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        orchestrator = CalculationOrchestrator()
        
        # 第一次调用失败
        try:
            orchestrator._get_device_type(1, 1)
        except Exception:
            pass
        
        # 第二次调用成功
        device_type = orchestrator._get_device_type(1, 2)
        assert device_type == 'pump'


class TestErrorPropagation:
    """错误传播测试"""

    @patch('app.services.ingest.create_staging.get_conn')
    @patch('app.services.ingest.create_staging.create_staging_if_not_exists')
    @patch('app.services.ingest.create_staging._act')
    def test_create_staging_error_logging(self, mock_logger, mock_create_fn, mock_get_conn):
        """场景26: create_staging错误日志记录"""
        # Mock数据库连接
        mock_conn = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        # Mock操作失败
        mock_create_fn.side_effect = Exception("Test error")
        
        settings = Mock(spec=Settings)
        
        # 执行并捕获异常
        with pytest.raises(Exception):
            create_staging(settings)
        
        # 验证错误日志被记录
        error_calls = [c for c in mock_logger.error.call_args_list if c[0][0] == "[流程-错误] [创建staging表失败]"]
        assert len(error_calls) == 1


class TestRetryMechanisms:
    """重试机制测试"""

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    def test_orchestrator_multiple_initialization_attempts(self, mock_validator, mock_selector, mock_analyzer):
        """场景27: Orchestrator多次初始化尝试"""
        # 多次创建orchestrator
        for _ in range(5):
            orchestrator = CalculationOrchestrator()
            assert orchestrator is not None


class TestResourceCleanup:
    """资源清理测试"""

    @patch('app.services.ingest.create_staging.get_conn')
    @patch('app.services.ingest.create_staging.create_staging_if_not_exists')
    def test_create_staging_connection_cleanup_on_error(self, mock_create_fn, mock_get_conn):
        """场景28: create_staging错误时连接清理"""
        # Mock数据库连接
        mock_conn = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_conn
        mock_context.__exit__.return_value = None
        mock_get_conn.return_value = mock_context
        
        # Mock操作失败
        mock_create_fn.side_effect = Exception("Test error")
        
        settings = Mock(spec=Settings)
        
        # 执行并捕获异常
        with pytest.raises(Exception):
            create_staging(settings)
        
        # 验证上下文管理器的__exit__被调用（资源清理）
        mock_context.__exit__.assert_called_once()


class TestFallbackBehavior:
    """回退行为测试"""

    def test_parse_granularity_fallback_to_default(self):
        """场景29: _parse_granularity回退到默认值"""
        # 测试各种无效输入都回退到默认值
        invalid_inputs = ["", None, "invalid", "123", "abc", "30x", "1y"]
        
        for invalid_input in invalid_inputs:
            result = _parse_granularity(invalid_input)
            assert result == 3600  # 默认1小时


class TestErrorMessages:
    """错误消息测试"""

    @patch('app.services.calculation.dependency_analyzer.get_connection')
    def test_dependency_analyzer_error_message_clarity(self, mock_conn):
        """场景30: DependencyAnalyzer错误消息清晰度"""
        # Mock数据库连接失败
        error_message = "Database connection failed: Connection refused on port 5432"
        mock_conn.side_effect = Exception(error_message)
        
        # 验证错误消息被保留
        with pytest.raises(Exception) as exc_info:
            DependencyAnalyzer()
        
        assert error_message in str(exc_info.value)

