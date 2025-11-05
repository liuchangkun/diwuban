# -*- coding: utf-8 -*-
"""
可配置、可扩展的异步日志系统（MVP）
- 基于标准 logging（不使用装饰器）
- 异步写入：QueueHandler + QueueListener
- 多目标输出：控制台、文件（支持按时间/大小轮换），可选并发安全（concurrent-log-handler）
- 可选依赖：psutil/colorlog/concurrent-log-handler/watchfiles/orjson（缺失自动降级）
- 热加载：watchfiles 可选
- 上下文：contextvars 注入（request_id/trace_id/user_id/tenant 等）
- 输出格式：管道分隔固定字段 + extra_json（严格 JSON，可解析）
- 提供 log_activity 上下文管理器与辅助事件 API（sql/biz）
"""
from __future__ import annotations

import contextvars
import json
import logging
import logging.handlers
import os
import queue
import sys
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# 可选依赖探测
try:
    import orjson as _json_fast  # type: ignore
except Exception:  # pragma: no cover
    _json_fast = None

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None  # type: ignore

try:
    from watchfiles import awatch  # type: ignore
except Exception:  # pragma: no cover
    awatch = None  # type: ignore

try:
    from concurrent_log_handler import ConcurrentRotatingFileHandler  # type: ignore
except Exception:  # pragma: no cover
    ConcurrentRotatingFileHandler = None  # type: ignore

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

# 上下文字段（必要时可扩展）
_ctx: dict[str, contextvars.ContextVar[Optional[str]]] = {
    "request_id": contextvars.ContextVar("request_id", default=None),
    "trace_id": contextvars.ContextVar("trace_id", default=None),
    "span_id": contextvars.ContextVar("span_id", default=None),
    "parent_span_id": contextvars.ContextVar("parent_span_id", default=None),
    "span_depth": contextvars.ContextVar("span_depth", default=None),
    "timeline_id": contextvars.ContextVar("timeline_id", default=None),
    "timeline_seq": contextvars.ContextVar("timeline_seq", default=None),
    "user_id": contextvars.ContextVar("user_id", default=None),
    "tenant": contextvars.ContextVar("tenant", default=None),
}


def set_context(**kwargs: str | None) -> None:
    for k, v in kwargs.items():
        if k in _ctx:
            _ctx[k].set(v)


def clear_context() -> None:
    for var in _ctx.values():
        try:
            var.set(None)
        except Exception:
            pass


def _get_context_snapshot() -> dict[str, Any]:
    return {k: v.get() for k, v in _ctx.items() if v.get() is not None}


# 配置对象（与 YAML 对齐，保留简单默认）
@dataclass
class LoggingDeps:
    psutil: str = "auto"  # auto|force|off
    colorlog: str = "auto"
    concurrent_log_handler: str = "auto"
    orjson: str = "auto"


@dataclass
class AsyncConfig:
    enabled: bool = True
    # 增大默认队列容量以避免批量场景 queue.Full（可被 YAML 覆盖）
    queue_size: int = 100000
    batch_size: int = 200  # 预留（本实现按逐条监听写出）
    flush_interval_ms: int = 100
    backpressure: str = "drop_debug"  # block|drop_debug|drop_oldest
    force_sync_levels: list[str] | None = None


@dataclass
class HotReload:
    enabled: bool = False
    backend: str = "watchfiles"  # none|watchfiles


@dataclass
class RotateConfig:
    type: str = "time"  # time|size
    when: str = "midnight"
    interval: int = 1
    backup_count: int = 14
    compress: bool = False
    max_bytes: int = 10485760


@dataclass
class OutputConfig:
    name: str = "console"
    type: str = "console"  # console|file
    enabled: bool = True
    level: str = "INFO"
    color: bool = False
    colors: dict[str, str] | None = None  # 级别到颜色名/ANSI 的映射，如 {INFO: green}
    sampling: float = 1.0
    path: Optional[str] = None
    rotate: RotateConfig = field(default_factory=RotateConfig)
    route: dict[str, Any] | None = None


