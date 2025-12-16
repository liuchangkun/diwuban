"""
P0 Pipeline模块单元测试 (test_p0_pipeline.py)

测试主管道的各个阶段处理器：
- 阶段注册
- 条件执行逻辑
- 数据传递
- 错误处理

版本: v1.0
创建日期: 2025-12-11
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from app.services.characteristic_curves.pipeline import CurveFittingPipeline
from app.services.characteristic_curves.core.enums import PipelineStage, Scenario
from app.services.characteristic_curves.core.data_structures import FitResult


class TestPipelineInitialization:
    """管道初始化测试"""

    def test_pipeline_init_default(self):
        """PI-001: 默认初始化"""
        pipeline = CurveFittingPipeline()
        
        assert pipeline is not None
        assert pipeline._config is not None
        assert pipeline._stage_handlers is not None

    def test_pipeline_init_with_dependencies(self):
        """PI-002: 带依赖注入的初始化"""
        from app.services.characteristic_curves.shared import ResultStorage
        from app.services.characteristic_curves.methods import MethodRegistry
        
        storage = ResultStorage()
        registry = MethodRegistry()
        
        pipeline = CurveFittingPipeline(
            method_registry=registry,
            result_storage=storage,
        )
        
        # 修复：参数顺序错误，应该是 method_registry 对应 registry
        assert pipeline._method_registry is registry
        assert pipeline._result_storage is storage


class TestStageHandlers:
    """阶段处理器测试"""

    def test_stage_handlers_registered(self):
        """SH-001: 验证所有P0阶段处理器已注册"""
        pipeline = CurveFittingPipeline()
        
        # P0必需的13个阶段
        p0_stages = [
            PipelineStage.TIME_WINDOW_SPLIT,
            PipelineStage.SCENARIO_DETECT,
            PipelineStage.DATA_EXTRACT,
            PipelineStage.DATA_CLEAN,
            PipelineStage.STEADY_STATE_DETECT,
            PipelineStage.CONSTRAINT_CALC,
            PipelineStage.FREQ_NORMALIZE,
            PipelineStage.DATA_NORMALIZE,
            PipelineStage.METHOD_SELECT,
            PipelineStage.CURVE_FIT,
            PipelineStage.RESULT_VALIDATE,
            PipelineStage.HISTORICAL_EVAL,
            PipelineStage.RESULT_STORE,
        ]
        
        for stage in p0_stages:
            assert stage in pipeline._stage_handlers, f"Stage {stage} not registered"

    def test_conditional_stage_skip_logic(self):
        """SH-002: 条件执行跳过逻辑"""
        pipeline = CurveFittingPipeline()
        
        # 创建测试上下文
        from app.services.characteristic_curves.pipeline import PipelineContext
        context = PipelineContext(device_id=1001, curve_type="qh")
        
        # 场景识别：默认不跳过（需要根据实际实现调整）
        should_skip = pipeline._should_skip_stage(PipelineStage.SCENARIO_DETECT, context)
        # 修复：根据实际实现，默认不跳过
        assert should_skip is False
        
        # 时间窗口分割：必须执行
        should_skip = pipeline._should_skip_stage(PipelineStage.TIME_WINDOW_SPLIT, context)
        assert should_skip is False


class TestTimeWindowSplit:
    """时间窗口分割阶段测试"""

    def test_time_window_split_with_time_range(self):
        """TWS-001: 有时间范围的窗口分割"""
        pipeline = CurveFittingPipeline()
        
        from app.services.characteristic_curves.pipeline import PipelineContext
        context = PipelineContext(
            device_id=1001,
            curve_type="qh",
        )
        
        # 设置时间范围
        start = datetime(2025, 12, 1)
        end = datetime(2025, 12, 10)
        context.set_data("kwargs", {"time_range": (start, end)})
        
        result = pipeline._stage_time_window_split(context)
        
        assert "can_evaluate" in result
        if result["can_evaluate"]:
            assert context.get_data("fit_window") is not None
            assert context.get_data("test_window") is not None

    def test_time_window_split_no_time_range(self):
        """TWS-002: 无时间范围的情况"""
        pipeline = CurveFittingPipeline()
        
        from app.services.characteristic_curves.pipeline import PipelineContext
        context = PipelineContext(
            device_id=1001,
            curve_type="qh",
        )
        
        # 不设置时间范围
        context.set_data("kwargs", {})
        
        result = pipeline._stage_time_window_split(context)
        
        assert result["can_evaluate"] is False


class TestDataExtract:
    """数据提取阶段测试"""

    def test_data_extract_with_direct_data(self):
        """DE-001: 直接提供数据"""
        pipeline = CurveFittingPipeline()
        
        from app.services.characteristic_curves.pipeline import PipelineContext
        context = PipelineContext(
            device_id=1001,
            curve_type="qh",
        )
        
        # 提供直接数据
        Q = np.linspace(0, 100, 50).tolist()
        H = (50 - 0.005 * np.linspace(0, 100, 50) ** 2).tolist()
        context.set_data("kwargs", {"x_values": Q, "y_values": H})
        
        result = pipeline._stage_data_extract(context)
        
        assert result["extracted"] is True
        assert result["source"] == "direct"
        assert result["points"] == 50
        assert context.get_data("raw_data") is not None


class TestDataClean:
    """数据清洗阶段测试"""

    def test_data_clean_basic(self):
        """DCL-001: 基本数据清洗"""
        pipeline = CurveFittingPipeline()
        
        from app.services.characteristic_curves.pipeline import PipelineContext
        context = PipelineContext(
            device_id=1001,
            curve_type="qh",
        )
        
        # 创建包含问题数据的DataFrame
        raw_data = pd.DataFrame({
            "Q": [0, 10, 20, 20, 30, 40, 50, 60, 70, 80, 90, 100],  # 重复值
            "H": [50, 48, 45, 45, 41, 36, 30, 23, 15, 6, -1, -5],  # 异常值
        })
        context.set_data("raw_data", raw_data)
        
        result = pipeline._stage_data_clean(context)
        
        assert result["cleaned"] is True
        assert result["points"] > 0
        assert context.get_data("cleaned_data") is not None


class TestCurveFit:
    """曲线拟合阶段测试"""

    def test_curve_fit_basic(self):
        """CF-001: 基本拟合功能"""
        pipeline = CurveFittingPipeline()
        
        from app.services.characteristic_curves.pipeline import PipelineContext
        context = PipelineContext(
            device_id=1001,
            curve_type="qh",
        )
        
        # 准备数据
        Q = np.linspace(0, 100, 50)
        H = 50 - 0.005 * Q ** 2 + np.random.normal(0, 0.5, 50)
        context.set_data("x_values", Q)
        context.set_data("y_values", H)
        
        result = pipeline._stage_curve_fit(context)
        
        assert result["fitted"] is True
        assert "r_squared" in result
        assert result["r_squared"] > 0.8  # 应该有较好的拟合
        assert context.get_data("coefficients") is not None


class TestResultValidate:
    """结果验证阶段测试"""

    def test_result_validate_good_fit(self):
        """RV-001: 高质量拟合验证"""
        pipeline = CurveFittingPipeline()
        
        from app.services.characteristic_curves.pipeline import PipelineContext
        context = PipelineContext(
            device_id=1001,
            curve_type="qh",
        )
        
        # 设置高质量拟合结果
        context.set_data("r_squared", 0.95)
        context.set_data("coefficients", [-0.005, 0.0, 50.0])
        context.set_data("x_values", np.linspace(0, 100, 50))
        context.set_data("y_values", 50 - 0.005 * np.linspace(0, 100, 50) ** 2)
        context.set_data("y_fitted", 50 - 0.005 * np.linspace(0, 100, 50) ** 2)
        
        result = pipeline._stage_result_validate(context)
        
        assert result["valid"] is True
        assert result["r_squared"] == 0.95

    def test_result_validate_poor_fit(self):
        """RV-002: 低质量拟合验证"""
        pipeline = CurveFittingPipeline()
        
        from app.services.characteristic_curves.pipeline import PipelineContext
        context = PipelineContext(
            device_id=1001,
            curve_type="qh",
        )
        
        # 设置低质量拟合结果
        context.set_data("r_squared", 0.75)  # 低于0.90阈值
        context.set_data("coefficients", [-0.001, 0.0, 40.0])
        context.set_data("x_values", np.linspace(0, 100, 50))
        context.set_data("y_values", 50 - 0.005 * np.linspace(0, 100, 50) ** 2)
        context.set_data("y_fitted", 40 - 0.001 * np.linspace(0, 100, 50) ** 2)
        
        result = pipeline._stage_result_validate(context)
        
        assert result["valid"] is False  # 应该验证失败


class TestEndToEndFlow:
    """端到端流程测试"""

    def test_fit_complete_flow(self):
        """E2E-001: 完整拟合流程"""
        pipeline = CurveFittingPipeline()
        
        # 准备测试数据
        Q = np.linspace(0, 100, 50)
        H = 50 - 0.005 * Q ** 2
        np.random.seed(42)
        H_noisy = H + np.random.normal(0, 0.5, len(H))
        
        # 执行拟合
        result = pipeline.fit(
            device_id=1001,
            curve_type="qh",
            x_values=Q.tolist(),
            y_values=H_noisy.tolist(),
        )
        
        # 验证结果
        assert isinstance(result, FitResult)
        assert result.success is True
        assert result.r_squared >= 0.90
        assert result.device_id == 1001
        assert result.curve_type == "qh"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
