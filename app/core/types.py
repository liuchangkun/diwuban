from __future__ import annotations

"""
核心类型定义（app.core.types）
- MergeStats/CopyStats：跨层统计的结构化字典类型（与日志/报表字段一致）
- ValidRow/RejectRow：CSV 行的标准表示与拒绝原因结构

注意：
- TypedDict total=False 以便增量补充字段（兼容历史）
- 变更字段需同步更新 docs/数据结构规范.md 与相关日志规范
"""


from dataclasses import dataclass
from typing import TypedDict


class MergeStats(TypedDict, total=False):
    rows_input: int
    rows_deduped: int
    rows_merged: int
    batch_cost_ms: int
    merge_cost_ms: int
    affected_rows: int
    dedup_ratio: float
    sql_cost_ms: int

    rows_per_sec: float


class CopyStats(TypedDict, total=False):
    files_total: int
    files_succeeded: int
    files_failed: int
    rows_read: int
    rows_loaded: int
    rows_rejected: int
    bytes_read: int


@dataclass(frozen=True)
class ValidRow:
    station_name: str
    device_name: str
    metric_key: str
    TagName: str
    DataTime: str
    DataValue: str
    source_hint: str


@dataclass(frozen=True)
class RejectRow:
    source_hint: str
    error_msg: str
