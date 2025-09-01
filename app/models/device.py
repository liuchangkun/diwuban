"""
设备数据模型（app.models.device）

本模块定义了设备相关的数据模型，包括：

核心模型：
- Device：设备完整信息模型
- DeviceCreate：创建设备时的数据模型
- DeviceUpdate：更新设备时的数据模型
- DeviceResponse：API 响应时的设备模型

设备类型：
- 水泵（pump）：变频泵、软启动泵
- 总管道（main_pipeline）：系统主管道

数据字段：
- 基础信息：设备ID、名称、类型
- 技术参数：额定功率、流量、扬程
- 运营信息：制造商、安装日期、状态
- 关联信息：所属泵站

使用方式：
    from app.models.device import Device, DeviceCreate
    from app.models.base import DeviceType, PumpType
    
    # 创建水泵设备
    pump_data = DeviceCreate(
        device_id="PUMP001_01",
        station_id="PUMP001",
        name="一号水泵",
        type=DeviceType.PUMP,
        pump_type=PumpType.VARIABLE_FREQUENCY
    )

注意事项：
- device_id 在系统中全局唯一
- pump_type 仅在 type="pump" 时有效
- 额定参数用于性能分析和曲线拟合
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from pydantic import Field, field_validator, model_validator

from app.models.base import (
    BaseModel,
    DeviceId,
    DeviceStatus,
    DeviceType,
    PumpType,
    StationId,
    TimestampMixin,
    ValidationMixin,
)


class Device(BaseModel, TimestampMixin, ValidationMixin):
    """
    设备完整数据模型
    
    包含设备的所有基础信息、技术参数和运营状态。
    对应数据库中的 device 表或 dim_devices 表。
    """
    
    device_id: DeviceId = Field(
        description="设备唯一标识符",
        max_length=50,
        pattern=r'^[A-Za-z0-9_-]+$'
    )
    
    station_id: StationId = Field(
        description="所属泵站ID",
        max_length=50
    )
    
    name: str = Field(
        description="设备名称",
        max_length=100,
        min_length=1
    )
    
    type: str = Field(
        description="设备类型",
        max_length=30
    )
    
    pump_type: Optional[str] = Field(
        description="泵类型（仅当 type='pump' 时有效）",
        default=None,
        max_length=30
    )
    
    model: Optional[str] = Field(
        description="设备型号",
        default=None,
        max_length=50
    )
    
    rated_power: Optional[Decimal] = Field(
        description="额定功率（kW）",
        default=None,
        ge=0,
        decimal_places=2
    )
    
    rated_flow: Optional[Decimal] = Field(
        description="额定流量（m³/h）",
        default=None,
        ge=0,
        decimal_places=2
    )
    
    rated_head: Optional[Decimal] = Field(
        description="额定扬程（m）",
        default=None,
        ge=0,
        decimal_places=2
    )
    
    manufacturer: Optional[str] = Field(
        description="制造商",
        default=None,
        max_length=100
    )
    
    install_date: Optional[date] = Field(
        description="安装日期",
        default=None
    )
    
    status: str = Field(
        description="设备状态",
        default=DeviceStatus.ACTIVE
    )
    
    extra: Optional[Dict[str, Any]] = Field(
        description="额外信息（JSON格式）",
        default=None
    )
    
    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        """验证设备类型"""
        if v not in DeviceType.all():
            raise ValueError(f"无效的设备类型: {v}")
        return v
    
    @field_validator('pump_type')
    @classmethod
    def validate_pump_type(cls, v: Optional[str]) -> Optional[str]:
        """验证泵类型"""
        if v is not None and v not in PumpType.all():
            raise ValueError(f"无效的泵类型: {v}")
        return v
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """验证设备状态"""
        if v not in DeviceStatus.all():
            raise ValueError(f"无效的设备状态: {v}")
        return v
    
    @field_validator('install_date')
    @classmethod
    def validate_install_date(cls, v: Optional[date]) -> Optional[date]:
        """验证安装日期"""
        if v is not None and v > date.today():
            raise ValueError("安装日期不能是未来日期")
        return v
    
    @model_validator(mode='after')
    def validate_pump_type_consistency(self) -> 'Device':
        """验证泵类型与设备类型的一致性"""
        if self.type == DeviceType.PUMP:
            if self.pump_type is None:
                raise ValueError("水泵设备必须指定泵类型")
        else:
            if self.pump_type is not None:
                raise ValueError("非水泵设备不能指定泵类型")
        return self


class DeviceCreate(BaseModel, ValidationMixin):
    """
    创建设备时的数据模型
    
    包含创建设备所需的必要字段，不包含系统生成的字段。
    """
    
    device_id: DeviceId = Field(
        description="设备唯一标识符",
        max_length=50,
        pattern=r'^[A-Za-z0-9_-]+$'
    )
    
    station_id: StationId = Field(
        description="所属泵站ID",
        max_length=50
    )
    
    name: str = Field(
        description="设备名称",
        max_length=100,
        min_length=1
    )
    
    type: str = Field(
        description="设备类型"
    )
    
    pump_type: Optional[str] = Field(
        description="泵类型（仅当 type='pump' 时有效）",
        default=None
    )
    
    model: Optional[str] = Field(
        description="设备型号",
        default=None,
        max_length=50
    )
    
    rated_power: Optional[Decimal] = Field(
        description="额定功率（kW）",
        default=None,
        ge=0,
        decimal_places=2
    )
    
    rated_flow: Optional[Decimal] = Field(
        description="额定流量（m³/h）",
        default=None,
        ge=0,
        decimal_places=2
    )
    
    rated_head: Optional[Decimal] = Field(
        description="额定扬程（m）",
        default=None,
        ge=0,
        decimal_places=2
    )
    
    manufacturer: Optional[str] = Field(
        description="制造商",
        default=None,
        max_length=100
    )
    
    install_date: Optional[date] = Field(
        description="安装日期",
        default=None
    )
    
    status: str = Field(
        description="设备状态",
        default=DeviceStatus.ACTIVE
    )
    
    extra: Optional[Dict[str, Any]] = Field(
        description="额外信息（JSON格式）",
        default=None
    )
    
    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        """验证设备类型"""
        if v not in DeviceType.all():
            raise ValueError(f"无效的设备类型: {v}")
        return v
    
    @field_validator('pump_type')
    @classmethod
    def validate_pump_type(cls, v: Optional[str]) -> Optional[str]:
        """验证泵类型"""
        if v is not None and v not in PumpType.all():
            raise ValueError(f"无效的泵类型: {v}")
        return v
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """验证设备状态"""
        if v not in DeviceStatus.all():
            raise ValueError(f"无效的设备状态: {v}")
        return v
    
    @model_validator(mode='after')
    def validate_pump_type_consistency(self) -> 'DeviceCreate':
        """验证泵类型与设备类型的一致性"""
        if self.type == DeviceType.PUMP:
            if self.pump_type is None:
                raise ValueError("水泵设备必须指定泵类型")
        else:
            if self.pump_type is not None:
                raise ValueError("非水泵设备不能指定泵类型")
        return self


class DeviceUpdate(BaseModel, ValidationMixin):
    """
    更新设备时的数据模型
    
    所有字段都是可选的，只更新提供的字段。
    device_id 和 station_id 不允许修改。
    """
    
    name: Optional[str] = Field(
        description="设备名称",
        default=None,
        max_length=100,
        min_length=1
    )
    
    type: Optional[str] = Field(
        description="设备类型",
        default=None
    )
    
    pump_type: Optional[str] = Field(
        description="泵类型",
        default=None
    )
    
    model: Optional[str] = Field(
        description="设备型号",
        default=None,
        max_length=50
    )
    
    rated_power: Optional[Decimal] = Field(
        description="额定功率（kW）",
        default=None,
        ge=0,
        decimal_places=2
    )
    
    rated_flow: Optional[Decimal] = Field(
        description="额定流量（m³/h）",
        default=None,
        ge=0,
        decimal_places=2
    )
    
    rated_head: Optional[Decimal] = Field(
        description="额定扬程（m）",
        default=None,
        ge=0,
        decimal_places=2
    )
    
    manufacturer: Optional[str] = Field(
        description="制造商",
        default=None,
        max_length=100
    )
    
    install_date: Optional[date] = Field(
        description="安装日期",
        default=None
    )
    
    status: Optional[str] = Field(
        description="设备状态",
        default=None
    )
    
    extra: Optional[Dict[str, Any]] = Field(
        description="额外信息（JSON格式）",
        default=None
    )
    
    @field_validator('type')
    @classmethod
    def validate_type(cls, v: Optional[str]) -> Optional[str]:
        """验证设备类型"""
        if v is not None and v not in DeviceType.all():
            raise ValueError(f"无效的设备类型: {v}")
        return v
    
    @field_validator('pump_type')
    @classmethod
    def validate_pump_type(cls, v: Optional[str]) -> Optional[str]:
        """验证泵类型"""
        if v is not None and v not in PumpType.all():
            raise ValueError(f"无效的泵类型: {v}")
        return v
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """验证设备状态"""
        if v is not None and v not in DeviceStatus.all():
            raise ValueError(f"无效的设备状态: {v}")
        return v


class DeviceResponse(Device):
    """
    API 响应中的设备模型
    
    继承自完整的 Device 模型，可以添加额外的响应字段。
    """
    
    # 可以添加计算字段或关联数据
    station_name: Optional[str] = Field(
        description="所属泵站名称",
        default=None
    )
    
    last_data_time: Optional[datetime] = Field(
        description="最后数据时间",
        default=None
    )
    
    data_count_24h: Optional[int] = Field(
        description="24小时内数据点数",
        default=None
    )


class DeviceSummary(BaseModel):
    """
    设备摘要信息模型
    
    用于列表显示或概览场景，包含关键信息。
    """
    
    device_id: DeviceId = Field(description="设备ID")
    station_id: StationId = Field(description="泵站ID")
    name: str = Field(description="设备名称")
    type: str = Field(description="设备类型")
    pump_type: Optional[str] = Field(description="泵类型", default=None)
    status: str = Field(description="设备状态")
    rated_power: Optional[Decimal] = Field(description="额定功率", default=None)
    last_data_time: Optional[datetime] = Field(description="最后数据时间", default=None)


class PumpPerformanceSpec(BaseModel):
    """
    水泵性能规格模型
    
    用于存储和传输水泵的详细性能参数。
    """
    
    device_id: DeviceId = Field(description="设备ID")
    
    # 额定工况参数
    rated_flow: Decimal = Field(description="额定流量（m³/h）", ge=0)
    rated_head: Decimal = Field(description="额定扬程（m）", ge=0)
    rated_power: Decimal = Field(description="额定功率（kW）", ge=0)
    rated_efficiency: Optional[Decimal] = Field(
        description="额定效率（%）", 
        default=None, 
        ge=0, 
        le=100
    )
    
    # 工作范围
    min_flow: Optional[Decimal] = Field(description="最小流量", default=None, ge=0)
    max_flow: Optional[Decimal] = Field(description="最大流量", default=None, ge=0)
    min_head: Optional[Decimal] = Field(description="最小扬程", default=None, ge=0)
    max_head: Optional[Decimal] = Field(description="最大扬程", default=None, ge=0)
    
    # 变频特性（仅变频泵）
    min_frequency: Optional[Decimal] = Field(
        description="最小频率（Hz）", 
        default=None, 
        ge=0, 
        le=100
    )
    max_frequency: Optional[Decimal] = Field(
        description="最大频率（Hz）", 
        default=None, 
        ge=0, 
        le=100
    )
    
    @model_validator(mode='after')
    def validate_ranges(self) -> 'PumpPerformanceSpec':
        """验证参数范围的合理性"""
        if self.min_flow is not None and self.max_flow is not None:
            if self.min_flow >= self.max_flow:
                raise ValueError("最小流量必须小于最大流量")
        
        if self.min_head is not None and self.max_head is not None:
            if self.min_head >= self.max_head:
                raise ValueError("最小扬程必须小于最大扬程")
        
        if self.min_frequency is not None and self.max_frequency is not None:
            if self.min_frequency >= self.max_frequency:
                raise ValueError("最小频率必须小于最大频率")
        
        return self