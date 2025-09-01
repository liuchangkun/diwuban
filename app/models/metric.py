"""
度量指标模型（app.models.metric）

提供前端指标选择器所需的基础字段。
"""
from __future__ import annotations
from typing import Optional, Any
from pydantic import BaseModel, Field


class MetricInfo(BaseModel):
    """指标清单模型（来源 dim_metric_config）"""
    id: int = Field(description="指标ID（dim_metric_config.id）")
    metric_key: str = Field(description="指标键（唯一标识）")
    unit: Optional[str] = Field(default=None, description="单位（优先 unit_display 回退 unit）")
    unit_display: Optional[str] = Field(default=None, description="单位展示（可能为空）")
    value_type: Optional[str] = Field(default=None, description="值类型，如 numeric/text")
    fixed_decimals: Optional[int] = Field(default=None, description="固定小数位（可选）")
    valid_min: Optional[float] = Field(default=None, description="有效最小值")
    valid_max: Optional[float] = Field(default=None, description="有效最大值")
    extra: Optional[Any] = Field(default=None, description="保留字段，可扩展")

