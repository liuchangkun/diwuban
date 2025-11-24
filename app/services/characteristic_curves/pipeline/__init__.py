"""
管道模块 (app.services.characteristic_curves.pipeline)

本模块提供特性曲线拟合的主管道和依赖注入容器。

版本: v1.0
更新日期: 2025-12-09
"""

from app.services.characteristic_curves.pipeline.pipeline_context import (
    PipelineContext,
    StageResult,
    PipelineStage,
)
from app.services.characteristic_curves.pipeline.curve_fitting_pipeline import (
    CurveFittingPipeline,
)
from app.services.characteristic_curves.pipeline.dependency_container import (
    DependencyContainer,
    get_container,
)

__all__ = [
    "PipelineContext",
    "StageResult",
    "PipelineStage",
    "CurveFittingPipeline",
    "DependencyContainer",
    "get_container",
]

