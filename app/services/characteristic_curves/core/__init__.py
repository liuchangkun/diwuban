"""
核心数据结构模块

本模块包含特性曲线拟合系统的核心数据类：
- FitResult: 拟合结果
- ValidationResult: 验证结果
- EvaluationReport: 评估报告
- MethodResult: 单个方法的拟合结果
- DeviceInfo: 设备信息
- ScenarioDetectionResult: 场景识别结果
- GroupFitResult: 泵组拟合结果（P2阶段）
- SynthesisResult: 并联合成结果（P2阶段）
- CorrectionModelConfig: 修正模型配置（P2阶段）

推荐导入方式：
    from app.services.characteristic_curves.core import FitResult, ValidationResult
"""

from .data_structures import (
    # 核心数据类
    FitResult,
    ValidationResult,
    EvaluationReport,
    MethodResult,
    DeviceInfo,
    ScenarioDetectionResult,
    # P2阶段
    GroupFitResult,
    SynthesisResult,
    CorrectionModelConfig,
    # 类型定义
    CurveType,
    FitStatus,
    ValidationStatus,
    PumpType,
    # TypedDict配置
    ValidationConfig,
    PerformanceConfig,
    MethodConfigDict,
    DeviceParams,
    FitResultDict,
    # 枚举类
    GroupProcessingStrategy,
    FittingScenario,
    # P0新增数据结构
    Scenario,
    DataQualityReport,
    DataCleaningResult,
    ConstraintResult,
    NormalizationParams,
    SteadyStateResult,
    PipelineContext,
)

__all__ = [
    # 核心数据类
    "FitResult",
    "ValidationResult",
    "EvaluationReport",
    "MethodResult",
    "DeviceInfo",
    "ScenarioDetectionResult",
    # P2阶段
    "GroupFitResult",
    "SynthesisResult",
    "CorrectionModelConfig",
    # 类型定义
    "CurveType",
    "FitStatus",
    "ValidationStatus",
    "PumpType",
    # TypedDict配置
    "ValidationConfig",
    "PerformanceConfig",
    "MethodConfigDict",
    "DeviceParams",
    "FitResultDict",
    # 枚举类
    "GroupProcessingStrategy",
    "FittingScenario",
    # P0新增数据结构
    "Scenario",
    "DataQualityReport",
    "DataCleaningResult",
    "ConstraintResult",
    "NormalizationParams",
    "SteadyStateResult",
    "PipelineContext",
]
