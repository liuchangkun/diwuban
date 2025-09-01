from __future__ import annotations

"""
日志适配器（adapters.logging）：统一的结构化日志输出与路由策略
- JsonFormatter/TextFormatter：控制输出格式（默认 JSON）
- init_logging(settings, run_dir)：初始化全局日志，支持 by_run/by_module 路由
- write_run_snapshot*：将本次运行的参数和配置快照输出到 env.json，并写入首行 app 日志

设计要点：
- 遵循 docs/日志规范.md 的事件命名与字段（task.begin/db.exec.*/align.merge.window 等）
- JSON 格式字段统一，禁止泄露敏感信息（本项目默认不脱敏，仅开发环境使用）
- 便于 CLI 与服务端共用；TextFormatter 用于本地调试可读
- 集成启动清理功能：每次程序启动时根据配置清理数据库和日志目录
"""


import json
import logging
import logging.handlers
import os
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict

from app.core.config.loader import Settings

# 全局变量跟踪清理状态，避免重复执行
_cleanup_performed = False


class JsonFormatter(logging.Formatter):
    """JSON 格式化器：用于结构化落盘（app/sql/perf）与控制台回显。
    - 支持自定义时间戳格式与消息最大长度（截断）
    - 字段顺序按 settings.logging.formatting.field_order（仅对常见字段尝试排序）
    """

    def __init__(
        self,
        timestamp_format: str | None = None,
        max_message_length: int | None = None,
        field_order: tuple[str, ...] | None = None,
    ) -> None:
        super().__init__()
        self.ts_fmt = timestamp_format
        self.max_len = max(0, int((max_message_length or 0)))
        self.field_order = tuple(field_order or ())

    def _now_str(self) -> str:
        if self.ts_fmt:
            try:
                return datetime.now(UTC).strftime(self.ts_fmt)
            except Exception:
                pass
        return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")

    def format(self, record: logging.LogRecord) -> str:
        msg = record.getMessage()
        if self.max_len and isinstance(msg, str) and len(msg) > self.max_len:
            msg = msg[: self.max_len] + "…"
        payload: Dict[str, Any] = {
            "timestamp": self._now_str(),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", None),
            "message": msg,
        }
        extra = getattr(record, "extra", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if self.field_order:
            ordered: Dict[str, Any] = {}
            for k in self.field_order:
                if k in payload:
                    ordered[k] = payload[k]
            for k, v in payload.items():
                if k not in ordered:
                    ordered[k] = v
            payload = ordered
        return json.dumps(
            payload, ensure_ascii=False, separators=(",", ":"), default=str
        )


class TextFormatter(logging.Formatter):
    def __init__(
        self, timestamp_format: str | None = None, max_message_length: int | None = None
    ) -> None:
        super().__init__()
        self.ts_fmt = timestamp_format
        self.max_len = max(0, int((max_message_length or 0)))

    def format(self, record: logging.LogRecord) -> str:
        if self.ts_fmt:
            try:
                ts = datetime.now(UTC).strftime(self.ts_fmt)
            except Exception:
                ts = (
                    datetime.now(UTC)
                    .isoformat(timespec="seconds")
                    .replace("+00:00", "Z")
                )
        else:
            ts = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        parts = [record.levelname, f"ts={ts}", f"logger={record.name}"]
        event = getattr(record, "event", None)
        if event:
            parts.append(f"event={event}")
        extra = getattr(record, "extra", None)
        if isinstance(extra, dict):
            for k in ("window_start", "window_end", "rows", "rows_merged", "sql_op"):
                if k in extra and extra[k] is not None:
                    parts.append(f"{k}={extra[k]}")
        msg = record.getMessage()
        if self.max_len and isinstance(msg, str) and len(msg) > self.max_len:
            msg = msg[: self.max_len] + "…"
        if msg:
            parts.append(f"msg={msg}")
        return " ".join(parts)


def compute_run_dir(base: Path | None = None) -> Path:
    """计算本次运行的日志目录（按天/按进程区分）
    - base: 基础目录，默认 logs/runs
    - 返回值: logs/runs/YYYYMMDD/HHMMSS-pidXXX
    """
    base = base or Path("logs") / "runs"
    today = datetime.now(UTC).strftime("%Y%m%d")
    job_id = datetime.now(UTC).strftime("%H%M%S") + f"-pid{os.getpid()}"
    return base / today / job_id


def init_logging(
    settings: Settings,
    run_dir: Path,
    *,
    override_format: str | None = None,
    override_routing: str | None = None,
    override_console_level: str | None = None,
    quiet: bool | None = None,
) -> None:
    global _cleanup_performed

    # 执行启动清理（仅在首次调用时执行）
    if not _cleanup_performed and hasattr(settings.logging, "startup_cleanup"):
        cleanup_config = settings.logging.startup_cleanup
        if cleanup_config.clear_logs or cleanup_config.clear_database:
            # 设置基本的控制台日志，用于记录清理过程
            basic_logger = logging.getLogger("startup_cleanup")
            basic_logger.setLevel(logging.INFO)
            if not basic_logger.handlers:
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(
                    logging.Formatter(
                        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                    )
                )
                basic_logger.addHandler(console_handler)

            try:
                from app.services.system.cleanup import perform_startup_cleanup

                perform_startup_cleanup(settings)
                _cleanup_performed = True
            except Exception as e:
                basic_logger.error(f"启动清理失败，但程序将继续运行: {e}")
                # 即使清理失败，也标记为已执行，避免重复尝试
                _cleanup_performed = True

    run_dir.mkdir(parents=True, exist_ok=True)

    # 注意：LoggingSettings 是冻结数据类，CLI 层若需临时覆盖应使用局部变量而非直接赋值
    # 允许 CLI 提供一次性覆盖；默认仍以 YAML 为准
    fmt = (override_format or settings.logging.format or "json").lower()
    routing = (override_routing or settings.logging.routing or "by_run").lower()
    fmt_cfg = settings.logging.formatting
    formatter: logging.Formatter = (
        JsonFormatter(
            fmt_cfg.timestamp_format, fmt_cfg.max_message_length, fmt_cfg.field_order
        )
        if fmt == "json"
        else TextFormatter(fmt_cfg.timestamp_format, fmt_cfg.max_message_length)
    )

    # 控制台级别：默认跟随全局 level；--quiet 至少 WARNING；--console-level 覆盖
    root = logging.getLogger()
    root_level = getattr(logging, settings.logging.level.upper(), logging.INFO)
    root.setLevel(root_level)
    console_level = root_level
    if isinstance(override_console_level, str) and override_console_level:
        console_level = getattr(logging, override_console_level.upper(), console_level)
    if quiet:
        console_level = logging.WARNING
    # 清理旧 handler，避免重复添加
    for h in list(root.handlers):
        root.removeHandler(h)

    if routing == "by_module":
        modules_dir = Path("logs") / "modules"
        modules_dir.mkdir(parents=True, exist_ok=True)

        class ByModuleRouter(logging.Handler):
            def __init__(self, base: Path, fmt: logging.Formatter) -> None:
                super().__init__()
                self.base = base
                self.fmt = fmt
                self._handlers: dict[str, logging.FileHandler] = {}

            def emit(self, record: logging.LogRecord) -> None:
                name = record.name or "root"
                # 将 logger 名转换为文件名：保留点号更易阅读
                path = self.base / f"{name}.log"
                handler = self._handlers.get(name)
                if handler is None:
                    handler = logging.FileHandler(path, encoding="utf-8")
                    handler.setFormatter(self.fmt)
                    self._handlers[name] = handler
                handler.emit(record)

        root.addHandler(ByModuleRouter(modules_dir, formatter))
        # 控制台输出（TextFormatter，更可读；尊重 console_level）
        console = logging.StreamHandler()
        console.setLevel(console_level)
        console.setFormatter(
            TextFormatter(fmt_cfg.timestamp_format, fmt_cfg.max_message_length)
        )
        root.addHandler(console)
        return

    # by_run：仍按运行目录落盘，多流文件，扩展名根据格式调整
    ext = "ndjson" if fmt == "json" else "log"
    app_log = run_dir / f"app.{ext}"
    err_log = run_dir / f"error.{ext}"
    sql_log = run_dir / f"sql.{ext}"
    perf_log = run_dir / f"perf.{ext}"

    # 轮转策略
    rot = settings.logging.rotation

    def _mk_file_handler(path: Path) -> logging.Handler:
        if rot.rotation_interval and int(rot.rotation_interval) > 0:
            # 按时间轮转（秒）
            # TimedRotatingFileHandler 支持 's' 秒级；backupCount 控制保留份数
            return logging.handlers.TimedRotatingFileHandler(
                path,
                when="s",
                interval=int(rot.rotation_interval),
                backupCount=int(rot.backup_count),
                encoding="utf-8",
            )
        else:
            # 按大小轮转
            return logging.handlers.RotatingFileHandler(
                path,
                maxBytes=int(rot.max_bytes),
                backupCount=int(rot.backup_count),
                encoding="utf-8",
            )

    # app/info
    app_handler = _mk_file_handler(app_log)
    app_handler.setFormatter(formatter)
    app_handler.setLevel(logging.INFO)

    # error/warn
    err_handler = _mk_file_handler(err_log)
    err_handler.setFormatter(formatter)
    err_handler.setLevel(logging.WARNING)

    # sql/perf 子 logger
    sql_logger = logging.getLogger("sql")
    sql_handler = _mk_file_handler(sql_log)
    sql_handler.setFormatter(formatter)
    sql_handler.setLevel(logging.INFO)
    sql_logger.setLevel(logging.INFO)
    sql_logger.propagate = False
    sql_logger.addHandler(sql_handler)

    perf_logger = logging.getLogger("perf")
    perf_handler = _mk_file_handler(perf_log)
    perf_handler.setFormatter(formatter)
    perf_handler.setLevel(logging.INFO)
    perf_logger.setLevel(logging.INFO)
    perf_logger.propagate = False
    perf_logger.addHandler(perf_handler)

    # 控制台输出采用 TextFormatter，并设置级别
    console = logging.StreamHandler()
    console.setLevel(console_level)
    console.setFormatter(
        TextFormatter(fmt_cfg.timestamp_format, fmt_cfg.max_message_length)
    )

    # 异步处理（可选）
    if settings.logging.queue_handler:
        import queue

        q: "queue.Queue[logging.LogRecord]" = queue.Queue(
            maxsize=int(settings.logging.performance.async_handler_queue_size)
        )
        root.addHandler(logging.handlers.QueueHandler(q))
        listener = logging.handlers.QueueListener(q, app_handler, err_handler)
        listener.start()
        # 子 logger（sql/perf）使用各自 handler，保持直连以避免错序
        root.addHandler(console)
    else:
        root.addHandler(app_handler)
        root.addHandler(err_handler)
        root.addHandler(console)


def write_run_snapshot(
    settings: Settings, run_dir: Path, args_summary: Dict[str, Any]
) -> None:
    """写入启动快照（不脱敏）：env.json 文件 + 首行 app 日志。
    - args_summary: 本次 CLI 的参数摘要（字典）
    - config_snapshot: dataclass Settings 转 dict（不脱敏）
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    snapshot = {
        "args_summary": args_summary,
        "config_snapshot": asdict(settings),
        "ts": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    # 写 env.json
    env_path = run_dir / "env.json"
    env_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # 记录到 app.ndjson 首行
    logging.getLogger().info(
        "run snapshot", extra={"event": "task.begin", "extra": snapshot}
    )


def write_run_snapshot_with_sources(
    settings: Settings,
    run_dir: Path,
    args_summary: Dict[str, Any],
    sources: Dict[str, Any],
) -> None:
    """写入启动快照（不脱敏），包含来源标注 sources。"""
    run_dir.mkdir(parents=True, exist_ok=True)
    snapshot = {
        "args_summary": args_summary,
        "config_snapshot": asdict(settings),
        "sources": sources,
        "ts": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    env_path = run_dir / "env.json"
    env_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logging.getLogger().info(
        "run snapshot", extra={"event": "task.begin", "extra": snapshot}
    )
