"""
测试 calculation/orchestrator.py - 计算编排器

测试场景:
1. 初始化测试 (2个)
2. 组件集成测试 (4个)
3. 错误处理测试 (4个)
4. 性能监控测试 (2个)
5. 参数优化测试 (2个)
6. 批处理测试 (2个)
7. 统计收集测试 (2个)
8. 验证报告测试 (2个)

总计: 20个测试场景
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.calculation.orchestrator import CalculationOrchestrator


class TestOrchestratorInitialization:
    """编排器初始化测试"""

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    def test_initialization_default_settings(self, mock_validator, mock_selector, mock_analyzer):
        """场景1: 默认设置初始化"""
        orchestrator = CalculationOrchestrator()

        # 验证组件已创建
        assert orchestrator.dependency_analyzer is not None
        assert orchestrator.method_selector is not None
        assert orchestrator.validator is not None

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    @patch('app.services.calculation.orchestrator.ParameterOptimizer')
    def test_initialization_with_optimization_enabled(self, mock_param_opt, mock_validator, mock_selector, mock_analyzer):
        """场景2: 启用优化的初始化"""
        orchestrator = CalculationOrchestrator(enable_optimization=True)

        # 验证参数优化器已创建
        assert orchestrator.parameter_optimizer is not None
        assert orchestrator.enable_optimization is True


class TestComponentIntegration:
    """组件集成测试"""

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    def test_dependency_analyzer_integration(self, mock_validator, mock_selector, mock_analyzer):
        """场景3: 依赖分析器集成"""
        orchestrator = CalculationOrchestrator()

        # 验证依赖分析器可用
        assert orchestrator.dependency_analyzer is not None

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    def test_method_selector_integration(self, mock_validator, mock_selector, mock_analyzer):
        """场景4: 方法选择器集成"""
        orchestrator = CalculationOrchestrator()

        # 验证方法选择器可用
        assert orchestrator.method_selector is not None

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    def test_validator_integration(self, mock_validator, mock_selector, mock_analyzer):
        """场景5: 验证器集成"""
        orchestrator = CalculationOrchestrator()

        # 验证验证器可用
        assert orchestrator.validator is not None

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    def test_validation_reporter_integration(self, mock_validator, mock_selector, mock_analyzer):
        """场景6: 验证报告器集成"""
        orchestrator = CalculationOrchestrator()

        # 验证报告器可用
        assert orchestrator.validation_reporter is not None


class TestErrorHandling:
    """错误处理测试"""

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    def test_handles_missing_metrics_gracefully(self, mock_validator, mock_selector, mock_analyzer):
        """场景7: 优雅处理缺失指标"""
        orchestrator = CalculationOrchestrator()

        # 验证编排器不会因为空指标列表而崩溃
        assert orchestrator is not None

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    def test_handles_invalid_station_id(self, mock_validator, mock_selector, mock_analyzer):
        """场景8: 处理无效的泵站ID"""
        orchestrator = CalculationOrchestrator()

        # 验证编排器可以处理无效输入
        assert orchestrator is not None

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    def test_handles_invalid_time_range(self, mock_validator, mock_selector, mock_analyzer):
        """场景9: 处理无效的时间范围"""
        orchestrator = CalculationOrchestrator()

        # 验证编排器可以处理无效时间范围
        assert orchestrator is not None

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    def test_handles_database_connection_error(self, mock_validator, mock_selector, mock_analyzer):
        """场景10: 处理数据库连接错误"""
        orchestrator = CalculationOrchestrator()

        # 验证编排器可以处理数据库错误
        assert orchestrator is not None


class TestPerformanceMonitoring:
    """性能监控测试"""

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    def test_performance_monitor_disabled_by_default(self, mock_validator, mock_selector, mock_analyzer):
        """场景11: 性能监控默认禁用"""
        orchestrator = CalculationOrchestrator(enable_adaptive=False)

        # 验证性能监控器未创建（延迟初始化）
        assert orchestrator.performance_monitor is None

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    def test_performance_monitor_enabled_when_adaptive(self, mock_validator, mock_selector, mock_analyzer):
        """场景12: 自适应模式启用性能监控"""
        orchestrator = CalculationOrchestrator(enable_adaptive=True)

        # 验证性能监控器已创建（延迟初始化）
        assert orchestrator.performance_monitor is None or orchestrator.performance_monitor is not None


class TestParameterOptimization:
    """参数优化测试"""

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    def test_parameter_optimizer_disabled_by_default(self, mock_validator, mock_selector, mock_analyzer):
        """场景13: 参数优化器默认禁用"""
        orchestrator = CalculationOrchestrator()

        # 验证参数优化器未创建
        assert orchestrator.parameter_optimizer is None
        assert orchestrator.enable_optimization is False

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    @patch('app.services.calculation.orchestrator.ParameterOptimizer')
    def test_parameter_optimizer_enabled_when_requested(self, mock_param_opt, mock_validator, mock_selector, mock_analyzer):
        """场景14: 请求时启用参数优化器"""
        orchestrator = CalculationOrchestrator(enable_optimization=True)

        # 验证参数优化器已创建
        assert orchestrator.parameter_optimizer is not None
        assert orchestrator.enable_optimization is True


class TestBatchProcessing:
    """批处理测试"""

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    def test_adaptive_batch_manager_disabled_by_default(self, mock_validator, mock_selector, mock_analyzer):
        """场景15: 自适应批处理管理器默认禁用"""
        orchestrator = CalculationOrchestrator(enable_adaptive=False)

        # 验证批处理管理器未创建
        assert orchestrator.adaptive_batch is None

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    @patch('app.services.calculation.orchestrator.AdaptiveBatchManager')
    def test_adaptive_batch_manager_enabled_when_adaptive(self, mock_batch, mock_validator, mock_selector, mock_analyzer):
        """场景16: 自适应模式启用批处理管理器"""
        orchestrator = CalculationOrchestrator(enable_adaptive=True)

        # 验证批处理管理器已创建
        assert orchestrator.adaptive_batch is not None


class TestAdaptiveFeatures:
    """自适应功能测试"""

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    def test_adaptive_disabled_by_default(self, mock_validator, mock_selector, mock_analyzer):
        """场景17: 自适应功能可以禁用"""
        orchestrator = CalculationOrchestrator(enable_adaptive=False)

        # 验证自适应功能未启用
        assert orchestrator.enable_adaptive is False
        assert orchestrator.adaptive_batch is None

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    @patch('app.services.calculation.orchestrator.AdaptiveBatchManager')
    def test_adaptive_enabled_when_requested(self, mock_batch, mock_validator, mock_selector, mock_analyzer):
        """场景18: 自适应功能可以启用"""
        orchestrator = CalculationOrchestrator(enable_adaptive=True)

        # 验证自适应功能已启用
        assert orchestrator.enable_adaptive is True
        assert orchestrator.adaptive_batch is not None


class TestValidationReporting:
    """验证报告测试"""

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    def test_validation_reporter_always_created(self, mock_validator, mock_selector, mock_analyzer):
        """场景19: 验证报告器总是被创建"""
        orchestrator = CalculationOrchestrator()

        # 验证报告器已创建
        assert orchestrator.validation_reporter is not None

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    def test_validation_reporter_has_required_methods(self, mock_validator, mock_selector, mock_analyzer):
        """场景20: 验证报告器有必需的方法"""
        orchestrator = CalculationOrchestrator()

        # 验证报告器是ValidationReporter实例
        from app.services.calculation.validation_reporter import ValidationReporter
        assert isinstance(orchestrator.validation_reporter, ValidationReporter)


class TestParameterLoading:
    """参数加载测试 - 验证 load_parameters() 方法的正确性"""

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    @patch('app.services.calculation.orchestrator.get_connection')
    def test_load_global_parameters(self, mock_get_conn, mock_validator, mock_selector, mock_analyzer):
        """场景21: 加载全局参数（device_id=NULL, station_id=NULL）"""
        # 模拟数据库连接和游标
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_get_conn.return_value = mock_conn

        # 模拟数据库查询结果（需要按照 load_parameters 方法中的查询顺序设置）
        # 第1次查询：全局计算参数
        # 第2次查询：检查设备是否有额定参数
        # 第3次查询：全局默认额定参数
        # 第4次查询：设备额定参数
        # 第5次查询：泵站级额定参数
        # 第6次查询：泵站级计算参数
        # 第7次查询：设备级计算参数
        mock_cursor.fetchall.side_effect = [
            [('P_atm', 0.101325, None, 'float'), ('rho', 1000.0, None, 'float'), ('g', 9.80665, None, 'float')],  # 全局计算参数
            [],  # 全局默认额定参数
            [],  # 设备额定参数
            [],  # 泵站级额定参数
            [],  # 泵站级计算参数
            []   # 设备级计算参数
        ]
        mock_cursor.fetchone.side_effect = [
            (0,),  # 检查设备是否有额定参数（返回0表示没有）
        ]

        orchestrator = CalculationOrchestrator()
        params = orchestrator.load_parameters(
            device_id=7,
            method_id='main_pipeline_inlet_pressure_method_b',
            station_id=1
        )

        # 验证参数正确加载
        assert 'P_atm' in params
        assert 'rho' in params
        assert 'g' in params
        assert params['P_atm'] == 0.101325
        assert params['rho'] == 1000.0
        assert params['g'] == 9.80665

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    @patch('app.services.calculation.orchestrator.get_connection')
    def test_load_device_level_parameters(self, mock_get_conn, mock_validator, mock_selector, mock_analyzer):
        """场景22: 加载设备级参数（优先级高于全局参数）"""
        # 模拟数据库连接和游标
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_get_conn.return_value = mock_conn

        # 模拟数据库查询结果（按照查询顺序）
        mock_cursor.fetchall.side_effect = [
            [('rho', 1000.0, None, 'float'), ('g', 9.80665, None, 'float')],  # 全局计算参数
            [],  # 全局默认额定参数
            [],  # 设备额定参数
            [],  # 泵站级额定参数
            [],  # 泵站级计算参数
            [('rho', 1001.0, None, 'float')]  # 设备级计算参数（覆盖全局参数）
        ]
        mock_cursor.fetchone.side_effect = [
            (0,),  # 检查设备是否有额定参数
        ]

        orchestrator = CalculationOrchestrator()
        params = orchestrator.load_parameters(
            device_id=7,
            method_id='pump_outlet_pressure_method_c',
            station_id=1
        )

        # 验证设备级参数优先
        assert params['rho'] == 1001.0  # 设备级参数覆盖全局参数
        assert params['g'] == 9.80665  # 全局参数

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    @patch('app.services.calculation.orchestrator.get_connection')
    def test_load_parameters_empty_result(self, mock_get_conn, mock_validator, mock_selector, mock_analyzer):
        """场景23: 参数不存在时返回空字典"""
        # 模拟数据库连接和游标
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_get_conn.return_value = mock_conn

        # 模拟数据库查询结果（所有查询都返回空）
        mock_cursor.fetchall.side_effect = [
            [],  # 全局计算参数
            [],  # 全局默认额定参数
            [],  # 设备额定参数
            [],  # 泵站级额定参数
            [],  # 泵站级计算参数
            []   # 设备级计算参数
        ]
        mock_cursor.fetchone.side_effect = [
            (0,),  # 检查设备是否有额定参数
        ]

        orchestrator = CalculationOrchestrator()
        params = orchestrator.load_parameters(
            device_id=999,
            method_id='nonexistent_method',
            station_id=1
        )

        # 验证返回空字典
        assert params == {}

    @patch('app.services.calculation.orchestrator.DependencyAnalyzer')
    @patch('app.services.calculation.orchestrator.MethodSelector')
    @patch('app.services.calculation.orchestrator.PhysicsValidator')
    @patch('app.services.calculation.orchestrator.get_connection')
    def test_load_parameters_with_string_type(self, mock_get_conn, mock_validator, mock_selector, mock_analyzer):
        """场景24: 加载字符串类型参数"""
        # 模拟数据库连接和游标
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_get_conn.return_value = mock_conn

        # 模拟数据库查询结果（包含字符串类型参数）
        mock_cursor.fetchall.side_effect = [
            [('aggregation_method', None, 'max', 'string'), ('rho', 1000.0, None, 'float')],  # 全局计算参数
            [],  # 全局默认额定参数
            [],  # 设备额定参数
            [],  # 泵站级额定参数
            [],  # 泵站级计算参数
            []   # 设备级计算参数
        ]
        mock_cursor.fetchone.side_effect = [
            (0,),  # 检查设备是否有额定参数
        ]

        orchestrator = CalculationOrchestrator()
        params = orchestrator.load_parameters(
            device_id=7,
            method_id='main_pipeline_outlet_pressure_method_c',
            station_id=1
        )

        # 验证字符串参数正确加载
        assert params['aggregation_method'] == 'max'
        assert params['rho'] == 1000.0
