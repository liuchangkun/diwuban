"""
运行数据模型（app.models.operation_data）

本模块定义了运行时序数据相关的模型，包括：

核心模型：
- OperationData：运行数据完整模型
- MeasurementData：测量数据模型（新表结构）
- DataPoint：单个数据点模型
- TimeSeriesQuery：时序查询参数模型

数据字段：
- 时间信息：原始时间戳、对齐时间戳
- 设备标识：泵站ID、设备ID、指标ID
- 测量数值：流量、压力、功率、频率等
- 元数据：数据源、插入时间

使用方式：
    from app.models.operation_data import OperationData, TimeSeriesQuery
    from datetime import datetime, timedelta
    
    # 查询参数
    query = TimeSeriesQuery(
        station_id="PUMP001",
        device_id="PUMP001_01",
        start_time=datetime.now() - timedelta(hours=24),
        end_time=datetime.now()
    )
    
    # 数据点
    data_point = DataPoint(
        timestamp=datetime.now(),
        flow_rate=Decimal("120.5"),
        pressure=Decimal("0.45"),
        power=Decimal("15.2")
    )

注意事项：
- 时间戳统一使用 UTC 时区
- 数值类型使用 Decimal 保证精度
- 支持新旧数据表结构
- 分区表查询需要包含时间范围
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from app.models.base import BaseModel, DeviceId, MetricKey, StationId, ValidationMixin


class DataQuality:
    """数据质量标识常量"""
    GOOD = "good"
    SUSPECT = "suspect"
    BAD = "bad"
    MISSING = "missing"
    
    @classmethod
    def all(cls) -> list[str]:
        """获取所有数据质量标识"""
        return [cls.GOOD, cls.SUSPECT, cls.BAD, cls.MISSING]


class OperationData(BaseModel, ValidationMixin):
    """
    运行数据完整模型（兼容旧表结构）
    
    对应数据库中的 operation_data 表，包含设备运行的时序数据。
    主要用于兼容现有系统和历史数据查询。
    """
    
    id: Optional[int] = Field(
        description="数据记录ID",
        default=None
    )
    
    station_id: StationId = Field(
        description="泵站ID",
        max_length=50
    )
    
    device_id: DeviceId = Field(
        description="设备ID",
        max_length=50
    )
    
    timestamp: datetime = Field(
        description="数据时间戳"
    )
    
    # 主要运行参数
    flow_rate: Optional[Decimal] = Field(
        description="流量（m³/h）",
        default=None,
        ge=0,
        decimal_places=3
    )
    
    pressure: Optional[Decimal] = Field(
        description="压力（MPa）",
        default=None,
        ge=0,
        decimal_places=3
    )
    
    power: Optional[Decimal] = Field(
        description="功率（kW）",
        default=None,
        ge=0,
        decimal_places=3
    )
    
    frequency: Optional[Decimal] = Field(
        description="频率（Hz）",
        default=None,
        ge=0,
        le=100,
        decimal_places=2
    )
    
    # 状态和质量信息
    status: Optional[int] = Field(
        description="运行状态代码",
        default=None,
        ge=0
    )
    
    data_source: Optional[str] = Field(
        description="数据源标识",
        default=None,
        max_length=20
    )
    
    created_at: Optional[datetime] = Field(
        description="创建时间",
        default=None
    )


class MeasurementData(BaseModel, ValidationMixin):
    """
    测量数据模型（新表结构）
    
    对应数据库中的 fact_measurements 表，采用新的维度建模结构。
    支持更灵活的指标配置和更好的查询性能。
    """
    
    id: Optional[int] = Field(
        description="行ID（非主键）",
        default=None
    )
    
    station_id: int = Field(
        description="泵站维度ID",
        gt=0
    )
    
    device_id: int = Field(
        description="设备维度ID",
        gt=0
    )
    
    metric_id: int = Field(
        description="指标维度ID",
        gt=0
    )
    
    ts_raw: datetime = Field(
        description="原始时间戳"
    )
    
    ts_bucket: datetime = Field(
        description="对齐时间戳（秒级）"
    )
    
    value: Decimal = Field(
        description="测量数值",
        decimal_places=6
    )
    
    source_hint: Optional[str] = Field(
        description="来源标识",
        default=None
    )
    
    inserted_at: Optional[datetime] = Field(
        description="插入时间",
        default=None
    )


class DataPoint(BaseModel, ValidationMixin):
    """
    单个数据点模型
    
    用于API传输和内存处理的轻量级数据点结构。
    """
    
    timestamp: datetime = Field(description="时间戳")
    metric_key: MetricKey = Field(description="指标键")
    value: Decimal = Field(description="数值", decimal_places=6)
    quality: str = Field(description="数据质量", default=DataQuality.GOOD)
    
    @field_validator('quality')
    @classmethod
    def validate_quality(cls, v: str) -> str:
        """验证数据质量标识"""
        if v not in DataQuality.all():
            raise ValueError(f"无效的数据质量标识: {v}")
        return v


class PumpOperationPoint(BaseModel):
    """
    水泵运行工况点模型
    
    表示水泵在某个时刻的完整运行状态，用于性能分析和优化计算。
    """
    
    timestamp: datetime = Field(description="时间戳")
    device_id: DeviceId = Field(description="设备ID")
    
    # 核心运行参数
    flow_rate: Decimal = Field(description="流量（m³/h）", ge=0)
    head: Optional[Decimal] = Field(description="扬程（m）", default=None, ge=0)
    power: Decimal = Field(description="功率（kW）", ge=0)
    frequency: Optional[Decimal] = Field(description="频率（Hz）", default=None, ge=0, le=100)
    
    # 计算参数
    efficiency: Optional[Decimal] = Field(
        description="效率（%）", 
        default=None, 
        ge=0, 
        le=100
    )
    
    specific_energy: Optional[Decimal] = Field(
        description="比能耗（kWh/m³）",
        default=None,
        ge=0
    )
    
    # 状态信息
    is_valid: bool = Field(description="数据有效性", default=True)
    quality_score: Optional[Decimal] = Field(
        description="质量评分（0-100）",
        default=None,
        ge=0,
        le=100
    )


class TimeSeriesQuery(BaseModel, ValidationMixin):
    """
    时序数据查询参数模型
    
    用于定义时序数据查询的条件和参数。
    """
    
    station_id: Optional[StationId] = Field(
        description="泵站ID",
        default=None
    )
    
    device_id: Optional[DeviceId] = Field(
        description="设备ID",
        default=None
    )
    
    device_ids: Optional[List[DeviceId]] = Field(
        description="设备ID列表",
        default=None
    )
    
    metric_keys: Optional[List[MetricKey]] = Field(
        description="指标键列表",
        default=None
    )
    
    start_time: datetime = Field(description="开始时间")
    end_time: datetime = Field(description="结束时间")
    
    # 查询选项
    limit: Optional[int] = Field(
        description="结果数量限制",
        default=None,
        gt=0,
        le=10000
    )
    
    offset: Optional[int] = Field(
        description="结果偏移量",
        default=None,
        ge=0
    )
    
    aggregate_interval: Optional[str] = Field(
        description="聚合时间间隔（如 '1h', '5m'）",
        default=None
    )
    
    aggregate_functions: Optional[List[str]] = Field(
        description="聚合函数列表（如 ['avg', 'max', 'min']）",
        default=None
    )
    
    include_quality: bool = Field(
        description="是否包含数据质量信息",
        default=False
    )
    
    @field_validator('end_time')
    @classmethod
    def validate_time_range(cls, v: datetime, info) -> datetime:
        """验证时间范围的合理性"""
        if 'start_time' in info.data:
            start_time = info.data['start_time']
            if v <= start_time:
                raise ValueError("结束时间必须大于开始时间")
            
            # 限制查询时间跨度（最大一年）
            if (v - start_time).days > 365:
                raise ValueError("查询时间跨度不能超过一年")
        
        return v


class TimeSeriesResponse(BaseModel):
    """
    时序数据查询响应模型
    
    包含查询结果和元数据信息。
    """
    
    data: List[Dict[str, Any]] = Field(description="数据列表")
    
    metadata: Dict[str, Any] = Field(
        description="元数据",
        default_factory=dict
    )
    
    total_count: Optional[int] = Field(
        description="总记录数",
        default=None
    )
    
    query_time_ms: Optional[float] = Field(
        description="查询耗时（毫秒）",
        default=None
    )
    
    has_more: bool = Field(
        description="是否有更多数据",
        default=False
    )


class AggregatedData(BaseModel):
    """
    聚合数据模型
    
    表示按时间间隔聚合后的数据。
    """
    
    timestamp: datetime = Field(description="时间戳（区间起点）")
    device_id: DeviceId = Field(description="设备ID")
    metric_key: MetricKey = Field(description="指标键")
    
    # 统计值
    avg_value: Optional[Decimal] = Field(description="平均值", default=None)
    min_value: Optional[Decimal] = Field(description="最小值", default=None)
    max_value: Optional[Decimal] = Field(description="最大值", default=None)
    sum_value: Optional[Decimal] = Field(description="累计值", default=None)
    count: int = Field(description="数据点数", ge=0)
    
    # 质量信息
    valid_count: Optional[int] = Field(description="有效数据点数", default=None)
    quality_score: Optional[Decimal] = Field(description="质量评分", default=None)


class DataExportRequest(BaseModel, ValidationMixin):
    """
    数据导出请求模型
    
    用于定义数据导出的参数和格式。
    """
    
    query: TimeSeriesQuery = Field(description="查询参数")
    
    format: str = Field(
        description="导出格式",
        default="csv"
    )
    
    include_headers: bool = Field(
        description="是否包含表头",
        default=True
    )
    
    timezone: Optional[str] = Field(
        description="时区（如系统默认时区）",
        default=None
    )
    
    filename: Optional[str] = Field(
        description="文件名",
        default=None
    )
    
    @field_validator('format')
    @classmethod
    def validate_format(cls, v: str) -> str:
        """验证导出格式"""
        allowed_formats = ['csv', 'excel', 'json']
        if v not in allowed_formats:
            raise ValueError(f"不支持的导出格式: {v}")
        return v