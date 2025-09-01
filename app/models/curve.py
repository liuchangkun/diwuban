"""
特性曲线数据模型（app.models.curve）

本模块定义了水泵特性曲线相关的数据模型，包括：

核心模型：
- Curve：特性曲线完整模型
- CurveCreate：创建曲线数据模型
- CurveUpdate：更新曲线数据模型
- CurveFittingRequest：曲线拟合请求模型

曲线类型：
- H-Q：扬程-流量特性曲线
- η-Q：效率-流量特性曲线
- N-Q：功率-流量特性曲线

数据字段：
- 基础信息：曲线ID、设备信息、曲线类型
- 拟合结果：数学方程、拟合优度、有效期
- 元数据：创建者、数据来源、创建时间

使用方式：
    from app.models.curve import Curve, CurveFittingRequest
    from app.models.base import CurveType

    # 拟合请求
    request = CurveFittingRequest(
        device_id="PUMP001_01",
        curve_type=CurveType.H_Q,
        start_time=datetime.now() - timedelta(days=30),
        end_time=datetime.now()
    )

注意事项：
- 方程系数以 JSON 格式存储
- 拟合优度 R² 值范围 0-1
- 有效期用于版本管理
- 支持多种数学模型
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator, model_validator

from app.models.base import (
    BaseModel,
    CurveType,
    DeviceId,
    StationId,
    TimestampMixin,
    ValidationMixin,
)


class CurveStatus:
    """曲线状态常量"""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    INVALID = "invalid"
    DRAFT = "draft"

    @classmethod
    def all(cls) -> list[str]:
        """获取所有曲线状态"""
        return [cls.ACTIVE, cls.DEPRECATED, cls.INVALID, cls.DRAFT]


class FittingMethod:
    """拟合方法常量"""

    POLYNOMIAL = "polynomial"  # 多项式拟合
    EXPONENTIAL = "exponential"  # 指数拟合
    POWER = "power"  # 幂函数拟合
    LOGARITHMIC = "logarithmic"  # 对数拟合
    CUSTOM = "custom"  # 自定义模型

    @classmethod
    def all(cls) -> list[str]:
        """获取所有拟合方法"""
        return [cls.POLYNOMIAL, cls.EXPONENTIAL, cls.POWER, cls.LOGARITHMIC, cls.CUSTOM]


class Curve(BaseModel, TimestampMixin, ValidationMixin):
    """
    特性曲线完整数据模型

    包含水泵特性曲线的所有信息，包括拟合方程、质量指标和有效期。
    对应数据库中的 curve 表。
    """

    curve_id: Optional[int] = Field(description="曲线ID（自增主键）", default=None)

    station_id: StationId = Field(description="泵站ID", max_length=50)

    device_id: Optional[DeviceId] = Field(
        description="设备ID（泵组时可为空）", default=None, max_length=50
    )

    curve_type: str = Field(description="曲线类型")

    equation: Dict[str, Any] = Field(description="拟合方程（JSON格式的系数和模型信息）")

    r_squared: Decimal = Field(description="拟合优度 R²", ge=0, le=1, decimal_places=4)

    valid_from: datetime = Field(description="有效起始时间")

    valid_to: Optional[datetime] = Field(description="有效结束时间", default=None)

    created_by: str = Field(description="创建者（算法名或用户）", max_length=50)

    source_data_range: Optional[str] = Field(
        description="拟合所用数据的时间范围", default=None, max_length=100
    )

    # 扩展字段
    fitting_method: Optional[str] = Field(description="拟合方法", default=None)

    status: str = Field(description="曲线状态", default=CurveStatus.ACTIVE)

    data_point_count: Optional[int] = Field(
        description="拟合使用的数据点数", default=None, ge=0
    )

    confidence_interval: Optional[Dict[str, Any]] = Field(
        description="置信区间信息", default=None
    )

    @field_validator("curve_type")
    @classmethod
    def validate_curve_type(cls, v: str) -> str:
        """验证曲线类型"""
        if v not in CurveType.all():
            raise ValueError(f"无效的曲线类型: {v}")
        return v

    @field_validator("fitting_method")
    @classmethod
    def validate_fitting_method(cls, v: Optional[str]) -> Optional[str]:
        """验证拟合方法"""
        if v is not None and v not in FittingMethod.all():
            raise ValueError(f"无效的拟合方法: {v}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """验证曲线状态"""
        if v not in CurveStatus.all():
            raise ValueError(f"无效的曲线状态: {v}")
        return v

    @model_validator(mode="after")
    def validate_valid_period(self) -> "Curve":
        """验证有效期的合理性"""
        if self.valid_to is not None and self.valid_to <= self.valid_from:
            raise ValueError("有效结束时间必须大于有效开始时间")
        return self


class CurveCreate(BaseModel, ValidationMixin):
    """
    创建特性曲线时的数据模型

    包含创建曲线所需的必要字段。
    """

    station_id: StationId = Field(description="泵站ID", max_length=50)

    device_id: Optional[DeviceId] = Field(
        description="设备ID", default=None, max_length=50
    )

    curve_type: str = Field(description="曲线类型")

    equation: Dict[str, Any] = Field(description="拟合方程")

    r_squared: Decimal = Field(description="拟合优度", ge=0, le=1, decimal_places=4)

    valid_from: datetime = Field(description="有效起始时间")

    valid_to: Optional[datetime] = Field(description="有效结束时间", default=None)

    created_by: str = Field(description="创建者", max_length=50)

    source_data_range: Optional[str] = Field(
        description="数据时间范围", default=None, max_length=100
    )

    fitting_method: Optional[str] = Field(
        description="拟合方法", default=FittingMethod.POLYNOMIAL
    )

    data_point_count: Optional[int] = Field(description="数据点数", default=None, ge=0)


class CurveUpdate(BaseModel, ValidationMixin):
    """
    更新特性曲线时的数据模型

    所有字段都是可选的，只更新提供的字段。
    """

    equation: Optional[Dict[str, Any]] = Field(description="拟合方程", default=None)

    r_squared: Optional[Decimal] = Field(
        description="拟合优度", default=None, ge=0, le=1, decimal_places=4
    )

    valid_to: Optional[datetime] = Field(description="有效结束时间", default=None)

    status: Optional[str] = Field(description="曲线状态", default=None)


class CurveFittingRequest(BaseModel, ValidationMixin):
    """
    曲线拟合请求模型

    用于定义曲线拟合任务的参数和选项。
    """

    device_id: DeviceId = Field(description="设备ID")

    curve_type: str = Field(description="曲线类型")

    start_time: datetime = Field(description="数据开始时间")

    end_time: datetime = Field(description="数据结束时间")

    # 拟合选项
    fitting_method: str = Field(
        description="拟合方法", default=FittingMethod.POLYNOMIAL
    )

    polynomial_degree: Optional[int] = Field(
        description="多项式次数（多项式拟合时使用）", default=2, ge=1, le=6
    )

    min_data_points: int = Field(description="最小数据点数", default=50, ge=10)

    min_r_squared: Decimal = Field(
        description="最小拟合优度要求", default=Decimal("0.8"), ge=0, le=1
    )

    # 数据过滤选项
    remove_outliers: bool = Field(description="是否移除异常值", default=True)

    outlier_threshold: Optional[Decimal] = Field(
        description="异常值阈值（标准差倍数）", default=Decimal("3.0"), ge=1, le=5
    )

    operating_range_only: bool = Field(
        description="是否仅使用正常运行工况数据", default=True
    )

    @field_validator("curve_type")
    @classmethod
    def validate_curve_type(cls, v: str) -> str:
        """验证曲线类型"""
        if v not in CurveType.all():
            raise ValueError(f"无效的曲线类型: {v}")
        return v

    @field_validator("fitting_method")
    @classmethod
    def validate_fitting_method(cls, v: str) -> str:
        """验证拟合方法"""
        if v not in FittingMethod.all():
            raise ValueError(f"无效的拟合方法: {v}")
        return v

    @model_validator(mode="after")
    def validate_time_range(self) -> "CurveFittingRequest":
        """验证时间范围"""
        if self.end_time <= self.start_time:
            raise ValueError("结束时间必须大于开始时间")
        return self


class CurveFittingResult(BaseModel):
    """
    曲线拟合结果模型

    包含拟合过程的详细结果和质量评估。
    """

    success: bool = Field(description="拟合是否成功")

    curve: Optional[Curve] = Field(description="拟合得到的曲线", default=None)

    # 拟合质量指标
    r_squared: Optional[Decimal] = Field(description="拟合优度 R²", default=None)

    rmse: Optional[Decimal] = Field(description="均方根误差", default=None)

    mae: Optional[Decimal] = Field(description="平均绝对误差", default=None)

    # 数据统计
    total_points: int = Field(description="原始数据点数", ge=0)
    used_points: int = Field(description="实际使用数据点数", ge=0)
    outliers_removed: int = Field(description="移除的异常值数量", ge=0)

    # 错误信息
    error_message: Optional[str] = Field(description="错误信息（失败时）", default=None)

    warnings: List[str] = Field(description="警告信息列表", default_factory=list)

    # 元数据
    fitting_duration_ms: Optional[float] = Field(
        description="拟合耗时（毫秒）", default=None
    )

    algorithm_version: Optional[str] = Field(description="算法版本", default=None)


class CurveEvaluationRequest(BaseModel, ValidationMixin):
    """
    曲线评估请求模型

    用于评估现有曲线的准确性和有效性。
    """

    curve_id: int = Field(description="曲线ID")

    evaluation_start: datetime = Field(description="评估数据开始时间")

    evaluation_end: datetime = Field(description="评估数据结束时间")

    metrics: List[str] = Field(
        description="评估指标列表", default=["r_squared", "rmse", "mae", "mape"]
    )


class CurveEvaluationResult(BaseModel):
    """
    曲线评估结果模型

    包含曲线在新数据上的表现评估。
    """

    curve_id: int = Field(description="曲线ID")

    evaluation_metrics: Dict[str, Decimal] = Field(description="评估指标结果")

    data_points_evaluated: int = Field(description="评估数据点数", ge=0)

    is_still_valid: bool = Field(description="曲线是否仍然有效")

    recommendations: List[str] = Field(description="改进建议", default_factory=list)


class CurveResponse(Curve):
    """
    API 响应中的曲线模型

    继承自完整的 Curve 模型，可以添加额外的响应字段。
    """

    # 关联信息
    device_name: Optional[str] = Field(description="设备名称", default=None)

    station_name: Optional[str] = Field(description="泵站名称", default=None)

    # 使用统计
    usage_count: Optional[int] = Field(description="使用次数", default=None)

    last_used: Optional[datetime] = Field(description="最后使用时间", default=None)
