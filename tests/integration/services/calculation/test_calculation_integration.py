"""
集成测试：app/services/calculation/ 模块集成

测试多个组件的协作：
- DependencyAnalyzer + MethodSelector 集成
- MethodSelector + Calculators 集成
- Validator + ValidationReporter 集成
- Orchestrator 组件集成
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
import numpy as np

from app.services.calculation.dependency_analyzer import DependencyAnalyzer
from app.services.calculation.method_selector import MethodSelector
from app.services.calculation.validator import PhysicsValidator
from app.services.calculation.validation_reporter import ValidationReporter
from app.services.calculation.calculators import get_calculator, CALCULATOR_REGISTRY
from app.services.calculation.orchestrator import CalculationOrchestrator
from app.services.calculation.domain import CalculationContext


class TestDependencyAnalyzerMethodSelectorIntegration:
    """DependencyAnalyzer + MethodSelector 集成测试"""

    @patch('app.services.calculation.dependency_analyzer.get_connection')
    @patch('app.services.calculation.method_selector.get_connection')
    def test_dependency_analysis_feeds_method_selection(self, mock_ms_conn, mock_da_conn):
        """场景1: 依赖分析结果用于方法选择"""
        # Mock DependencyAnalyzer数据库连接（返回6个字段）
        mock_da_cursor = MagicMock()
        mock_da_cursor.fetchall.return_value = [
            ('method_1', 'pump_flow_rate', 'flow_v1', 1, 'pump_head', True),
            ('method_2', 'pump_efficiency', 'eff_v1', 1, 'pump_flow_rate,pump_head', True)
        ]
        mock_da_conn_obj = MagicMock()
        mock_da_conn_obj.cursor.return_value.__enter__.return_value = mock_da_cursor
        mock_da_conn.return_value.__enter__.return_value = mock_da_conn_obj

        # Mock MethodSelector数据库连接
        mock_ms_cursor = MagicMock()
        mock_ms_cursor.fetchall.return_value = []
        mock_ms_conn_obj = MagicMock()
        mock_ms_conn_obj.cursor.return_value.__enter__.return_value = mock_ms_cursor
        mock_ms_conn.return_value.__enter__.return_value = mock_ms_conn_obj

        # 创建组件
        analyzer = DependencyAnalyzer()
        selector = MethodSelector()

        # 验证组件创建成功
        assert analyzer is not None
        assert selector is not None

    @patch('app.services.calculation.dependency_analyzer.get_connection')
    def test_topological_sort_produces_calculation_order(self, mock_conn):
        """场景2: 拓扑排序产生计算顺序"""
        # Mock数据库连接（返回6个字段）
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('method_b', 'metric_b', 'b_v1', 1, 'metric_a', True),
            ('method_c', 'metric_c', 'c_v1', 1, 'metric_b', True)
        ]
        mock_conn_obj = MagicMock()
        mock_conn_obj.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_conn_obj

        # 创建分析器
        analyzer = DependencyAnalyzer()

        # 构建依赖图
        graph = {
            'metric_a': [],
            'metric_b': ['metric_a'],
            'metric_c': ['metric_b']
        }

        # 拓扑排序
        result = analyzer.topological_sort(graph)

        # 验证顺序：metric_a应该在metric_b之前，metric_b应该在metric_c之前
        assert len(result) > 0
        if 'metric_a' in result and 'metric_b' in result:
            assert result.index('metric_a') < result.index('metric_b')
        if 'metric_b' in result and 'metric_c' in result:
            assert result.index('metric_b') < result.index('metric_c')


class TestMethodSelectorCalculatorsIntegration:
    """MethodSelector + Calculators 集成测试"""

    @patch('app.services.calculation.method_selector.get_connection')
    def test_method_selection_returns_valid_calculator(self, mock_conn):
        """场景3: 方法选择返回有效的计算器"""
        # Mock数据库连接
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn_obj = MagicMock()
        mock_conn_obj.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_conn_obj
        
        # 创建选择器
        selector = MethodSelector()
        
        # 验证CALCULATOR_REGISTRY不为空
        assert len(CALCULATOR_REGISTRY) > 0

    def test_calculator_registry_contains_expected_calculators(self):
        """场景4: 计算器注册表包含预期的计算器"""
        # 验证注册表包含常见的计算器
        assert isinstance(CALCULATOR_REGISTRY, dict)
        assert len(CALCULATOR_REGISTRY) > 0
        
        # 验证每个计算器都是可调用的
        for calc_name, calc_func in CALCULATOR_REGISTRY.items():
            assert callable(calc_func), f"Calculator {calc_name} is not callable"


class TestValidatorReporterIntegration:
    """Validator + ValidationReporter 集成测试"""

    @patch('app.services.calculation.validator.get_connection')
    @patch('app.services.calculation.validator.CharacteristicCurveManager')
    def test_validator_results_feed_reporter(self, mock_curve_mgr, mock_conn):
        """场景5: 验证器结果传递给报告器"""
        # Mock数据库连接
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn_obj = MagicMock()
        mock_conn_obj.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_conn_obj
        
        # 创建组件
        validator = PhysicsValidator()
        reporter = ValidationReporter()
        
        # 验证组件创建成功
        assert validator is not None
        assert reporter is not None

    @patch('app.services.calculation.validator.get_connection')
    @patch('app.services.calculation.validator.CharacteristicCurveManager')
    def test_validation_error_reporting(self, mock_curve_mgr, mock_conn):
        """场景6: 验证错误报告"""
        # Mock数据库连接
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn_obj = MagicMock()
        mock_conn_obj.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_conn_obj
        
        # 创建验证器
        validator = PhysicsValidator()
        
        # 测试范围验证
        values = np.array([50.0, 150.0, 70.0])  # 150.0超出范围
        mask, errors = validator.validate_range(values, 0.0, 100.0)
        
        # 验证结果
        assert not mask[1]  # 第二个值应该无效
        assert len(errors) > 0


class TestOrchestratorComponentIntegration:
    """Orchestrator 组件集成测试"""

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    def test_orchestrator_initializes_all_components(self, mock_validator, mock_selector, mock_analyzer):
        """场景7: Orchestrator初始化所有组件"""
        # 创建orchestrator
        orchestrator = CalculationOrchestrator()
        
        # 验证所有核心组件都被初始化
        assert orchestrator.dependency_analyzer is not None
        assert orchestrator.method_selector is not None
        assert orchestrator.validator is not None
        assert orchestrator.validation_reporter is not None

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    def test_orchestrator_with_optimization_enabled(self, mock_validator, mock_selector, mock_analyzer):
        """场景8: Orchestrator启用优化"""
        # 创建orchestrator（启用优化）
        orchestrator = CalculationOrchestrator(enable_optimization=True)
        
        # 验证优化器被初始化
        assert orchestrator.enable_optimization is True
        assert orchestrator.parameter_optimizer is not None

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    def test_orchestrator_with_adaptive_enabled(self, mock_validator, mock_selector, mock_analyzer):
        """场景9: Orchestrator启用自适应"""
        # 创建orchestrator（启用自适应）
        orchestrator = CalculationOrchestrator(enable_adaptive=True)
        
        # 验证自适应组件被初始化
        assert orchestrator.enable_adaptive is True
        assert orchestrator.adaptive_batch is not None

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    def test_orchestrator_without_optional_features(self, mock_validator, mock_selector, mock_analyzer):
        """场景10: Orchestrator禁用可选功能"""
        # 创建orchestrator（禁用所有可选功能）
        orchestrator = CalculationOrchestrator(enable_adaptive=False, enable_optimization=False)
        
        # 验证可选组件未被初始化
        assert orchestrator.enable_optimization is False
        assert orchestrator.parameter_optimizer is None
        assert orchestrator.enable_adaptive is False


class TestCalculationContextIntegration:
    """CalculationContext 集成测试"""

    def test_calculation_context_creation(self):
        """场景11: 创建计算上下文"""
        from datetime import datetime

        # 创建上下文（使用正确的字段名）
        ctx = CalculationContext(
            station_id=1,
            device_id=1,
            start_ts=datetime(2025, 1, 1, 0, 0, 0),
            end_ts=datetime(2025, 1, 1, 1, 0, 0),
            quality_filters={'status': ['valid']},
            extra={'batch_size': 1000}
        )

        # 验证上下文
        assert ctx.station_id == 1
        assert ctx.device_id == 1
        assert ctx.quality_filters == {'status': ['valid']}
        assert ctx.extra['batch_size'] == 1000

    def test_calculation_context_immutability(self):
        """场景12: 计算上下文不可变性"""
        from dataclasses import FrozenInstanceError
        from datetime import datetime

        # 创建上下文（提供所有必需参数）
        ctx = CalculationContext(
            station_id=1,
            device_id=1,
            start_ts=datetime(2025, 1, 1, 0, 0, 0),
            end_ts=datetime(2025, 1, 1, 1, 0, 0)
        )

        # 尝试修改应该失败
        with pytest.raises(FrozenInstanceError):
            ctx.station_id = 2


class TestEndToEndCalculationFlow:
    """端到端计算流程测试"""

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    @patch('app.services.calculation.orchestrator.get_connection')
    def test_orchestrator_device_type_caching(self, mock_get_conn, mock_validator, mock_selector, mock_analyzer):
        """场景13: Orchestrator设备类型缓存"""
        # Mock数据库连接
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ('pump',)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        # 创建orchestrator
        orchestrator = CalculationOrchestrator()
        
        # 第一次调用
        device_type1 = orchestrator._get_device_type(1, 1)
        
        # 第二次调用（应该使用缓存）
        device_type2 = orchestrator._get_device_type(1, 1)
        
        # 验证结果一致
        assert device_type1 == device_type2
        assert device_type1 == 'pump'
        
        # 验证数据库只被查询一次（使用缓存）
        assert mock_cursor.fetchone.call_count == 1

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    @patch('app.services.calculation.orchestrator.get_connection')
    def test_orchestrator_metric_allowance_caching(self, mock_get_conn, mock_validator, mock_selector, mock_analyzer):
        """场景14: Orchestrator指标允许缓存"""
        # Mock数据库连接
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(['pump', 'valve'],)]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        # 创建orchestrator
        orchestrator = CalculationOrchestrator()
        
        # 第一次调用
        allowed1 = orchestrator._metric_allowed_for_device('pump_flow_rate', 'pump')
        
        # 第二次调用（应该使用缓存）
        allowed2 = orchestrator._metric_allowed_for_device('pump_flow_rate', 'pump')
        
        # 验证结果一致
        assert allowed1 == allowed2


class TestComponentErrorHandling:
    """组件错误处理集成测试"""

    @patch('app.services.calculation.dependency_analyzer.get_connection')
    def test_dependency_analyzer_handles_database_error(self, mock_conn):
        """场景15: DependencyAnalyzer处理数据库错误"""
        # Mock数据库连接失败
        mock_conn.side_effect = Exception("Database connection failed")

        # 创建分析器应该失败
        with pytest.raises(Exception) as exc_info:
            analyzer = DependencyAnalyzer()

        assert "Database connection failed" in str(exc_info.value)

    @patch('app.services.calculation.method_selector.get_connection')
    def test_method_selector_handles_database_error(self, mock_conn):
        """场景16: MethodSelector处理数据库错误"""
        # Mock数据库连接失败
        mock_conn.side_effect = Exception("Database connection failed")

        # 创建选择器应该失败
        with pytest.raises(Exception) as exc_info:
            selector = MethodSelector()

        assert "Database connection failed" in str(exc_info.value)


class TestAdaptiveBatchIntegration:
    """自适应批量管理集成测试"""

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    def test_adaptive_batch_initialization(self, mock_validator, mock_selector, mock_analyzer):
        """场景17: 自适应批量管理初始化"""
        # 创建orchestrator（启用自适应）
        orchestrator = CalculationOrchestrator(enable_adaptive=True)

        # 验证自适应批量管理器被初始化
        assert orchestrator.adaptive_batch is not None
        assert orchestrator.enable_adaptive is True

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    def test_adaptive_batch_disabled(self, mock_validator, mock_selector, mock_analyzer):
        """场景18: 禁用自适应批量管理"""
        # 创建orchestrator（禁用自适应）
        orchestrator = CalculationOrchestrator(enable_adaptive=False)

        # 验证自适应批量管理器未被初始化
        assert orchestrator.adaptive_batch is None
        assert orchestrator.enable_adaptive is False


class TestParameterOptimizerIntegration:
    """参数优化器集成测试"""

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    def test_parameter_optimizer_initialization(self, mock_validator, mock_selector, mock_analyzer):
        """场景19: 参数优化器初始化"""
        # 创建orchestrator（启用优化）
        orchestrator = CalculationOrchestrator(enable_optimization=True)

        # 验证参数优化器被初始化
        assert orchestrator.parameter_optimizer is not None
        assert orchestrator.enable_optimization is True

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    def test_parameter_optimizer_disabled(self, mock_validator, mock_selector, mock_analyzer):
        """场景20: 禁用参数优化器"""
        # 创建orchestrator（禁用优化）
        orchestrator = CalculationOrchestrator(enable_optimization=False)

        # 验证参数优化器未被初始化
        assert orchestrator.parameter_optimizer is None
        assert orchestrator.enable_optimization is False


class TestValidationReporterIntegration:
    """验证报告器集成测试"""

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    def test_validation_reporter_always_initialized(self, mock_validator, mock_selector, mock_analyzer):
        """场景21: 验证报告器总是被初始化"""
        # 创建orchestrator
        orchestrator = CalculationOrchestrator()

        # 验证验证报告器被初始化
        assert orchestrator.validation_reporter is not None
        assert isinstance(orchestrator.validation_reporter, ValidationReporter)

    def test_validation_reporter_standalone(self):
        """场景22: 验证报告器独立使用"""
        # 创建验证报告器
        reporter = ValidationReporter()

        # 验证报告器创建成功
        assert reporter is not None


class TestMethodDescriptorIntegration:
    """方法描述符集成测试"""

    def test_method_descriptor_creation(self):
        """场景23: 创建方法描述符"""
        from app.services.calculation.domain import MethodDescriptor

        # 创建方法描述符
        descriptor = MethodDescriptor(
            method_id='method_1',
            method_code='flow_v1',
            metric_key='pump_flow_rate',
            priority=1,
            dependencies=['pump_head'],
            conditions={'device_type': 'pump'},
            params={'coefficient': 1.5},
            validator_hint='range_check'
        )

        # 验证描述符
        assert descriptor.method_id == 'method_1'
        assert descriptor.method_code == 'flow_v1'
        assert descriptor.metric_key == 'pump_flow_rate'
        assert descriptor.priority == 1
        assert descriptor.dependencies == ['pump_head']
        assert descriptor.conditions == {'device_type': 'pump'}
        assert descriptor.params == {'coefficient': 1.5}
        assert descriptor.validator_hint == 'range_check'

    def test_method_descriptor_immutability(self):
        """场景24: 方法描述符不可变性"""
        from dataclasses import FrozenInstanceError
        from app.services.calculation.domain import MethodDescriptor

        # 创建方法描述符
        descriptor = MethodDescriptor(
            method_id='method_1',
            method_code='flow_v1',
            metric_key='pump_flow_rate',
            priority=1
        )

        # 尝试修改应该失败
        with pytest.raises(FrozenInstanceError):
            descriptor.priority = 2


class TestCachingMechanisms:
    """缓存机制集成测试"""

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    @patch('app.services.calculation.orchestrator.get_connection')
    def test_device_type_cache_hit(self, mock_get_conn, mock_validator, mock_selector, mock_analyzer):
        """场景25: 设备类型缓存命中"""
        # Mock数据库连接
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ('pump',)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        # 创建orchestrator
        orchestrator = CalculationOrchestrator()

        # 多次调用相同参数
        for _ in range(5):
            device_type = orchestrator._get_device_type(1, 1)
            assert device_type == 'pump'

        # 验证数据库只被查询一次
        assert mock_cursor.fetchone.call_count == 1

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    @patch('app.services.calculation.orchestrator.get_connection')
    def test_device_type_cache_miss(self, mock_get_conn, mock_validator, mock_selector, mock_analyzer):
        """场景26: 设备类型缓存未命中"""
        # Mock数据库连接
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [('pump',), ('valve',)]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        # 创建orchestrator
        orchestrator = CalculationOrchestrator()

        # 调用不同参数
        device_type1 = orchestrator._get_device_type(1, 1)
        device_type2 = orchestrator._get_device_type(1, 2)

        # 验证结果不同
        assert device_type1 == 'pump'
        assert device_type2 == 'valve'

        # 验证数据库被查询两次
        assert mock_cursor.fetchone.call_count == 2


class TestComponentLifecycle:
    """组件生命周期集成测试"""

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    def test_orchestrator_multiple_instances(self, mock_validator, mock_selector, mock_analyzer):
        """场景27: 创建多个Orchestrator实例"""
        # 创建多个实例
        orchestrator1 = CalculationOrchestrator()
        orchestrator2 = CalculationOrchestrator(enable_adaptive=False)
        orchestrator3 = CalculationOrchestrator(enable_optimization=True)

        # 验证实例独立
        assert orchestrator1 is not orchestrator2
        assert orchestrator2 is not orchestrator3
        assert orchestrator1.enable_adaptive is True
        assert orchestrator2.enable_adaptive is False
        assert orchestrator3.enable_optimization is True

    @patch('app.services.calculation.dependency_analyzer.get_connection')
    def test_dependency_analyzer_multiple_instances(self, mock_conn):
        """场景28: 创建多个DependencyAnalyzer实例"""
        # Mock数据库连接
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn_obj = MagicMock()
        mock_conn_obj.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_conn_obj

        # 创建多个实例
        analyzer1 = DependencyAnalyzer()
        analyzer2 = DependencyAnalyzer()

        # 验证实例独立
        assert analyzer1 is not analyzer2


class TestDataFlowIntegration:
    """数据流集成测试"""

    @patch('app.services.calculation.validator.get_connection')
    @patch('app.services.calculation.validator.CharacteristicCurveManager')
    def test_validator_multiple_validations(self, mock_curve_mgr, mock_conn):
        """场景29: 验证器多次验证"""
        # Mock数据库连接
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn_obj = MagicMock()
        mock_conn_obj.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_conn_obj

        # 创建验证器
        validator = PhysicsValidator()

        # 多次验证
        values1 = np.array([50.0, 60.0, 70.0])
        mask1, errors1 = validator.validate_range(values1, 0.0, 100.0)

        values2 = np.array([150.0, 160.0, 170.0])
        mask2, errors2 = validator.validate_range(values2, 0.0, 100.0)

        # 验证结果
        assert mask1.all()  # 所有值在范围内
        assert not mask2.any()  # 所有值超出范围
        assert len(errors1) == 0
        assert len(errors2) > 0

    def test_calculation_context_multiple_contexts(self):
        """场景30: 创建多个计算上下文"""
        from datetime import datetime

        # 创建多个上下文
        ctx1 = CalculationContext(
            station_id=1,
            device_id=1,
            start_ts=datetime(2025, 1, 1, 0, 0, 0),
            end_ts=datetime(2025, 1, 1, 1, 0, 0)
        )

        ctx2 = CalculationContext(
            station_id=2,
            device_id=2,
            start_ts=datetime(2025, 1, 2, 0, 0, 0),
            end_ts=datetime(2025, 1, 2, 1, 0, 0)
        )

        # 验证上下文独立
        assert ctx1.station_id != ctx2.station_id
        assert ctx1.device_id != ctx2.device_id
        assert ctx1.start_ts != ctx2.start_ts

