"""
结构化日志扩展：事件埋点 + 采样节流 + 汇总
- ingest.load.begin/progress/end：rows_read/bytes/rows_per_sec/batch_cost_ms（progress 采样）
- align.merge.window：影响行数/去重比/窗口参数
- task.summary：吞吐、慢SQL Top、背压次数

说明：为保持最小可用，本模块只提供轻量实现与注释；后续可接入更完备的 JSON 格式化与异步队列。
"""

from __future__ import annotations

import json
import logging
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# 事件名常量（集中管理，避免魔法字符串散落各处）
EVENT_INGEST_LOAD_BEGIN = "ingest.load.begin"
EVENT_INGEST_LOAD_PROGRESS = "ingest.load.progress"
EVENT_INGEST_LOAD_END = "ingest.load.end"
EVENT_INGEST_COPY_BATCH = "ingest.copy.batch"
EVENT_BACKPRESSURE_ENTER = "backpressure.enter"
EVENT_BACKPRESSURE_EXIT = "backpressure.exit"
EVENT_INGEST_COPY_FAILED = "ingest.copy.failed"
EVENT_INGEST_PATH_RESOLVE = "ingest.path.resolve"
EVENT_INGEST_ERROR_THRESHOLD = "ingest.error.threshold"
EVENT_ALIGN_MERGE_WINDOW = "align.merge.window"
EVENT_TASK_SUMMARY = "task.summary"


def get_event_sampling_rate(settings, event_name: str) -> float:
    """根据 settings.logging.sampling 计算事件的采样率。
    - 优先 high_frequency_events[event_name]，否则使用 default_rate
    - 返回值范围：0.0~1.0（超界会被裁剪）
    """
    try:
        s = settings.logging.sampling
        rate = float((s.high_frequency_events or {}).get(event_name, s.default_rate))
    except Exception:
        rate = 1.0
    if rate < 0.0:
        return 0.0
    if rate > 1.0:
        return 1.0
    return rate


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "logger": record.name,
        }
        if hasattr(record, "event"):
            payload["event"] = getattr(record, "event")
        # 合并 extra 字段
        for k, v in getattr(record, "extra", {}).items():
            payload[k] = v
        # msg 作为补充信息（仅文本模式下有意义）
        if record.getMessage():
            payload["msg"] = record.getMessage()
        return json.dumps(payload, ensure_ascii=False)


class EventLogger:
    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self.logger = logger or logging.getLogger("root")

    def info(self, event: str, **fields: Any) -> None:
        self.logger.info("", extra={"event": event, "extra": fields})

    def error(self, event: str, **fields: Any) -> None:
        self.logger.error("", extra={"event": event, "extra": fields})


class SamplingGate:
    """采样门：按条数或时间节流输出 progress 事件。"""

    def __init__(self, every_n: int = 10000, min_interval_sec: float = 1.0) -> None:
        self.every_n = max(1, every_n)
        self.min_interval = max(0.0, min_interval_sec)
        self._last_emit_ts: float = 0.0

    def allow(self, index: int) -> bool:
        now = time.time()
        if (
            index % self.every_n == 0
            and (now - self._last_emit_ts) >= self.min_interval
        ):
            self._last_emit_ts = now
            return True
        return False


@dataclass
class SqlStat:
    sql: str
    cost_ms: float
    affected_rows: int


@dataclass
class TaskSummaryCollector:
    rows_total: int = 0
    rows_merged: int = 0
    failures: int = 0
    backpressure_count: int = 0
    slow_sql_top: List[SqlStat] = field(default_factory=list)  # 预留
    diagnostics: Dict[str, Any] = field(default_factory=dict)  # 新增：诊断聚合数据
    started_ts: float = field(default_factory=time.time)

    def as_dict(self) -> Dict[str, Any]:
        duration_ms = int((time.time() - self.started_ts) * 1000)
        rows_per_sec = (self.rows_merged / max(1, duration_ms)) * 1000.0
        # 慢 SQL Top 可在外部排序截取 N 条后传入
        slow_top = [
            {"sql": s.sql[:200], "cost_ms": s.cost_ms, "affected_rows": s.affected_rows}
            for s in self.slow_sql_top
        ]
        out = {
            "rows_total": self.rows_total,
            "rows_merged": self.rows_merged,
            "failures": self.failures,
            "backpressure_count": self.backpressure_count,
            "duration_ms": duration_ms,
            "rows_per_sec": rows_per_sec,
            "slow_sql_top": slow_top,
        }
        if self.diagnostics:
            out["diagnostics"] = self.diagnostics
        return out


