"""
泵组处理层测试 (test_pump_group_layer.py)

测试 pump_group 模块中的所有类：
- PumpGroupProcessor: 泵组处理器
- ParallelSynthesizer: 并联合成器
- SystemCorrectionModel: 系统修正模型
- FrequencyDataProvider: 频率数据提供器
- PumpGroupValidator: 泵组验证器
- PumpGroupResultStorage: 泵组结果存储
- ScenarioHandler: 场景处理器
- P2Pipeline: P2管道

测试用例遵循约束：
- 禁止使用默认值，所有参数显式指定
- 禁止回退机制

版本: v1.0
更新日期: 2025-12-09
"""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from app.services.characteristic_curves.models import GroupProcessingStrategy
from app.services.characteristic_curves.pump_group import (
    PumpGroupProcessor,
    ParallelSynthesizer,
    SystemCorrectionModel,
    CorrectionModelConfig,
    FrequencyDataProvider,
    PumpGroupValidator,
    ValidationResult,
    PumpGroupResultStorage,
    GroupFitResult,
    ScenarioHandler,
    Scenario,
    ScenarioContext,
    P2Pipeline,
    P2PipelineResult,
)
from app.services.characteristic_curves.shared.exceptions import (
    InsufficientDataError,
    FrequencyQueryError,
    DataNotFoundError,
)


class TestPumpGroupProcessor:
    """PumpGroupProcessor 泵组处理器测试"""

    @pytest.fixture
    def mock_synthesizer(self):
        """Mock并联合成器"""
        return MagicMock()

    @pytest.fixture
    def mock_correction_model(self):
        """Mock修正模型"""
        return MagicMock()

    @pytest.fixture
    def mock_freq_provider(self):
        """Mock频率数据提供器"""
        provider = MagicMock()
        provider.calculate_freq_std.return_value = 1.0  # 频率差 < 2%
        return provider

    @pytest.fixture
    def processor(self, mock_synthesizer, mock_correction_model, mock_freq_provider):
        """创建处理器实例"""
        return PumpGroupProcessor(
            parallel_synthesizer=mock_synthesizer,
            correction_model=mock_correction_model,
            freq_provider=mock_freq_provider,
            power_diff_threshold=0.10,
            freq_diff_threshold=2.0,
        )

    @pytest.fixture
    def sample_pump_infos(self):
        """示例泵信息"""
        return [
            {"pump_id": 1, "control_type": "VFD", "rated_power": 75.0},
            {"pump_id": 2, "control_type": "VFD", "rated_power": 75.0},
            {"pump_id": 3, "control_type": "VFD", "rated_power": 75.0},
        ]

    def test_identify_homogeneous_group(self, processor, sample_pump_infos):
        """PGP-001: 识别同构泵组（功率相同、频率差<2%）"""
        # 同功率、同类型
        result = processor.identify_group_type(pump_infos=sample_pump_infos)

        # 纯VFD、功率相同 → 同构泵组
        assert result == GroupProcessingStrategy.HOMOGENEOUS_GROUP

    def test_identify_heterogeneous_group(self, processor):
        """PGP-002: 识别异构泵组（功率差≥10%）"""
        pump_infos = [
            {"pump_id": 1, "control_type": "VFD", "rated_power": 75.0},
            {"pump_id": 2, "control_type": "VFD", "rated_power": 90.0},  # 功率差20%
        ]

        result = processor.identify_group_type(pump_infos=pump_infos)

        assert result == GroupProcessingStrategy.HETEROGENEOUS_GROUP

    def test_identify_mixed_group(self, processor):
        """PGP-003: 识别混合泵组（VFD+SS）"""
        pump_infos = [
            {"pump_id": 1, "control_type": "VFD", "rated_power": 75.0},
            {"pump_id": 2, "control_type": "SS", "rated_power": 75.0},  # 软启泵
        ]

        result = processor.identify_group_type(pump_infos=pump_infos)

        assert result == GroupProcessingStrategy.MIXED_GROUP

    def test_identify_mixed_heterogeneous_group(self, processor):
        """PGP-004: 识别混合异构泵组（VFD+SS，功率差≥10%）"""
        pump_infos = [
            {"pump_id": 1, "control_type": "VFD", "rated_power": 75.0},
            {"pump_id": 2, "control_type": "SS", "rated_power": 90.0},  # 功率差20%
        ]

        result = processor.identify_group_type(pump_infos=pump_infos)

        assert result == GroupProcessingStrategy.MIXED_HETEROGENEOUS


