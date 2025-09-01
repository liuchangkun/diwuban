"""
泵站数据模型（app.models.station）

本模块定义了泵站相关的数据模型，包括：

核心模型：
- Station：泵站基础信息模型
- StationCreate：创建泵站时的数据模型
- StationUpdate：更新泵站时的数据模型
- StationResponse：API 响应时的泵站模型

数据字段：
- 基础信息：站点ID、名称、位置
- 运营信息：容量、投运日期、管理员
- 状态信息：运行状态、创建和更新时间
- 扩展信息：额外的 JSON 数据

使用方式：
    from app.models.station import Station, StationCreate

    # 创建泵站数据
    station_data = StationCreate(
        station_id="PUMP001",
        name="一号泵站",
        location="上海市浦东新区"
    )

    # 转换为完整模型
    station = Station(**station_data.model_dump())

注意事项：
- station_id 是全局唯一标识符
- 所有枚举值应使用预定义常量
- 创建和更新时间自动管理
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from pydantic import Field, field_validator

from app.models.base import BaseModel, StationId, TimestampMixin, ValidationMixin


class StationStatus:
    """泵站状态常量"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    DECOMMISSIONED = "decommissioned"

    @classmethod
    def all(cls) -> list[str]:
        """获取所有泵站状态"""
        return [cls.ACTIVE, cls.INACTIVE, cls.MAINTENANCE, cls.DECOMMISSIONED]


class Station(BaseModel, TimestampMixin, ValidationMixin):
    """
    泵站完整数据模型

    包含泵站的所有基础信息、运营状态和元数据。
    对应数据库中的 station 表或 dim_stations 表。
    """

    station_id: StationId = Field(
        description="泵站唯一标识符", max_length=50, pattern=r"^[A-Za-z0-9_-]+$"
    )

    name: str = Field(description="泵站名称", max_length=100, min_length=1)

    location: Optional[str] = Field(
        description="泵站地理位置", default=None, max_length=200
    )

    region: Optional[str] = Field(description="所属区域", default=None, max_length=50)

    capacity: Optional[Decimal] = Field(
        description="设计容量（m³/h）", default=None, ge=0, decimal_places=2
    )

    commission_date: Optional[date] = Field(description="投运日期", default=None)

    manager: Optional[str] = Field(description="负责人", default=None, max_length=50)

    status: str = Field(description="泵站状态", default=StationStatus.ACTIVE)

    extra: Optional[Dict[str, Any]] = Field(
        description="额外信息（JSON格式）", default=None
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """验证泵站状态值"""
        if v not in StationStatus.all():
            raise ValueError(f"无效的泵站状态: {v}")
        return v

    @field_validator("capacity")
    @classmethod
    def validate_capacity(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """验证容量值"""
        if v is not None and v <= 0:
            raise ValueError("泵站容量必须大于 0")
        return v

    @field_validator("commission_date")
    @classmethod
    def validate_commission_date(cls, v: Optional[date]) -> Optional[date]:
        """验证投运日期"""
        if v is not None and v > date.today():
            raise ValueError("投运日期不能是未来日期")
        return v


class StationCreate(BaseModel, ValidationMixin):
    """
    创建泵站时的数据模型

    包含创建泵站所需的必要字段，不包含系统生成的字段如时间戳等。
    """

    station_id: StationId = Field(
        description="泵站唯一标识符", max_length=50, pattern=r"^[A-Za-z0-9_-]+$"
    )

    name: str = Field(description="泵站名称", max_length=100, min_length=1)

    location: Optional[str] = Field(
        description="泵站地理位置", default=None, max_length=200
    )

    region: Optional[str] = Field(description="所属区域", default=None, max_length=50)

    capacity: Optional[Decimal] = Field(
        description="设计容量（m³/h）", default=None, ge=0, decimal_places=2
    )

    commission_date: Optional[date] = Field(description="投运日期", default=None)

    manager: Optional[str] = Field(description="负责人", default=None, max_length=50)

    status: str = Field(description="泵站状态", default=StationStatus.ACTIVE)

    extra: Optional[Dict[str, Any]] = Field(
        description="额外信息（JSON格式）", default=None
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """验证泵站状态值"""
        if v not in StationStatus.all():
            raise ValueError(f"无效的泵站状态: {v}")
        return v


class StationUpdate(BaseModel, ValidationMixin):
    """
    更新泵站时的数据模型

    所有字段都是可选的，只更新提供的字段。
    station_id 不允许修改。
    """

    name: Optional[str] = Field(
        description="泵站名称", default=None, max_length=100, min_length=1
    )

    location: Optional[str] = Field(
        description="泵站地理位置", default=None, max_length=200
    )

    region: Optional[str] = Field(description="所属区域", default=None, max_length=50)

    capacity: Optional[Decimal] = Field(
        description="设计容量（m³/h）", default=None, ge=0, decimal_places=2
    )

    commission_date: Optional[date] = Field(description="投运日期", default=None)

    manager: Optional[str] = Field(description="负责人", default=None, max_length=50)

    status: Optional[str] = Field(description="泵站状态", default=None)

    extra: Optional[Dict[str, Any]] = Field(
        description="额外信息（JSON格式）", default=None
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """验证泵站状态值"""
        if v is not None and v not in StationStatus.all():
            raise ValueError(f"无效的泵站状态: {v}")
        return v


class StationResponse(Station):
    """
    API 响应中的泵站模型

    继承自完整的 Station 模型，可以添加额外的响应字段。
    """

    # 可以添加计算字段或关联数据
    device_count: Optional[int] = Field(description="设备数量", default=None)

    last_data_time: Optional[datetime] = Field(description="最后数据时间", default=None)


class StationSummary(BaseModel):
    """
    泵站摘要信息模型

    用于列表显示或概览场景，包含关键信息。
    """

    station_id: StationId = Field(description="泵站ID")
    name: str = Field(description="泵站名称")
    region: Optional[str] = Field(description="所属区域", default=None)
    status: str = Field(description="泵站状态")
    device_count: Optional[int] = Field(description="设备数量", default=None)
    capacity: Optional[Decimal] = Field(description="设计容量", default=None)
    last_data_time: Optional[datetime] = Field(description="最后数据时间", default=None)