def setup_basic_json_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # 不要覆盖已有 handlers（兼容 pytest caplog）
    has_json_stdout = False
    for h in root.handlers:
        if isinstance(h, logging.StreamHandler) and isinstance(
            getattr(h, "formatter", None), JsonFormatter
        ):
            has_json_stdout = True
            break
    if not has_json_stdout:
        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)


def log_ingest_begin(
    log: EventLogger, file_path: str, rows_total: Optional[int] = None
) -> None:
    fields: Dict[str, Any] = {"file_path": file_path}
    if rows_total is not None:
        fields["rows_total"] = int(rows_total)
    log.info(EVENT_INGEST_LOAD_BEGIN, **fields)


def log_ingest_progress(
    log: EventLogger,
    gate: SamplingGate,
    rows_read: int,
    bytes_read: int,
    batch_cost_ms: Optional[float] = None,
    started_ts: Optional[float] = None,
) -> None:
    if not gate.allow(rows_read):
        return
    rows_per_sec: Optional[float] = None
    if started_ts:
        elapsed = time.time() - started_ts
        if elapsed > 0:
            rows_per_sec = rows_read / elapsed
    fields: Dict[str, Any] = {
        "rows_read": int(rows_read),
        "bytes": int(bytes_read),
    }
    if rows_per_sec is not None:
        fields["rows_per_sec"] = float(rows_per_sec)
    if batch_cost_ms is not None:
        fields["batch_cost_ms"] = float(batch_cost_ms)
    log.info(EVENT_INGEST_LOAD_PROGRESS, **fields)


def log_ingest_end(
    log: EventLogger, rows_loaded: int, cost_ms: Optional[float] = None
) -> None:
    fields = {"rows_loaded": rows_loaded}
    if cost_ms is not None:
        fields["cost_ms"] = int(cost_ms)
    log.info(EVENT_INGEST_LOAD_END, **fields)


def log_align_merge_window(
    log: EventLogger,
    window_start: str,
    window_end: str,
    rows_in: Optional[int] = None,
    rows_deduped: Optional[int] = None,
    rows_merged: Optional[int] = None,
    dedup_ratio: Optional[float] = None,
    sql_cost_ms: Optional[int] = None,
    affected_rows: Optional[int] = None,
) -> None:
    fields: Dict[str, Any] = {
        "window_start": window_start,
        "window_end": window_end,
    }
    if rows_in is not None:
        fields["rows_in"] = rows_in
    if rows_deduped is not None:
        fields["rows_deduped"] = rows_deduped
    if rows_merged is not None:
        fields["rows_merged"] = rows_merged
    if dedup_ratio is not None:
        fields["dedup_ratio"] = dedup_ratio
    if sql_cost_ms is not None:
        fields["sql_cost_ms"] = sql_cost_ms
    if affected_rows is not None:
        fields["affected_rows"] = affected_rows
    log.info(EVENT_ALIGN_MERGE_WINDOW, **fields)


def log_task_summary(log: EventLogger, summary: TaskSummaryCollector) -> None:
    log.info(EVENT_TASK_SUMMARY, **summary.as_dict())


__all__ = [
    "JsonFormatter",
    "EventLogger",
    "SamplingGate",
    "TaskSummaryCollector",
    "SqlStat",
    "setup_basic_json_logging",
    "log_ingest_begin",
    "log_ingest_progress",
    "log_ingest_end",
    "log_align_merge_window",
    "log_task_summary",
    "EVENT_INGEST_PATH_RESOLVE",
    "EVENT_INGEST_ERROR_THRESHOLD",
    "EVENT_INGEST_COPY_BATCH",
    "EVENT_BACKPRESSURE_ENTER",
    "EVENT_BACKPRESSURE_EXIT",
    "EVENT_INGEST_COPY_FAILED",
    "EVENT_ALIGN_MERGE_WINDOW",
    "EVENT_TASK_SUMMARY",
]