class TestParallelSynthesizer:
    """ParallelSynthesizer 并联合成器测试"""

    @pytest.fixture
    def synthesizer(self):
        """创建合成器实例"""
        return ParallelSynthesizer()

    @pytest.fixture
    def sample_curve_func(self):
        """示例曲线函数（二次多项式 H = 100 - 0.01*Q^2）"""
        def forward(Q: float) -> float:
            return 100.0 - 0.01 * Q * Q

        def inverse(H: float) -> float:
            if H > 100.0:
                return 0.0
            return np.sqrt((100.0 - H) / 0.01)

        return forward, inverse

    def test_register_pump_curve(self, synthesizer, sample_curve_func):
        """PS-001: 注册泵曲线"""
        forward, inverse = sample_curve_func

        synthesizer.register_pump_curve(
            pump_id=1,
            curve_func=forward,
            inverse_func=inverse,
        )

        # 验证注册成功
        assert 1 in synthesizer._pump_curves

    def test_synthesize_homogeneous(self, synthesizer, sample_curve_func):
        """PS-002: 同构泵组合成"""
        forward, inverse = sample_curve_func

        # 注册基准泵
        synthesizer.register_pump_curve(
            pump_id=1,
            curve_func=forward,
            inverse_func=inverse,
        )

        # 合成同构泵组曲线（3台泵）
        result = synthesizer.synthesize_homogeneous(base_pump_id=1, n_pumps=3)

        # 验证合成结果是一个可调用函数
        assert callable(result)

        # 并联特性：扬程相同，流量相加
        # 单泵Q=50时H=75，三泵并联总流量=150，扬程=75
        single_H = forward(50.0)
        total_Q = 150.0  # 3 * 50

        # 合成曲线：输入总流量，返回扬程
        synth_H = result(total_Q)
        assert abs(synth_H - single_H) < 1.0  # 允许1m误差

    def test_synthesize_heterogeneous(self, synthesizer):
        """PS-003: 异构泵组合成"""
        # 两台不同功率的泵
        def forward1(Q: float) -> float:
            return 100.0 - 0.01 * Q * Q  # 较大泵

        def forward2(Q: float) -> float:
            return 80.0 - 0.015 * Q * Q  # 较小泵

        def inverse1(H: float) -> float:
            return np.sqrt(max(0, (100.0 - H) / 0.01))

        def inverse2(H: float) -> float:
            return np.sqrt(max(0, (80.0 - H) / 0.015))

        synthesizer.register_pump_curve(1, forward1, inverse1)
        synthesizer.register_pump_curve(2, forward2, inverse2)

        # 异构合成需要指定H_system
        result = synthesizer.synthesize_heterogeneous(pump_ids=[1, 2], H_system=70.0)

        assert result is not None
        assert result.H_system == 70.0


class TestSystemCorrectionModel:
    """SystemCorrectionModel 系统修正模型测试"""

    @pytest.fixture
    def model(self):
        """创建模型实例"""
        config = CorrectionModelConfig(
            model_type="polynomial",
            polynomial_degree=2,
            min_training_points=5,  # 测试用较低阈值
        )
        return SystemCorrectionModel(config=config)

    @pytest.fixture
    def training_data(self):
        """生成训练数据 [N, Q_total, H_theoretical, H_actual]"""
        np.random.seed(42)
        n_samples = 10
        N = np.full(n_samples, 3)  # 3台泵
        Q_total = np.random.uniform(100, 400, n_samples)
        H_theo = 80.0 - 0.0005 * Q_total ** 2  # 理论扬程
        alpha = 1.05 + np.random.normal(0, 0.01, n_samples)  # 修正系数
        H_actual = H_theo * alpha  # 实际扬程
        return np.column_stack([N, Q_total, H_theo, H_actual])

    def test_fit_linear_model(self, training_data):
        """SCM-001: 线性模型训练"""
        config = CorrectionModelConfig(
            model_type="linear",
            min_training_points=5,
        )
        model = SystemCorrectionModel(config=config)

        model.fit(station_id=1, pump_ids=[1, 2, 3], training_data=training_data)

        # 验证模型已训练
        assert model.is_fitted

    def test_fit_polynomial_model(self, model, training_data):
        """SCM-002: 多项式模型训练"""
        model.fit(station_id=1, pump_ids=[1, 2, 3], training_data=training_data)
        assert model.is_fitted

    def test_apply_correction(self, model, training_data):
        """SCM-003: 应用修正"""
        model.fit(station_id=1, pump_ids=[1, 2, 3], training_data=training_data)

        # 理论扬程
        H_theoretical = 60.0
        N = 3
        Q_total = 200.0

        # 应用修正
        corrected_head = model.apply_correction(
            H_theoretical=H_theoretical,
            N=N,
            Q_total=Q_total,
        )

        # 修正后扬程应略高于理论值（因为α约1.05）
        assert corrected_head > H_theoretical * 0.9
        assert corrected_head < H_theoretical * 1.3

    def test_serialize_deserialize(self, model, training_data):
        """SCM-004: 序列化和反序列化"""
        model.fit(station_id=1, pump_ids=[1, 2, 3], training_data=training_data)

        # 序列化
        model_dict = model.to_dict()

        # 反序列化
        restored_model = SystemCorrectionModel.from_dict(model_dict)

        # 验证模型状态
        assert restored_model.is_fitted == model.is_fitted