@dataclass
class LoggingConfig:
    timezone: str = ""
    time_format: str = ""
    level: str = ""
    format: str = ""  # pipe|json|keyvalue
    localize: bool = True
    async_cfg: AsyncConfig = field(default_factory=AsyncConfig)
    hot_reload: HotReload = field(default_factory=HotReload)
    outputs: list[OutputConfig] | None = None
    fields_include: list[str] | None = None
    localize_map: dict[str, str] | None = None
    deps: LoggingDeps = field(default_factory=LoggingDeps)
    palette: dict[str, str] | None = None
    # 采集策略
    capture_params: bool = True
    capture_return: bool = True
    max_field_length: int = 2000
    mask_keys: list[str] = field(
        default_factory=lambda: ["password", "token", "id_card"]
    )
    # SQL 慢日志阈值（毫秒，0 表示关闭）
    sql_slow_ms: int = 0
    # SQL EXPLAIN 配置
    sql_explain_on_slow: bool = True
    sql_explain_timeout_ms: int = 200
    sql_explain_max_length: int = 2000
    # Activity 配置
    activity_step_slow_ms: int = 0
    activity_capture_result_summary: bool = False
    activity_summary_max_length: int = 1000
    # Jobs 配置
    jobs_retry_enabled: bool = True
    jobs_retry_include_policy: bool = True
    jobs_retry_threshold_ms: int = 50
    # 依赖调用/缓存/事务配置
    http_out_enabled: bool = False
    http_out_mask_headers: list[str] = field(default_factory=list)
    cache_enabled: bool = False
    cache_slow_ms: int = 0
    tx_enabled: bool = False
    # 数据库连接池日志配置
    db_pool_enabled: bool = False
    db_pool_acquire_slow_ms: int = 0
    db_pool_create_slow_ms: int = 0
    db_pool_health_check_slow_ms: int = 0
    db_pool_include_thread: bool = False
    db_pool_include_stack: bool = False

    @staticmethod
    def from_yaml(path: Path, system_tz: str = "Asia/Shanghai") -> "LoggingConfig":
        cfg = LoggingConfig()
        try:
            if yaml and path.exists():
                with path.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                root = data.get("logging", data)
                cfg.timezone = root.get("timezone", cfg.timezone)
                cfg.time_format = root.get("time_format", cfg.time_format)
                cfg.level = root.get("level", cfg.level)
                cfg.format = root.get("format", cfg.format)
                cfg.localize = bool(root.get("localize", cfg.localize))
                cap = root.get("capture", {})
                cfg.capture_params = bool(cap.get("params", cfg.capture_params))
                cfg.capture_return = bool(cap.get("return", cfg.capture_return))
                cfg.max_field_length = int(
                    cap.get("max_field_length", cfg.max_field_length)
                )
                cfg.mask_keys = cap.get("mask_keys", cfg.mask_keys)
                cfg.sql_slow_ms = int(root.get("sql_slow_ms", cfg.sql_slow_ms))
                sqlx = root.get("sql", {})
                cfg.sql_explain_on_slow = bool(sqlx.get("explain_on_slow", True))
                cfg.sql_explain_timeout_ms = int(sqlx.get("explain_timeout_ms", 200))
                cfg.sql_explain_max_length = int(sqlx.get("explain_max_length", 2000))
                ac = root.get("async", {})
                cfg.async_cfg = AsyncConfig(
                    enabled=ac.get("enabled", cfg.async_cfg.enabled),
                    queue_size=int(ac.get("queue_size", cfg.async_cfg.queue_size)),
                    batch_size=int(ac.get("batch_size", cfg.async_cfg.batch_size)),
                    flush_interval_ms=int(
                        ac.get("flush_interval_ms", cfg.async_cfg.flush_interval_ms)
                    ),
                    backpressure=ac.get("backpressure", cfg.async_cfg.backpressure),
                    force_sync_levels=ac.get(
                        "force_sync_levels", cfg.async_cfg.force_sync_levels
                    ),
                )
                act = root.get("activity", {})
                cfg.activity_step_slow_ms = int(act.get("step_slow_ms", 0))
                cfg.activity_capture_result_summary = bool(
                    act.get("capture_result_summary", False)
                )
                cfg.activity_summary_max_length = int(
                    act.get("summary_max_length", 1000)
                )
                hr = root.get("hot_reload", {})
                cfg.hot_reload = HotReload(
                    enabled=hr.get("enabled", False),
                    backend=hr.get("backend", "watchfiles"),
                )
                # palette
                cfg.palette = root.get("palette")
                # outputs（必须提供）
                outs = root.get("outputs", [])
                cfg.outputs = []
                for o in outs:
                    rot = o.get("rotate", {})
                    oc = OutputConfig(
                        name=o.get("name", "console"),
                        type=o.get("type", "console"),
                        enabled=o.get("enabled", True),
                        level=o.get("level", "INFO"),
                        color=o.get("color", False),
                        colors=o.get("colors"),
                        sampling=float(o.get("sampling", 1.0)),
                        path=o.get("path"),
                        rotate=RotateConfig(
                            type=rot.get("type", "time"),
                            when=rot.get("when", "midnight"),
                            interval=int(rot.get("interval", 1)),
                            backup_count=int(rot.get("backup_count", 14)),
                            compress=bool(rot.get("compress", False)),
                            max_bytes=int(rot.get("max_bytes", 10 * 1024 * 1024)),
                        ),
                        route=o.get("route"),
                    )
                    cfg.outputs.append(oc)
                # fields（必须提供 include）
                inc = root.get("fields", {}).get("include")
                if not inc:
                    raise ValueError("logging.fields.include 必须配置且非空")
                cfg.fields_include = inc
                # 可配置的中文键映射（移除代码硬编码）
                locmap = root.get("fields", {}).get("localize_map")
                cfg.localize_map = locmap if isinstance(locmap, dict) else None
                # deps
                d = root.get("deps", {})
                cfg.deps = LoggingDeps(
                    psutil=d.get("psutil", "auto"),
                    colorlog=d.get("colorlog", "auto"),
                    concurrent_log_handler=d.get("concurrent_log_handler", "auto"),
                    orjson=d.get("orjson", "auto"),
                )
                # jobs/deps/cache/tx
                jobs = root.get("jobs", {})
                rlog = jobs.get("retry_log", {})
                cfg.jobs_retry_enabled = bool(rlog.get("enabled", True))
                cfg.jobs_retry_include_policy = bool(rlog.get("include_policy", True))
                cfg.jobs_retry_threshold_ms = int(rlog.get("threshold_ms", 50))
                http_out = root.get("dependencies", {}).get("http_out", {})
                cfg.http_out_enabled = bool(http_out.get("enabled", False))
                cfg.http_out_mask_headers = http_out.get("mask_headers", [])
                cache = root.get("cache", {})
                cfg.cache_enabled = bool(cache.get("enabled", False))
                cfg.cache_slow_ms = int(cache.get("slow_ms", 0))
                tx = root.get("database", {}).get("tx", {})
                cfg.tx_enabled = bool(tx.get("enabled", False))
                # db pool logging
                dbp = root.get("database", {}).get("pool_log", {})
                cfg.db_pool_enabled = bool(dbp.get("enabled", False))
                cfg.db_pool_acquire_slow_ms = int(dbp.get("acquire_slow_ms", 0))
                cfg.db_pool_create_slow_ms = int(dbp.get("create_slow_ms", 0))
                cfg.db_pool_health_check_slow_ms = int(
                    dbp.get("health_check_slow_ms", 0)
                )
                cfg.db_pool_include_thread = bool(dbp.get("include_thread", False))
                cfg.db_pool_include_stack = bool(dbp.get("include_stack", False))
        except Exception:
            # 读取失败时使用默认
            pass
        return cfg


