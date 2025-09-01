from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TimeSeriesResponse(BaseModel):
    """统一的时间序列响应模型
    - data: 列表，元素为字典（前端按扁平结构使用）
    - metadata: 可选的元信息（station_id/device_id、时间窗、粒度等）
    - total_count: 记录总数（或估算值）
    - query_time_ms: 查询耗时（毫秒）
    - has_more: 是否还有更多数据（结合 limit/offset）
    """

    data: List[Dict[str, Any]] = Field(default_factory=list, description="数据列表")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据")
    total_count: int = Field(default=0, ge=0, description="总数")
    query_time_ms: float = Field(default=0.0, ge=0.0, description="查询耗时（毫秒）")
    has_more: bool = Field(default=False, description="是否还有更多")
