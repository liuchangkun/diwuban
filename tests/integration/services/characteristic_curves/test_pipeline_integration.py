"""
Pipeline 集成测试 (test_pipeline_integration.py)

测试 P0 和 P2 管道的端到端流程：
- P0单泵拟合管道（阶段1-13）
- P2泵组处理管道（阶段14-16）
- P0→P2完整流程

版本: v1.0
更新日期: 2025-12-09
"""

import numpy as np
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# P2模块已删除，暂时禁用此测试文件
pytestmark = pytest.mark.skip(reason="P2模块已删除，等待P0完成后重写")

# from app.services.characteristic_curves.core.data_structures import FitResult


class TestP0PipelineIntegration:
    """P0 单泵拟合管道集成测试"""

    @pytest.fixture
    def mock_data_provider(self):
        """Mock数据提供器"""
        provider = MagicMock()
        # 生成测试数据：Q-H曲线 H = 100 - 0.01*Q^2
        Q_values = np.linspace(0, 100, 50)
        H_values = 100.0 - 0.01 * Q_values ** 2 + np.random.normal(0, 1, 50)
        
        provider.get_qh_data.return_value = {
            "Q": Q_values.tolist(),
            "H": H_values.tolist(),
            "timestamps": [datetime.now() + timedelta(seconds=i) for i in range(50)],
        }
        return provider

    def test_p0_fitting_basic(self, mock_data_provider):
        """P0-INT-001: 基本拟合流程"""
        # 此测试验证拟合流程的基本执行
        # 由于依赖复杂，使用mock验证流程
        
        Q = np.array(mock_data_provider.get_qh_data()["Q"])
        H = np.array(mock_data_provider.get_qh_data()["H"])
        
        # 简单多项式拟合验证
        coeffs = np.polyfit(Q, H, 2)
        
        # 验证拟合质量
        H_pred = np.polyval(coeffs, Q)
        r_squared = 1 - np.sum((H - H_pred) ** 2) / np.sum((H - np.mean(H)) ** 2)
        
        assert r_squared > 0.9  # R² > 0.9


class TestP2PipelineIntegration:
    """P2 泵组处理管道集成测试"""

    @pytest.fixture
    def sample_qh_curve(self):
        """示例Q-H曲线函数"""
        def forward(Q: float) -> float:
            return 100.0 - 0.01 * Q * Q
        
        def inverse(H: float) -> float:
            if H > 100.0:
                return 0.0
            return np.sqrt(max(0, (100.0 - H) / 0.01))
        
        return forward, inverse

    @pytest.fixture
    def mock_curve_registry(self, sample_qh_curve):
        """Mock P2曲线注册表"""
        forward, inverse = sample_qh_curve
        
        registry = MagicMock()
        registry.has_curve.return_value = True
        registry.get_forward.return_value = forward
        registry.get_inverse.return_value = inverse
        return registry

    def test_p2_homogeneous_group_integration(self, mock_curve_registry):
        """P2-INT-001: 同构泵组完整流程"""
        # 创建组件
        processor = PumpGroupProcessor(station_id=1)
        synthesizer = ParallelSynthesizer(station_id=1)
        validator = PumpGroupValidator()
        
        # 创建P2管道
        pipeline = P2Pipeline(
            pump_group_processor=processor,
            parallel_synthesizer=synthesizer,
            curve_registry=mock_curve_registry,
            validator=validator,
        )
        
        # 泵组信息（3台相同VFD泵）
        pump_infos = [
            {"pump_id": 1, "control_type": "VFD", "rated_power": 75.0},
            {"pump_id": 2, "control_type": "VFD", "rated_power": 75.0},
            {"pump_id": 3, "control_type": "VFD", "rated_power": 75.0},
        ]
        
        # 执行P2管道
        result = pipeline.execute(
            station_id=1,
            pump_infos=pump_infos,
            curve_type="qh",
        )
        
        # 验证结果
        assert isinstance(result, P2PipelineResult)
        assert result.group_type == GroupProcessingStrategy.HOMOGENEOUS_GROUP
        assert "stage_14_identify" in result.stages_executed

    def test_p2_mixed_group_integration(self, mock_curve_registry):
        """P2-INT-002: 混合泵组完整流程"""
        processor = PumpGroupProcessor(station_id=1)
        synthesizer = ParallelSynthesizer(station_id=1)
        
        pipeline = P2Pipeline(
            pump_group_processor=processor,
            parallel_synthesizer=synthesizer,
            curve_registry=mock_curve_registry,
        )
        
        # 混合泵组（VFD + SS）
        pump_infos = [
            {"pump_id": 1, "control_type": "VFD", "rated_power": 75.0},
            {"pump_id": 2, "control_type": "SS", "rated_power": 75.0},
        ]
        
        result = pipeline.execute(
            station_id=1,
            pump_infos=pump_infos,
            curve_type="qh",
        )
        
        assert result.group_type == GroupProcessingStrategy.MIXED_GROUP

    def test_p2_entry_condition_failure(self):
        """P2-INT-003: 入口条件失败"""
        pipeline = P2Pipeline()
        
        # 只有1台泵，不满足入口条件
        pump_infos = [
            {"pump_id": 1, "control_type": "VFD"},
        ]
        
        result = pipeline.execute(
            station_id=1,
            pump_infos=pump_infos,
            curve_type="qh",
        )
        
        assert not result.success
        assert "入口条件不满足" in result.error_message