def _json_dumps(obj: Any) -> str:
    if _json_fast is not None:
        try:
            return _json_fast.dumps(obj, option=_json_fast.OPT_NON_STR_KEYS).decode(
                "utf-8"
            )
        except Exception:
            pass
    return json.dumps(obj, ensure_ascii=False, default=str)


def _summarize(value: Any, max_len: int = 1000) -> dict[str, Any]:
    """轻量结果摘要：类型、长度、预览、数值统计等。"""
    try:
        t = type(value).__name__
        summary: dict[str, Any] = {"type": t}
        # 字符串
        if isinstance(value, str):
            s = value
            if len(s) > max_len:
                s = s[: max_len - 3] + "..."
            summary.update({"len": len(value), "preview": s})
            return summary
        # 字节
        if isinstance(value, (bytes, bytearray)):
            summary.update({"len": len(value)})
            return summary
        # 映射
        if isinstance(value, dict):
            keys = list(value.keys())
            summary.update({"len": len(value), "keys_sample": keys[:10]})
            return summary
        # 序列
        if isinstance(value, (list, tuple, set)):
            seq = list(value)
            summary.update({"len": len(seq)})
            # 数值统计（小样本，避免开销）
            nums = [x for x in seq[:1000] if isinstance(x, (int, float))]
            if nums:
                n = len(nums)
                mean = sum(nums) / n
                summary.update(
                    {
                        "numeric_count": n,
                        "min": min(nums),
                        "max": max(nums),
                        "mean": round(mean, 6),
                    }
                )
            # 预览
            preview = seq[:5]
            try:
                s = _json_dumps(preview)
            except Exception:
                s = str(preview)
            if len(s) > max_len:
                s = s[: max_len - 3] + "..."
            summary["preview"] = s
            return summary
        # 其他对象
        s = str(value)
        if len(s) > max_len:
            s = s[: max_len - 3] + "..."
        summary["preview"] = s
        return summary
    except Exception:
        return {"type": type(value).__name__, "preview": "<summary_error>"}


def _tzinfo_from_name(name: str):
    if ZoneInfo is not None:
        try:
            return ZoneInfo(name)
        except Exception:
            pass
    # 退回本地时区或 UTC
    try:
        return timezone.utc if name.upper() in ("UTC", "Z") else ZoneInfo("UTC")  # type: ignore
    except Exception:
        return timezone.utc


class PipeFormatter(logging.Formatter):
    def __init__(
        self,
        time_format: str,
        tz_name: str,
        fields: list[str],
        localize: bool = True,
        colorize: bool = False,
        localize_map: Optional[dict[str, str]] = None,
    ):
        super().__init__()
        self.time_format = time_format
        self.tz = _tzinfo_from_name(tz_name)
        self.fields = fields
        self.localize = localize
        self.colorize = colorize
        self.level_colors: dict[str, str] | None = None
        self.localize_map = localize_map or {}

    def format(self, record: logging.LogRecord) -> str:
        # 时间戳（按时区）
        ts = datetime.fromtimestamp(record.created, tz=self.tz).strftime(
            self.time_format
        )
        filename = (
            os.path.basename(record.pathname)
            if getattr(record, "pathname", None)
            else record.filename
        )
        base = {
            "timestamp": ts,
            "pid": record.process,
            "processName": record.processName,
            "threadId": record.thread,
            "threadName": record.threadName,
            "filename": filename,
            "module": record.module,
            "funcName": record.funcName,
            "lineno": record.lineno,
            "level": record.levelname,
            "message": record.getMessage(),
        }
        # 合并 extra：事件字段 + 上下文（由生产者线程注入）
        extra: dict[str, Any] = {}
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            extra.update(record.extra_data)
        if hasattr(record, "context_data") and isinstance(record.context_data, dict):
            extra.update(record.context_data)

        # 统一规范化 extra 中的 datetime 为配置的时间格式（含微秒与时区）
        def _normalize_dt(obj: Any) -> Any:
            try:
                from datetime import date, time as _time
                if isinstance(obj, datetime):
                    try:
                        dt = obj.astimezone(self.tz) if getattr(obj, 'tzinfo', None) else obj.replace(tzinfo=self.tz)
                    except Exception:
                        dt = obj
                    return dt.strftime(self.time_format)
                if isinstance(obj, _time):
                    # 仅时间，按字符串输出
                    return obj.strftime("%H:%M:%S.%f")
                if isinstance(obj, date):
                    return obj.strftime("%Y-%m-%d")
                if isinstance(obj, dict):
                    return {k: _normalize_dt(v) for k, v in obj.items()}
                if isinstance(obj, (list, tuple)):
                    return [_normalize_dt(v) for v in obj]
                return obj
            except Exception:
                return obj
        extra = _normalize_dt(extra)

        # 中文键映射，完全由配置驱动（受 localize 开关控制）
        def _cn_map(k: str) -> str:
            try:
                return self.localize_map.get(k, k)
            except Exception:
                return k

        def _map_val(v: Any) -> Any:
            if isinstance(v, dict):
                if set(v.keys()) & {"rss", "cpu", "fds"}:
                    im = {"rss": "内存RSS字节", "cpu": "CPU%", "fds": "文件描述符变更"}
                    return {im.get(ik, ik): _map_val(iv) for ik, iv in v.items()}
                return _cn_map if self.localize else (lambda x: x)  # type: ignore
            if isinstance(v, (list, tuple)):
                return [_map_val(i) for i in v]
            return v

        def _maybe_localize(d: dict[str, Any]) -> dict[str, Any]:
            if not self.localize:
                return d

            def _deep_map(obj: Any) -> Any:
                if isinstance(obj, dict):
                    return {_cn_map(k): _deep_map(v) for k, v in obj.items()}
                if isinstance(obj, (list, tuple)):
                    return [_deep_map(i) for i in obj]
                return obj

            return _deep_map(d)  # type: ignore

        # 控制台彩色：按级别为 level 与 message 着色（仅 console handler 会启用）
        if self.colorize:
            try:
                # 仅使用配置映射（不做代码默认回退），可选 palette 支持颜色名→ANSI 映射
                cmap = self.level_colors or {}
                reset = "\x1b[0m"
                col = cmap.get(record.levelname, "")
                if col:
                    ansi = str(col)
                    if hasattr(logging, "_augment_palette"):
                        pal = getattr(logging, "_augment_palette") or {}
                        if isinstance(col, str):
                            ansi = pal.get(col.lower(), col)
                    if ansi:
                        base["level"] = f"{ansi}{base['level']}{reset}"
                        base["message"] = f"{ansi}{base['message']}{reset}"
            except Exception:
                pass

        extra_loc = _maybe_localize(extra) if extra else {}
        # 允许在 fields.include 中使用“中文键名”（如：线程名），此处做一次反向映射
        loc_rev: dict[str, str] = {}
        try:
            loc_rev = {v: k for k, v in (self.localize_map or {}).items()}
        except Exception:
            loc_rev = {}
        line_parts: list[str] = []
        for f in self.fields:
            if f == "extra_json":
                line_parts.append(_json_dumps(extra_loc) if extra_loc else "{}")
            else:
                val = base.get(f, None)
                if val is None and self.localize and f in loc_rev:
                    val = base.get(loc_rev.get(f, ""), "")
                if val is None:
                    val = ""
                line_parts.append(str(val))
        return "|".join(line_parts)


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # 在生产者线程注入上下文，避免 QueueListener 线程丢失 contextvars
        try:
            record.context_data = _get_context_snapshot()
        except Exception:
            record.context_data = {}
        return True


