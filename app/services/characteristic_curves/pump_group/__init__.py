"""
泵组处理层模块 (app.services.characteristic_curves.pump_group)

版本: v2.0
创建日期: 2025-12-09
更新日期: 2025-12-09
来源: 07_泵组处理层.md + 泵组直接拟合功能

本模块提供P2阶段泵组处理相关类：
- PumpGroupProcessor: 泵组处理器（任务73）
- ParallelSynthesizer: 并联合成器（任务74）
- SystemCorrectionModel: 系统修正模型（任务75）
- FrequencyDataProvider: 频率数据提供器（任务76）
- PumpGroupValidator: 泵组验证器（任务77）
- PumpGroupResultStorage: 泵组结果存储（任务78）
- ScenarioHandler: 场景处理器（任务79）
- P2Pipeline: P2管道（任务80）

新增（v2.0 - 泵组直接拟合）：
- GroupDataExtractor: 泵组数据提取器
- GroupCurveFitter: 泵组曲线拟合器
- GroupCurveComparator: 泵组曲线对比器
- DualMethodExecutor: 双方法执行器
- GroupCurvePlotter: 泵组曲线绘图器
- 数据模型: GroupFitData, GroupOperatingPoint, DirectFitResult, ComparisonResult, CurveFitMethod
"""

from app.services.characteristic_curves.pump_group.pump_group_processor import (
    PumpGroupProcessor,
)
from app.services.characteristic_curves.pump_group.parallel_synthesizer import (
    ParallelSynthesizer,
    WeightedSynthesisResult,
)
from app.services.characteristic_curves.pump_group.system_correction_model import (
    SystemCorrectionModel,
    CorrectionModelConfig,
    prepare_features_mixed_heterogeneous,
)
from app.services.characteristic_curves.pump_group.frequency_data_provider import (
    FrequencyDataProvider,
)
from app.services.characteristic_curves.pump_group.pump_group_validator import (
    PumpGroupValidator,
    ValidationResult,
)
from app.services.characteristic_curves.pump_group.pump_group_result_storage import (
    PumpGroupResultStorage,
    GroupFitResult,
)
from app.services.characteristic_curves.pump_group.scenario_handler import (
    ScenarioHandler,
    Scenario,
    ScenarioContext,
)
from app.services.characteristic_curves.pump_group.p2_pipeline import (
    P2Pipeline,
    P2PipelineResult,
)
from app.services.characteristic_curves.pump_group.models import (
    GroupFitData,
    GroupOperatingPoint,
    DirectFitResult,
    ComparisonResult,
    CurveFitMethod,
)
from app.services.characteristic_curves.pump_group.group_data_extractor import (
    GroupDataExtractor,
)
from app.services.characteristic_curves.pump_group.group_curve_fitter import (
    GroupCurveFitter,
)
from app.services.characteristic_curves.pump_group.group_curve_comparator import (
    GroupCurveComparator,
)
from app.services.characteristic_curves.pump_group.dual_method_executor import (
    DualMethodExecutor,
)
from app.services.characteristic_curves.pump_group.group_curve_plotter import (
    GroupCurvePlotter,
)

__all__ = [
    # 任务73: PumpGroupProcessor
    "PumpGroupProcessor",
    # 任务74: ParallelSynthesizer
    "ParallelSynthesizer",
    "WeightedSynthesisResult",
    # 任务75: SystemCorrectionModel
    "SystemCorrectionModel",
    "CorrectionModelConfig",
    "prepare_features_mixed_heterogeneous",
    # 任务76: FrequencyDataProvider
    "FrequencyDataProvider",
    # 任务77: PumpGroupValidator
    "PumpGroupValidator",
    "ValidationResult",
    # 任务78: PumpGroupResultStorage
    "PumpGroupResultStorage",
    "GroupFitResult",
    # 任务79: ScenarioHandler
    "ScenarioHandler",
    "Scenario",
    "ScenarioContext",
    # 任务80: P2Pipeline
    "P2Pipeline",
    "P2PipelineResult",
    # v2.0: 泵组直接拟合
    "GroupFitData",
    "GroupOperatingPoint",
    "DirectFitResult",
    "ComparisonResult",
    "CurveFitMethod",
    "GroupDataExtractor",
    "GroupCurveFitter",
    "GroupCurveComparator",
    "DualMethodExecutor",
    "GroupCurvePlotter",
]