class TestPumpGroupValidator:
    """PumpGroupValidator 泵组验证器测试"""

    @pytest.fixture
    def validator(self):
        """创建验证器实例"""
        return PumpGroupValidator()

    @pytest.fixture
    def mock_curve_registry(self):
        """Mock曲线注册表"""
        registry = MagicMock()
        registry.has_curve.return_value = True
        # 返回真实的数值而不是MagicMock
        registry.get_curve_metadata.return_value = {"h0": 100.0, "k": 0.01}
        # get_entry返回模拟的曲线条目
        mock_entry = MagicMock()
        mock_entry.h0 = 100.0
        mock_entry.k = 0.01
        registry.get_entry.return_value = mock_entry
        return registry

    def test_validate_group_config_success(self, validator):
        """PGV-001: 配置验证成功"""
        pump_infos = [
            {"pump_id": 1, "control_type": "VFD", "rated_power": 75.0},
            {"pump_id": 2, "control_type": "VFD", "rated_power": 75.0},
        ]

        result = validator.validate_group_config(pump_infos=pump_infos)

        assert result.is_valid

    def test_validate_group_config_insufficient_pumps(self, validator):
        """PGV-002: 泵数不足验证（空泵列表）"""
        pump_infos = []

        result = validator.validate_group_config(pump_infos=pump_infos)

        assert not result.is_valid
        assert len(result.errors) > 0

    def test_validate_physics_consistency(self, validator):
        """PGV-003: 物理一致性验证"""
        pump_infos = [
            {"pump_id": 1, "control_type": "VFD", "rated_power": 75.0},
            {"pump_id": 2, "control_type": "VFD", "rated_power": 75.0},
        ]

        result = validator.validate_physics_consistency(
            pump_infos=pump_infos,
            group_type=GroupProcessingStrategy.HOMOGENEOUS_GROUP,
        )

        assert result.is_valid

    def test_validate_all(self, validator, mock_curve_registry):
        """PGV-004: 综合验证"""
        pump_infos = [
            {"pump_id": 1, "control_type": "VFD", "rated_power": 75.0},
            {"pump_id": 2, "control_type": "VFD", "rated_power": 75.0},
        ]

        result = validator.validate_all(
            pump_infos=pump_infos,
            group_type=GroupProcessingStrategy.HOMOGENEOUS_GROUP,
            curve_registry=mock_curve_registry,
        )

        assert isinstance(result, ValidationResult)


class TestScenarioHandler:
    """ScenarioHandler 场景处理器测试"""

    @pytest.fixture
    def handler(self):
        """创建处理器实例"""
        return ScenarioHandler()

    def test_identify_single_pump_vfd(self, handler):
        """SH-001: 识别VFD单泵场景"""
        scenario = handler.identify_single_pump_scenario(
            control_type="VFD",
            freq_std=5.0,  # 频率变化大
        )

        assert scenario == Scenario.VFD_SINGLE

    def test_identify_single_pump_ss(self, handler):
        """SH-002: 识别软启单泵场景"""
        scenario = handler.identify_single_pump_scenario(
            control_type="SS",
            freq_std=0.0,
        )

        assert scenario == Scenario.SOFT_START_SINGLE

    def test_identify_quasi_fixed_freq(self, handler):
        """SH-003: 识别类工频变频泵场景"""
        scenario = handler.identify_single_pump_scenario(
            control_type="VFD",
            freq_std=1.0,  # 频率变化小
        )

        assert scenario == Scenario.QUASI_FIXED_FREQ_SINGLE

    def test_identify_group_scenario(self, handler):
        """SH-004: 识别泵组场景"""
        scenario = handler.identify_group_scenario(
            group_type=GroupProcessingStrategy.HOMOGENEOUS_GROUP
        )

        assert scenario == Scenario.HOMOGENEOUS_GROUP

    def test_build_context(self, handler):
        """SH-005: 构建场景上下文"""
        pump_infos = [
            {"pump_id": 1, "control_type": "VFD"},
            {"pump_id": 2, "control_type": "VFD"},
        ]

        context = handler.build_context(
            pump_infos=pump_infos,
            freq_std=3.0,
            group_type=GroupProcessingStrategy.HOMOGENEOUS_GROUP,
        )

        assert isinstance(context, ScenarioContext)
        assert context.pump_count == 2
        assert not context.is_single_pump
        assert context.is_vfd

    def test_get_stage_sequence(self, handler):
        """SH-006: 获取阶段序列"""
        pump_infos = [{"pump_id": 1, "control_type": "VFD"}]
        context = handler.build_context(pump_infos=pump_infos, freq_std=0.5)

        stages = handler.get_stage_sequence(context)

        assert len(stages) > 0
        assert "fit_execute" in stages  # 阶段10必须存在