def _build_handler(out: OutputConfig, cfg: LoggingConfig) -> logging.Handler:
    level = getattr(logging, out.level.upper(), logging.INFO)
    if not cfg.fields_include:
        raise ValueError("logging.fields.include 必须配置且非空")
    fmt = PipeFormatter(
        cfg.time_format,
        cfg.timezone,
        cfg.fields_include,
        localize=cfg.localize,
        colorize=(out.type == "console" and bool(out.color)),
        localize_map=(cfg.localize_map or {}),
    )
    # 从输出配置注入颜色映射（不使用硬编码回退）
    if out.type == "console" and out.colors:
        fmt.level_colors = out.colors
    # 设置全局 palette 供颜色名解析（若配置提供）
    if cfg.palette is not None:
        setattr(logging, "_augment_palette", cfg.palette)
    filt = ContextFilter()

    handler: logging.Handler
    if out.type == "console":
        handler = logging.StreamHandler(stream=sys.stdout)
    else:
        assert out.path, "file output requires path"
        log_path = Path(out.path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        use_shared = False
        if (
            cfg.deps.concurrent_log_handler != "off"
            and ConcurrentRotatingFileHandler is not None
        ):
            # 仅当配置 route 允许共享且 rotate 按大小时使用并发文件
            if out.rotate.type == "size":
                handler = ConcurrentRotatingFileHandler(
                    filename=str(log_path),
                    maxBytes=int(out.rotate.max_bytes),
                    backupCount=int(out.rotate.backup_count),
                    encoding="utf-8",
                )
                use_shared = True
            else:
                use_shared = False
        if out.rotate.type == "time" and not use_shared:
            handler = logging.handlers.TimedRotatingFileHandler(
                filename=str(log_path),
                when=out.rotate.when,
                interval=int(out.rotate.interval),
                backupCount=int(out.rotate.backup_count),
                encoding="utf-8",
                utc=False,
            )
        elif out.rotate.type == "size" and not use_shared:
            handler = logging.handlers.RotatingFileHandler(
                filename=str(log_path),
                maxBytes=int(out.rotate.max_bytes),
                backupCount=int(out.rotate.backup_count),
                encoding="utf-8",
            )
        # 可选压缩留作扩展（定制 Rotator/Namer）

    handler.setLevel(level)
    handler.setFormatter(fmt)
    handler.addFilter(filt)
    return handler


class DroppingQueueHandler(logging.handlers.QueueHandler):
    """自定义队列处理器：在队列满时按策略退避，避免抛出 queue.Full。
    策略：
      - block: 阻塞 put（不丢日志）
      - drop_debug: 丢弃 DEBUG/INFO 级别日志；WARNING 及以上改为同步 fallback
      - drop_oldest: 丢弃队列中最旧的一条，再写入当前记录
    """
    def __init__(self, q: queue.Queue, policy: str = "drop_debug"):
        super().__init__(q)
        self.policy = (policy or "drop_debug").lower()

    def enqueue(self, record: logging.LogRecord) -> None:
        # SimpleQueue 无 put_nowait，用 put 即可（无界）
        if not hasattr(self.queue, "put_nowait"):
            try:
                self.queue.put(record)
            except Exception:
                pass
            return
        try:
            self.queue.put_nowait(record)
        except queue.Full:
            if self.policy == "block":
                try:
                    self.queue.put(record, block=True)
                except Exception:
                    pass
            elif self.policy == "drop_oldest":
                try:
                    # 丢最旧
                    if hasattr(self.queue, "get_nowait"):
                        self.queue.get_nowait()
                    self.queue.put_nowait(record)
                except Exception:
                    pass
            else:  # drop_debug（默认）
                if record.levelno < logging.WARNING:
                    # 丢弃低级别日志
                    return
                # 关键日志同步写 stderr 作为兜底，避免静默丢失
                try:
                    sys.stderr.write(f"[LOG-DROP-FALLBACK] {record.levelname}: {record.getMessage()}\n")
                except Exception:
                    pass


class AsyncLoggingManager:
    def __init__(self, cfg: LoggingConfig):
        self.cfg = cfg
        # 支持无界队列以避免 queue.Full（通过环境变量控制），否则使用可配置容量
        _unbounded = str(os.getenv("AUGMENT_LOG_UNBOUNDED_QUEUE", "")).lower() in ("1", "true", "yes")
        if _unbounded:
            try:
                self.q = queue.SimpleQueue()  # type: ignore[attr-defined]
            except Exception:
                self.q = queue.Queue(maxsize=0)  # 退化为无界
        else:
            self.q = queue.Queue(maxsize=int(cfg.async_cfg.queue_size))
        # 使用可退避的队列处理器，避免 queue.Full 异常
        self.queue_handler = DroppingQueueHandler(self.q, policy=(cfg.async_cfg.backpressure or "drop_debug"))
        self.listener: Optional[logging.handlers.QueueListener] = None
        self._stop_event = threading.Event()

    def start(self, handlers: list[logging.Handler]) -> None:
        self.listener = logging.handlers.QueueListener(
            self.q, *handlers, respect_handler_level=True
        )
        self.listener.start()

    def stop(self) -> None:
        try:
            if self.listener:
                self.listener.stop()
        except Exception:
            pass


_global_async_mgr: Optional[AsyncLoggingManager] = None
_global_watch_thread: Optional[threading.Thread] = None
_global_watch_stop: Optional[threading.Event] = None
_global_cfg: Optional[LoggingConfig] = None


def _start_hot_reload_if_needed(
    cfg: LoggingConfig, log_yaml: Path, system_tz: str
) -> None:
    global _global_watch_thread, _global_watch_stop
    if not cfg.hot_reload.enabled:
        return
    # 若已有旧线程，先停止
    try:
        if _global_watch_stop is not None:
            _global_watch_stop.set()
        if _global_watch_thread is not None and _global_watch_thread.is_alive():
            _global_watch_thread.join(timeout=0.5)
    except Exception:
        pass
    _global_watch_stop = threading.Event()

    def _watcher(path: Path, stop_evt: threading.Event, tz: str):
        last_mtime = path.stat().st_mtime if path.exists() else 0.0
        while not stop_evt.is_set():
            try:
                cur = path.stat().st_mtime if path.exists() else 0.0
                if cur != last_mtime:
                    last_mtime = cur
                    logging.getLogger(__name__).info(
                        "检测到 logging.yaml 变更，重新加载..."
                    )
                    # 递归重建配置（避免重复创建监听器线程）
                    init_logging(str(path.parent), tz)
                stop_evt.wait(1.0)
            except Exception:
                stop_evt.wait(2.0)

    _global_watch_thread = threading.Thread(
        target=_watcher,
        args=(log_yaml, _global_watch_stop, system_tz),
        name="logging-config-watcher",
        daemon=True,
    )
    _global_watch_thread.start()


def init_logging(
    config_dir: Path | str = "configs", system_tz: str = "Asia/Shanghai"
) -> None:
    """初始化日志系统。重复调用将重置全局 logging 配置。"""
    global _global_async_mgr

    # 修复 Windows 终端中文乱码：强制 stdout/stderr 使用 UTF-8
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    config_dir = Path(config_dir)
    log_yaml = config_dir / "logging.yaml"
    cfg = LoggingConfig.from_yaml(log_yaml, system_tz)
    # 缓存全局配置，供 call_with_activity / log_sql 等读取
    global _global_cfg
    _global_cfg = cfg

    # 根 logger 基础级别
    root_level = getattr(logging, cfg.level.upper(), logging.INFO)
    logging.root.handlers.clear()
    logging.root.setLevel(root_level)

    # 按输出创建 handlers
    handlers: list[logging.Handler] = []
    for out in cfg.outputs:
        if not out.enabled:
            continue
        h = _build_handler(out, cfg)
        # 路由：若配置了 only_loggers，则仅绑定到这些 logger，避免污染 root
        only = (out.route or {}).get("only_loggers") if out.route else None
        if only and isinstance(only, (list, tuple)):
            for ln in only:
                lg = logging.getLogger(str(ln))
                lg.addHandler(h)
                lg.setLevel(getattr(logging, out.level.upper(), logging.INFO))
                # 防止向 root 传播，避免重复写入其他文件
                try:
                    lg.propagate = False
                except Exception:
                    pass
        else:
            handlers.append(h)

    # 绑定 handlers（异步/同步两种模式）
    if cfg.async_cfg.enabled:
        _global_async_mgr = AsyncLoggingManager(cfg)
        _global_async_mgr.start(handlers)
        logging.root.addHandler(_global_async_mgr.queue_handler)
        # 进程退出时确保 flush 队列，避免丢日志
        try:
            import atexit as _atexit

            _atexit.register(lambda: (_global_async_mgr and _global_async_mgr.stop()))
        except Exception:
            pass
    else:
        for h in handlers:
            logging.root.addHandler(h)

    # 独立 logger 级别/路由（示例：sql → SQL 文件）
    logging.getLogger("sql").setLevel(getattr(logging, "INFO"))

    # 安装未捕获异常钩子
    _install_exception_hooks()

    # 热加载监视
    _start_hot_reload_if_needed(cfg, log_yaml, cfg.timezone)

    # 首行启动日志
    logging.getLogger(__name__).info(
        "日志系统初始化完成",
        extra={"extra_data": {"timezone": cfg.timezone, "format": cfg.format}},
    )


def _install_exception_hooks() -> None:
    import sys as _sys
    import threading as _th

    def excepthook(exc_type, exc, tb):
        logging.getLogger("stderr").error("未捕获异常", exc_info=(exc_type, exc, tb))

    def thread_excepthook(args):  # type: ignore[no-redef]
        logging.getLogger("stderr").error(
            "线程未捕获异常",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    _sys.excepthook = excepthook
    if hasattr(_th, "excepthook"):
        _th.excepthook = thread_excepthook  # type: ignore[attr-defined]


# ActivitySpan 定义（供调用方在 with log_activity 中使用 span.step/return）
class ActivitySpan:
    def __init__(self, name: str, params: Optional[dict[str, Any]] = None):
        self.name = name
        self.params = params or {}
        self.steps: list[dict[str, Any]] = []
        self.return_value: Any = None
        # 序列与层级信息
        self.seq = None
        self.step_index = 0
        self.depth = None
        self.span_id = None
        self.parent_span_id = None

    def step(self, message: str, **fields: Any) -> None:
        # 自增步骤序号
        self.step_index += 1
        logging.getLogger("activity").info(
            "[步骤] %s: %s",
            self.name,
            message,
            extra={
                "extra_data": {
                    "类型": "步骤",
                    "event": "step",
                    "step_index": self.step_index,
                    "depth": self.depth,
                    **fields,
                }
            },
        )
        self.steps.append({"message": message, **fields})

    def set_return(self, value: Any) -> None:
        self.return_value = value


@contextmanager
def log_activity(name: str, params: Optional[dict[str, Any]] = None):
    """记录进入/退出/耗时/异常；不使用装饰器。"""
    logger = logging.getLogger("activity")
    start = datetime.now()
    res_before = None
    if psutil is not None:
        try:
            p = psutil.Process()
            res_before = {
                "rss": p.memory_info().rss,
                "cpu": p.cpu_percent(interval=None),
                "fds": p.num_fds() if hasattr(p, "num_fds") else None,
            }
        except Exception:
            res_before = None
    # 生成 span_id / parent_span_id / depth
    try:
        parent = _ctx["span_id"].get()
        depth = _ctx["span_depth"].get()
        if depth is None:
            depth_n = 0
        else:
            try:
                depth_n = int(depth)
            except Exception:
                depth_n = 0
        cur_span = uuid.uuid4().hex[:16]
        _ctx["parent_span_id"].set(parent)
        _ctx["span_id"].set(cur_span)
        _ctx["span_depth"].set(str(depth_n + 1))
    except Exception:
        cur_span = None
        parent = None
        depth_n = None

    logger.info(
        "[进入] %s",
        name,
        extra={
            "extra_data": {
                "类型": "进入",
                "event": "enter",
                "params": params or {},
                **(
                    {"span_id": cur_span, "parent_span_id": parent, "depth": depth_n}
                    if cur_span
                    else {}
                ),
            }
        },
    )
    try:
        yield
        dur_ms = int((datetime.now() - start).total_seconds() * 1000)
        res_after = None
        if psutil is not None:
            try:
                p = psutil.Process()
                res_after = {
                    "rss": p.memory_info().rss,
                    "cpu": p.cpu_percent(interval=None),
                    "fds": p.num_fds() if hasattr(p, "num_fds") else None,
                }
            except Exception:
                res_after = None
        delta = None
        if res_before and res_after:
            delta = {
                "rss": res_after["rss"] - res_before["rss"],
                "cpu": res_after["cpu"],
                "fds": (
                    (res_after["fds"] - res_before["fds"])
                    if res_before.get("fds") is not None
                    and res_after.get("fds") is not None
                    else None
                ),
            }
        # 退出日志：慢标记 + 链路携带
        slow_flag = False
        try:
            if _global_cfg and _global_cfg.activity_step_slow_ms > 0:
                slow_flag = dur_ms >= _global_cfg.activity_step_slow_ms
        except Exception:
            pass
        logger.info(
            "[退出] %s",
            name,
            extra={
                "extra_data": {
                    "类型": "退出",
                    "event": "exit",
                    "duration_ms": dur_ms,
                    "resource_delta": delta,
                    **({"slow": True} if slow_flag else {}),
                }
            },
        )
    except Exception:
        dur_ms = int((datetime.now() - start).total_seconds() * 1000)
        logger.error(
            "[错误] %s",
            name,
            extra={
                "extra_data": {"类型": "错误", "event": "fail", "duration_ms": dur_ms}
            },
            exc_info=True,
        )
        raise


def _mask_and_truncate(obj: Any, mask_keys: list[str], max_len: int) -> Any:
    def _mask_value(v: Any) -> Any:
        if isinstance(v, str):
            if len(v) > max_len:
                return v[: max_len - 3] + "..."
            return v
        return v

    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if isinstance(k, str) and k.lower() in {m.lower() for m in mask_keys}:
                out[k] = "***"
            else:
                out[k] = _mask_and_truncate(v, mask_keys, max_len)
        return out
    if isinstance(obj, (list, tuple)):
        return [_mask_and_truncate(v, mask_keys, max_len) for v in obj]
    return _mask_value(obj)


def call_with_activity(name: str, func, *args, **kwargs):
    # 初始化或推进 timeline 序列
    try:
        cur_seq = _ctx["timeline_seq"].get()
        if cur_seq is None:
            _ctx["timeline_id"].set(_ctx["timeline_id"].get() or str(uuid.uuid4()))
            _ctx["timeline_seq"].set("0")
        else:
            try:
                _ctx["timeline_seq"].set(str(int(cur_seq) + 1))
            except Exception:
                _ctx["timeline_seq"].set(cur_seq)
    except Exception:
        pass
    """方案A：自动采集参数与返回值（不使用装饰器）。

    - 进入：记录 参数（脱敏/截断）
    - 返回：记录 返回值（脱敏/截断）
    - 退出：记录 耗时/资源变化
    - 异常：记录 错误 类型与堆栈
    """
    logger = logging.getLogger("activity")
    # 从当前配置推断策略（简化：从 YAML 已装载的默认值）
    # 这里直接使用 LoggingConfig 的默认策略；如需严格使用运行时 cfg，可在 init 时缓存。
    # 默认从全局配置读取
    global _global_cfg
    capture_params = _global_cfg.capture_params if _global_cfg else True
    capture_return = _global_cfg.capture_return if _global_cfg else True
    mask_keys = (
        _global_cfg.mask_keys if _global_cfg else ["password", "token", "id_card"]
    )
    max_len = _global_cfg.max_field_length if _global_cfg else 2000

    safe_args = (
        _mask_and_truncate(list(args), mask_keys, max_len) if capture_params else []
    )
    safe_kwargs = (
        _mask_and_truncate(dict(kwargs), mask_keys, max_len) if capture_params else {}
    )

    start = datetime.now()
    res_before = None
    if psutil is not None:
        try:
            p = psutil.Process()
            res_before = {
                "rss": p.memory_info().rss,
                "cpu": p.cpu_percent(interval=None),
                "fds": p.num_fds() if hasattr(p, "num_fds") else None,
            }
        except Exception:
            res_before = None

    # 进入
    logger.info(
        "[进入] %s",
        name,
        extra={
            "extra_data": {
                "类型": "进入",
                "event": "enter",
                "params": {"args": safe_args, "kwargs": safe_kwargs},
            }
        },
    )

    try:
        result = func(*args, **kwargs)
        # 返回
        if capture_return:
            rv = _mask_and_truncate(result, mask_keys, max_len)
            if _global_cfg and _global_cfg.activity_capture_result_summary:
                rv_summary = _summarize(result, _global_cfg.activity_summary_max_length)
                extra_rv = {"return": rv_summary}
            else:
                extra_rv = {"return": rv}
            logger.info(
                "[返回] %s",
                name,
                extra={
                    "extra_data": {
                        "类型": "返回",
                        **extra_rv,
                    }
                },
            )
        return result
    except Exception:
        dur_ms = int((datetime.now() - start).total_seconds() * 1000)
        logger.error(
            "[错误] %s",
            name,
            extra={
                "extra_data": {"类型": "错误", "event": "fail", "duration_ms": dur_ms}
            },
            exc_info=True,
        )
        raise
    finally:
        dur_ms = int((datetime.now() - start).total_seconds() * 1000)
        res_after = None
        if psutil is not None:
            try:
                p = psutil.Process()
                res_after = {
                    "rss": p.memory_info().rss,
                    "cpu": p.cpu_percent(interval=None),
                    "fds": p.num_fds() if hasattr(p, "num_fds") else None,
                }
            except Exception:
                res_after = None
        delta = None
        if res_before and res_after:
            delta = {
                "rss": res_after["rss"] - res_before["rss"],
                "cpu": res_after["cpu"],
                "fds": (
                    (res_after["fds"] - res_before["fds"])
                    if res_before.get("fds") is not None
                    and res_after.get("fds") is not None
                    else None
                ),
            }
        slow_flag = False
        try:
            if _global_cfg and _global_cfg.activity_step_slow_ms > 0:
                slow_flag = dur_ms >= _global_cfg.activity_step_slow_ms
        except Exception:
            pass
        logger.info(
            "[退出] %s",
            name,
            extra={
                "extra_data": {
                    "类型": "退出",
                    "event": "exit",
                    "duration_ms": dur_ms,
                    "resource_delta": delta,
                    **({"slow": True} if slow_flag else {}),
                }
            },
        )


def log_sql(
    sql: str,
    params: Optional[dict[str, Any]] = None,
    duration_ms: Optional[int] = None,
    rows: Optional[int] = None,
    error: Optional[str] = None,
    slow_ms: Optional[int] = None,
) -> None:
    logger = logging.getLogger("sql")
    level = logging.ERROR if error else logging.INFO
    # 慢SQL标注（优先使用函数参数，其次从全局配置读取）
    global _global_cfg
    slow_threshold = (
        slow_ms
        if slow_ms is not None
        else (_global_cfg.sql_slow_ms if _global_cfg else None)
    )

    # 线程名注入（同时保留在 extra_json 内，便于日志文件内独立解析）
    try:
        import threading as _th

        thread_name = _th.current_thread().name
    except Exception:
        thread_name = None

    extra = {
        "type": "SQL",
        "sql": sql,
        "params": params or {},
        "duration_ms": duration_ms,
        "rows": rows,
        # 结果：无错误=ok，有错误=error（不本地中文化，保持英文键/值以便对齐要求）
        "result": ("error" if error else "ok"),
    }
    if thread_name:
        extra["threadName"] = thread_name
    if error:
        extra["error"] = error

    # 输出日志（含慢SQL标记）
    slow_flag = False
    if slow_threshold and duration_ms is not None:
        try:
            slow_flag = duration_ms >= int(slow_threshold)
        except Exception:
            slow_flag = False

    logger.log(
        level,
        "[SQL] 执行",
        extra={
            "extra_data": {
                **extra,
                **({"slow": True} if slow_flag else {}),
            }
        },
    )


def log_db_function(
    name: str,
    *,
    args: Optional[dict[str, Any]] = None,
    duration_ms: Optional[int] = None,
    rows: Optional[int] = None,
    error: Optional[str] = None,
) -> None:
    """记录数据库函数调用（应用侧）。

    - name: 函数名（如 public.fn_startstop_windows）
    - args: 关键参数摘要（避免放入大对象）
    - duration_ms: 执行耗时（ms）
    - rows: 返回行数（如 SELECT 函数）
    - error: 错误信息（有则 ERROR 级别）
    """
    logger = logging.getLogger("db.func")
    level = logging.ERROR if error else logging.INFO
    logger.log(
        level,
        "[DB函数] 调用",
        extra={
            "extra_data": {
                "类型": "DB_FUNC",
                "函数": name,
                "参数": args or {},
                "耗时ms": duration_ms,
                "行数": rows,
                **({"错误": error} if error else {}),
            }
        },
    )


def log_db_view(
    name: str,
    *,
    filters: Optional[dict[str, Any]] = None,
    duration_ms: Optional[int] = None,
    rows: Optional[int] = None,
    error: Optional[str] = None,
) -> None:
    """记录视图查询（应用侧）。

    - name: 视图名（如 public.v_startstop_windows）
    - filters: 过滤条件/参数摘要
    - duration_ms: 执行耗时（ms）
    - rows: 返回行数
    - error: 错误信息（有则 ERROR 级别）
    """
    logger = logging.getLogger("db.view")
    level = logging.ERROR if error else logging.INFO
    logger.log(
        level,
        "[视图] 查询",
        extra={
            "extra_data": {
                "类型": "DB_VIEW",
                "视图": name,
                "过滤": filters or {},
                "耗时ms": duration_ms,
                "行数": rows,
                **({"错误": error} if error else {}),
            }
        },
    )


def log_http_out(
    method: str,
    url: str,
    status: Optional[int] = None,
    *,
    host: Optional[str] = None,
    duration_ms: Optional[int] = None,
    req_headers: Optional[dict[str, Any]] = None,
    resp_bytes: Optional[int] = None,
    error: Optional[str] = None,
) -> None:
    """记录出站 HTTP 调用（需在 YAML 启用）。"""
    if not (_global_cfg and _global_cfg.http_out_enabled):
        return
    logger = logging.getLogger("dep.http")
    mh = set(k.lower() for k in (_global_cfg.http_out_mask_headers or []))
    safe_headers = {}
    if isinstance(req_headers, dict):
        for k, v in req_headers.items():
            if isinstance(k, str) and k.lower() in mh:
                safe_headers[k] = "***"
            else:
                safe_headers[k] = v
    extra = {
        "类型": "HTTP_OUT",
        "method": method,
        "url": url,
        "host": host,
        "status": status,
        "duration_ms": duration_ms,
        "req_headers": safe_headers,
        "resp_size": resp_bytes,
        "error": error,
    }
    level = logging.INFO if not error else logging.ERROR
    logger.log(level, "[HTTP] OUT %s %s", method, url, extra={"extra_data": extra})


def log_cache(
    op: str,
    *,
    key_hash: Optional[str] = None,
    hit: Optional[bool] = None,
    duration_ms: Optional[int] = None,
    bytes: Optional[int] = None,
    ttl: Optional[int] = None,
    reason: Optional[str] = None,
) -> None:
    if not (_global_cfg and _global_cfg.cache_enabled):
        return
    level = logging.INFO
    slow = False
    if _global_cfg.cache_slow_ms and duration_ms is not None:
        slow = duration_ms >= _global_cfg.cache_slow_ms
    if (hit is False) or slow:
        logger = logging.getLogger("cache")
        msg = f"[CACHE]{'[慢]' if slow else ''} {op}"
        extra = {
            "类型": "CACHE",
            "op": op,
            "key_hash": key_hash,
            "hit": hit,
            "duration_ms": duration_ms,
            "bytes": bytes,
            "ttl": ttl,
            "reason": reason,
        }
        logger.log(level, msg, extra={"extra_data": extra})


def log_tx(
    event: str, *, tx_id: Optional[str] = None, error: Optional[str] = None
) -> None:
    if not (_global_cfg and _global_cfg.tx_enabled):
        return
    logger = logging.getLogger("db.tx")
    extra = {"类型": "TX", "event": event, "tx_id": tx_id, "error": error}
    level = logging.INFO if error is None else logging.ERROR
    logger.log(level, f"[TX] {event}", extra={"extra_data": extra})


def log_biz(
    action: str, status: str = "info", detail: Optional[dict[str, Any]] = None
) -> None:
    logger = logging.getLogger("biz")
    extra = {"类型": "业务", "action": action, "status": status, "detail": detail or {}}
    logger.info("[业务] %s %s", action, status, extra={"extra_data": extra})


# DB Pool logging API


def log_db_pool(event: str, detail: dict[str, Any], level: int | None = None) -> None:
    """数据库连接池日志（统一入口）。受 logging.database.pool_log.enabled 控制。

    目标：中文可读，同时保留英文字段（如 result/threadName/age_ms/idle_ms/pool_id/use_count/wait_ms/total/idle/active）。
    """
    if not (_global_cfg and _global_cfg.db_pool_enabled):
        return

    logger = logging.getLogger("db.pool")
    lvl = logging.INFO if level is None else level

    # 事件名中英对照
    event_cn_map = {
        "CREATE": "创建",
        "ACQUIRE": "获取",
        "RELEASE": "归还",
        "HEALTH_CHECK": "健康检查",
        "CLOSE": "关闭",
    }

    # 细分子事件（detail.get("event")）的中英映射
    subevent_cn_map = {
        "create": "创建",
        "acquire": "获取",
        "release_pre": "归还前检查",
        "release": "归还",
        "health_check": "健康检查",
        "close_begin": "开始关闭",
        "close_end": "关闭结束",
        "close_summary": "关闭汇总",
    }

    # 线程名注入（按配置）
    try:
        import threading as _th

        th_name = (
            _th.current_thread().name if _global_cfg.db_pool_include_thread else None
        )
    except Exception:
        th_name = None

    # 英文字段原样保留（基础集）
    detail_en: dict[str, Any] = dict(detail or {})
    if th_name and "threadName" not in detail_en:
        detail_en["threadName"] = th_name

    # 中文别名映射（仅追加，不删除英文字段）——改为使用全局 localize_map 配置
    key_cn_map = (
        _global_cfg.localize_map if _global_cfg and _global_cfg.localize_map else {}
    )

    value_cn_map = {
        "cached": "缓存",
        "direct": "直接",
        True: "正常",
        False: "异常",
    }

    # 生成中文同义字段
    detail_cn: dict[str, Any] = {}
    for k, v in detail_en.items():
        v_cn = v
        if k == "event" and isinstance(v, str):
            v_cn = subevent_cn_map.get(v, v)
        elif k == "type" and isinstance(v, str):
            v_cn = value_cn_map.get(v, v)
        elif k == "result" and isinstance(v, bool):
            v_cn = value_cn_map.get(v, v)
        cn_key = key_cn_map.get(k)
        if cn_key:
            detail_cn[cn_key] = v_cn

    # 事件抬头中文化
    event_upper = (event or "").upper()
    event_cn = event_cn_map.get(event_upper, event)

    # 统一 extra：先放入英文字段，再追加中文同义字段；并补充类型/中文类型
    extra_payload = {
        "type": "DB_POOL",
        "类型": "DB_POOL",
        "类型_中文": "数据库连接池",
        **detail_en,
        **detail_cn,
    }

    logger.log(lvl, f"[连接池] {event_cn}", extra={"extra_data": extra_payload})
