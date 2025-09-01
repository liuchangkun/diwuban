# models package (可选，只读 ORM 映射)
"""
泵站数据优化系统数据模型包 (app.models)

本包包含系统中所有的数据模型定义，基于 Pydantic 提供类型安全的数据验证和序列化。

模块结构：
- base: 基础模型类和通用组件
- station: 泵站相关模型
- device: 设备相关模型
- operation_data: 运行数据和测量数据模型
- curve: 特性曲线相关模型
- optimization: 优化结果相关模型

使用方式：
    from app.models import Station, Device, OperationData
    from app.models.base import DeviceType, CurveType
    
    # 创建设备模型实例
    device = Device(
        device_id="PUMP001_01",
        station_id="PUMP001",
        name="一号水泵",
        type=DeviceType.PUMP
    )

设计原则：
- 类型安全：完整的类型注解和验证
- 数据一致性：统一的字段命名和验证规则
- 可扩展性：支持新增字段和模型
- 向后兼容：保持 API 稳定性
"""

from __future__ import annotations

# 基础组件
from app.models.base import (
    BaseModel,
    TimestampMixin,
    ValidationMixin,
    # 类型定义
    StationId,
    DeviceId,
    MetricKey,
    # 枚举常量
    DeviceType,
    PumpType,
    DeviceStatus,
    CurveType,
    OptimizationStatus,
    # 验证器
    validate_positive_decimal,
    validate_non_negative_decimal,
    validate_percentage,
)

# 泵站模型
from app.models.station import (
    Station,
    StationCreate,
    StationUpdate,
    StationResponse,
    StationSummary,
    StationStatus,
)

# 设备模型
from app.models.device import (
    Device,
    DeviceCreate,
    DeviceUpdate,
    DeviceResponse,
    DeviceSummary,
    PumpPerformanceSpec,
)

# 运行数据模型
from app.models.operation_data import (
    OperationData,
    MeasurementData,
    DataPoint,
    PumpOperationPoint,
    TimeSeriesQuery,
    TimeSeriesResponse,
    AggregatedData,
    DataExportRequest,
    DataQuality,
)

# 特性曲线模型
from app.models.curve import (
    Curve,
    CurveCreate,
    CurveUpdate,
    CurveResponse,
    CurveFittingRequest,
    CurveFittingResult,
    CurveEvaluationRequest,
    CurveEvaluationResult,
    CurveStatus,
    FittingMethod,
)

# 优化模型
from app.models.optimization import (
    Optimization,
    OptimizationCreate,
    OptimizationRequest,
    OptimizationResult,
    OptimizationResponse,
    OptimizationComparison,
    OptimizationSchedule,
    OptimizationTarget,
    OptimizationAlgorithm,
)

__all__ = [
    # 基础组件
    "BaseModel",
    "TimestampMixin",
    "ValidationMixin",
    # 类型定义
    "StationId",
    "DeviceId",
    "MetricKey",
    # 枚举常量
    "DeviceType",
    "PumpType",
    "DeviceStatus",
    "CurveType",
    "OptimizationStatus",
    # 验证器
    "validate_positive_decimal",
    "validate_non_negative_decimal",
    "validate_percentage",
    # 泵站模型
    "Station",
    "StationCreate",
    "StationUpdate",
    "StationResponse",
    "StationSummary",
    "StationStatus",
    # 设备模型
    "Device",
    "DeviceCreate",
    "DeviceUpdate",
    "DeviceResponse",
    "DeviceSummary",
    "PumpPerformanceSpec",
    # 运行数据模型
    "OperationData",
    "MeasurementData",
    "DataPoint",
    "PumpOperationPoint",
    "TimeSeriesQuery",
    "TimeSeriesResponse",
    "AggregatedData",
    "DataExportRequest",
    "DataQuality",
    # 特性曲线模型
    "Curve",
    "CurveCreate",
    "CurveUpdate",
    "CurveResponse",
    "CurveFittingRequest",
    "CurveFittingResult",
    "CurveEvaluationRequest",
    "CurveEvaluationResult",
    "CurveStatus",
    "FittingMethod",
    # 优化模型
    "Optimization",
    "OptimizationCreate",
    "OptimizationRequest",
    "OptimizationResult",
    "OptimizationResponse",
    "OptimizationComparison",
    "OptimizationSchedule",
    "OptimizationTarget",
    "OptimizationAlgorithm",
]