class TestP2Pipeline:
    """P2Pipeline P2管道测试"""

    @pytest.fixture
    def mock_registry(self):
        """Mock曲线注册表"""
        registry = MagicMock()
        registry.has_curve.return_value = True
        registry.get_forward.return_value = lambda Q: 100.0 - 0.01 * Q * Q
        registry.get_inverse.return_value = lambda H: np.sqrt(max(0, (100.0 - H) / 0.01))
        return registry

    @pytest.fixture
    def mock_processor(self):
        """Mock泵组处理器"""
        processor = MagicMock()
        processor.identify_group_type.return_value = GroupProcessingStrategy.HOMOGENEOUS_GROUP
        return processor

    @pytest.fixture
    def mock_synthesizer(self):
        """Mock并联合成器"""
        synthesizer = MagicMock()
        return synthesizer

    def test_check_entry_conditions_success(self, mock_registry):
        """P2P-001: 入口条件检查成功"""
        pipeline = P2Pipeline(curve_registry=mock_registry)

        can_enter, reasons = pipeline.check_entry_conditions(
            pump_ids=[1, 2, 3],
            curve_type="qh",
        )

        assert can_enter
        assert len(reasons) == 0

    def test_check_entry_conditions_insufficient_pumps(self):
        """P2P-002: 入口条件检查失败（泵数不足）"""
        pipeline = P2Pipeline()

        can_enter, reasons = pipeline.check_entry_conditions(
            pump_ids=[1],  # 只有1台泵
            curve_type="qh",
        )

        assert not can_enter
        assert len(reasons) > 0

    def test_execute_success(self, mock_registry, mock_processor, mock_synthesizer):
        """P2P-003: 执行成功"""
        pipeline = P2Pipeline(
            pump_group_processor=mock_processor,
            parallel_synthesizer=mock_synthesizer,
            curve_registry=mock_registry,
        )

        pump_infos = [
            {"pump_id": 1, "control_type": "VFD"},
            {"pump_id": 2, "control_type": "VFD"},
        ]

        result = pipeline.execute(
            station_id=1,
            pump_infos=pump_infos,
            curve_type="qh",
        )

        assert isinstance(result, P2PipelineResult)
        # 验证阶段执行
        assert "entry_check" in result.stages_executed
        assert "stage_14_identify" in result.stages_executed


class TestGroupFitResult:
    """GroupFitResult 数据类测试"""

    def test_to_dict(self):
        """GFR-001: 转换为字典"""
        result = GroupFitResult(
            station_id=1,
            pump_combination=[1, 2, 3],
            group_type=GroupProcessingStrategy.HOMOGENEOUS_GROUP,
            curve_type="qh",
            pump_count=3,
            valid_n_range=(1, 3),
        )

        data = result.to_dict()

        assert data["station_id"] == 1
        assert data["pump_combination"] == [1, 2, 3]
        assert data["group_type"] == "homogeneous"

    def test_from_dict(self):
        """GFR-002: 从字典创建"""
        data = {
            "station_id": 1,
            "pump_combination": [1, 2],
            "group_type": "heterogeneous",
            "curve_type": "qh",
            "pump_count": 2,
            "valid_n_range": [1, 2],
        }

        result = GroupFitResult.from_dict(data)

        assert result.station_id == 1
        assert result.group_type == GroupProcessingStrategy.HETEROGENEOUS_GROUP