class TestScenarioIntegration:
    """场景识别集成测试"""

    @pytest.fixture
    def handler(self):
        """场景处理器"""
        return ScenarioHandler()

    def test_scenario_to_stage_sequence(self, handler):
        """SC-INT-001: 场景到阶段序列映射"""
        # 单泵VFD场景
        pump_infos = [{"pump_id": 1, "control_type": "VFD"}]
        context = handler.build_context(
            pump_infos=pump_infos,
            freq_std=5.0,  # 频率变化大
        )

        stages = handler.get_stage_sequence(context)

        # 验证P0阶段存在
        assert "data_extract" in stages
        assert "fit_execute" in stages
        assert "result_store" in stages

        # 单泵不应有P2阶段
        assert "group_identify" not in stages
        assert "parallel_synthesize" not in stages

    def test_group_scenario_stage_sequence(self, handler):
        """SC-INT-002: 泵组场景阶段序列"""
        pump_infos = [
            {"pump_id": 1, "control_type": "VFD"},
            {"pump_id": 2, "control_type": "VFD"},
        ]

        context = handler.build_context(
            pump_infos=pump_infos,
            freq_std=1.0,
            group_type=GroupProcessingStrategy.HOMOGENEOUS_GROUP,
        )

        stages = handler.get_stage_sequence(context)

        # 泵组应有P2阶段
        assert "group_identify" in stages
        assert "parallel_synthesize" in stages
        assert "group_store" in stages


class TestEndToEndIntegration:
    """端到端集成测试"""

    @pytest.fixture
    def sample_curves(self):
        """生成测试曲线"""
        def make_curve(h_max: float, coeff: float):
            def forward(Q: float) -> float:
                return h_max - coeff * Q * Q

            def inverse(H: float) -> float:
                if H > h_max:
                    return 0.0
                return np.sqrt(max(0, (h_max - H) / coeff))

            return forward, inverse

        return {
            1: make_curve(100.0, 0.01),
            2: make_curve(100.0, 0.01),
            3: make_curve(100.0, 0.01),
        }

    def test_full_p0_to_p2_flow(self, sample_curves):
        """E2E-001: 完整P0→P2流程"""
        # 模拟P0完成后的状态
        mock_registry = MagicMock()
        mock_registry.has_curve.return_value = True

        def get_forward(pump_id, curve_type):
            return sample_curves[pump_id][0]

        def get_inverse(pump_id, curve_type):
            return sample_curves[pump_id][1]

        mock_registry.get_forward.side_effect = get_forward
        mock_registry.get_inverse.side_effect = get_inverse

        # 创建P2组件
        processor = PumpGroupProcessor(station_id=1)
        synthesizer = ParallelSynthesizer(station_id=1)

        # 注册曲线到合成器
        for pump_id, (fwd, inv) in sample_curves.items():
            synthesizer.register_pump_curve(pump_id, fwd, inv, "qh")

        # 创建P2管道
        pipeline = P2Pipeline(
            pump_group_processor=processor,
            parallel_synthesizer=synthesizer,
            curve_registry=mock_registry,
        )

        # 执行
        pump_infos = [
            {"pump_id": 1, "control_type": "VFD", "rated_power": 75.0},
            {"pump_id": 2, "control_type": "VFD", "rated_power": 75.0},
            {"pump_id": 3, "control_type": "VFD", "rated_power": 75.0},
        ]

        result = pipeline.execute(
            station_id=1,
            pump_infos=pump_infos,
            curve_type="qh",
        )

        # 验证
        assert result.group_type == GroupProcessingStrategy.HOMOGENEOUS_GROUP
        assert len(result.stages_executed) >= 2

    def test_parallel_synthesis_physics(self, sample_curves):
        """E2E-002: 并联合成物理验证"""
        synthesizer = ParallelSynthesizer(station_id=1)

        # 注册3台相同泵
        for pump_id, (fwd, inv) in sample_curves.items():
            synthesizer.register_pump_curve(pump_id, fwd, inv, "qh")

        # 合成同构泵组
        result = synthesizer.synthesize_homogeneous(
            pump_ids=[1, 2, 3],
            curve_type="qh",
        )

        # 物理验证：并联特性
        # 单泵Q=50时，H = 100 - 0.01*50^2 = 75m
        single_Q = 50.0
        single_H = sample_curves[1][0](single_Q)

        # 3泵并联，总流量 = 3 * 50 = 150 m³/h
        total_Q = 150.0

        # 合成曲线的扬程应等于单泵扬程（并联特性）
        synth_H = result["forward"](total_Q)

        assert abs(synth_H - single_H) < 2.0  # 允许2m误差

        # 逆向验证：给定扬程，计算总流量
        synth_Q = result["inverse"](single_H)
        assert abs(synth_Q - total_Q) < 5.0  # 允许5m³/h误差

