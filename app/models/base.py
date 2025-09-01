"""
基础数据模型（app.models.base）

本模块定义了数据模型的基础类和通用组件，为整个项目的数据结构提供统一的基础：

核心功能：
- BaseModel：所有业务模型的基础类，基于 Pydantic
- TimestampMixin：时间戳字段混入类  
- ValidationMixin：通用验证逻辑混入类
- 常用数据类型定义和验证器

设计原则：
- 类型安全：完整的类型注解支持
- 数据验证：基于 Pydantic 的自动验证
- 一致性：统一的字段命名和验证规则
- 可扩展性：支持混入类和自定义验证器

使用方式：
    from app.models.base import BaseModel, TimestampMixin
    
    class StationModel(BaseModel, TimestampMixin):
        station_id: str
        name: str
        # 其他字段...

注意事项：
- 所有模型都应继承自 BaseModel
- 时间相关模型应混入 TimestampMixin
- 自定义验证器应遵循 Pydantic 规范
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, Field, field_validator


class BaseModel(PydanticBaseModel):
    """
    所有数据模型的基础类
    
    提供：
    - 基础的 Pydantic 配置
    - 通用的序列化方法
    - 标准的字符串表示
    - 配置验证行为
    """
    
    model_config = ConfigDict(
        # 启用严格模式，提高类型安全性
        strict=False,
        # 允许额外字段，便于未来扩展
        extra='forbid',
        # 在序列化时排除 None 值
        exclude_none=True,
        # 支持任意类型（如 Decimal）
        arbitrary_types_allowed=True,
        # 在赋值时验证
        validate_assignment=True,
        # 使用枚举值而不是名称
        use_enum_values=True,
        # JSON 序列化配置
        json_encoders={
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }
    )
    
    def to_dict(self, exclude_none: bool = True) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Args:
            exclude_none: 是否排除 None 值
            
        Returns:
            字典格式的数据
        """
        return self.model_dump(exclude_none=exclude_none)
    
    def to_json(self, **kwargs) -> str:
        """
        转换为 JSON 字符串
        
        Returns:
            JSON 格式的字符串
        """
        return self.model_dump_json(**kwargs)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BaseModel:
        """
        从字典创建模型实例
        
        Args:
            data: 字典数据
            
        Returns:
            模型实例
        """
        return cls(**data)


class TimestampMixin:
    """
    时间戳字段混入类
    
    为模型添加标准的时间戳字段：
    - created_at: 创建时间
    - updated_at: 更新时间（可选）
    """
    
    created_at: datetime = Field(
        description="创建时间",
        default_factory=datetime.now
    )
    
    updated_at: Optional[datetime] = Field(
        description="更新时间",
        default=None
    )


class ValidationMixin:
    """
    通用验证逻辑混入类
    
    提供常用的验证器和验证方法
    """
    
    @field_validator('*', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        """将空字符串转换为 None"""
        if isinstance(v, str) and v.strip() == '':
            return None
        return v
    
    @field_validator('*', mode='before')
    @classmethod  
    def strip_whitespace(cls, v):
        """去除字符串前后空格"""
        if isinstance(v, str):
            return v.strip()
        return v


# 常用数据类型定义
StationId = str
DeviceId = str
MetricKey = str

# 设备类型枚举
class DeviceType:
    """设备类型常量"""
    PUMP = "pump"
    MAIN_PIPELINE = "main_pipeline"
    
    @classmethod
    def all(cls) -> list[str]:
        """获取所有设备类型"""
        return [cls.PUMP, cls.MAIN_PIPELINE]


class PumpType:
    """泵类型常量"""
    VARIABLE_FREQUENCY = "variable_frequency"  # 变频泵
    SOFT_START = "soft_start"  # 软启动泵
    
    @classmethod
    def all(cls) -> list[str]:
        """获取所有泵类型"""
        return [cls.VARIABLE_FREQUENCY, cls.SOFT_START]


class DeviceStatus:
    """设备状态常量"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    
    @classmethod
    def all(cls) -> list[str]:
        """获取所有设备状态"""
        return [cls.ACTIVE, cls.INACTIVE, cls.MAINTENANCE, cls.ERROR]


class CurveType:
    """特性曲线类型常量"""
    H_Q = "H-Q"  # 扬程-流量曲线
    ETA_Q = "η-Q"  # 效率-流量曲线  
    N_Q = "N-Q"  # 功率-流量曲线
    
    @classmethod
    def all(cls) -> list[str]:
        """获取所有曲线类型"""
        return [cls.H_Q, cls.ETA_Q, cls.N_Q]


class OptimizationStatus:
    """优化状态常量"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    
    @classmethod
    def all(cls) -> list[str]:
        """获取所有优化状态"""
        return [cls.PENDING, cls.RUNNING, cls.COMPLETED, cls.FAILED]


# 常用验证器
def validate_positive_decimal(value: Decimal) -> Decimal:
    """验证正数 Decimal 值"""
    if value <= 0:
        raise ValueError("值必须大于 0")
    return value


def validate_non_negative_decimal(value: Decimal) -> Decimal:
    """验证非负 Decimal 值"""
    if value < 0:
        raise ValueError("值不能为负数")
    return value


def validate_percentage(value: Decimal) -> Decimal:
    """验证百分比值（0-100）"""
    if not (0 <= value <= 100):
        raise ValueError("百分比值必须在 0-100 之间")
    return value