"""
日志查看 API 端点（app.api.v1.endpoints.logs）

提供系统日志查看功能：
- 日志记录查询
- 日志级别过滤
- 时间范围筛选
- 关键词搜索
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import structlog
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.core.config.loader_new import load_settings

router = APIRouter()

# 加载配置
settings = load_settings(Path("configs"))

# 获取结构化日志器
logger = structlog.get_logger("api.logs")


class LogEntry(BaseModel):
    """日志条目模型"""

    timestamp: str
    level: str
    message: str
    module: Optional[str] = None
    request_id: Optional[str] = None
    duration_ms: Optional[float] = None
    client_ip: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None


class LogsResponse(BaseModel):
    """日志查询响应模型"""

    logs: List[LogEntry]
    total_count: int
    has_more: bool
    query_info: dict


@router.get("/search", response_model=LogsResponse)
async def search_logs(
    request: Request,
    level: Optional[str] = Query(
        None, description="日志级别过滤（大小写不敏感，支持 WARN）"
    ),
    search: Optional[str] = Query(None, description="搜索关键词"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    fmt: Optional[str] = Query(
        None,
        alias="format",
        description="日志格式：log | json | ndjson；为空则自动识别",
    ),
) -> LogsResponse:
    """
    搜索系统日志

    支持按级别、关键词、时间范围搜索日志记录
    """
    query_start_time = datetime.now()

    logger.info(
        "日志搜索请求开始",
        level=level,
        search=search,
        start_time=start_time.isoformat() if start_time else None,
        end_time=end_time.isoformat() if end_time else None,
        limit=limit,
        offset=offset,
        client_ip=request.client.host if request.client else "unknown",
    )

    try:
        # 读取日志文件
        logs = []
        total_count = 0

        # 查找日志文件
        log_dir = Path("logs")
        if not log_dir.exists():
            log_dir = Path(".")  # 如果logs目录不存在，在当前目录查找

        # 查找所有日志文件（同时支持 .log/.ndjson/.jsonl）
        log_files = []
        for pattern in ["*.log", "*.ndjson", "*.jsonl", "app*.log", "api*.log"]:
            log_files.extend(log_dir.glob(pattern))

        if not log_files:
            # 如果没有找到日志文件，返回空结果
            logger.warning("未找到日志文件")
            return LogsResponse(
                logs=[],
                total_count=0,
                has_more=False,
                query_info={
                    "level": level,
                    "search": search,
                    "start_time": start_time.isoformat() if start_time else None,
                    "end_time": end_time.isoformat() if end_time else None,
                    "files_searched": 0,
                },
            )

        # 设置默认时间范围（最近24小时）
        if not start_time:
            start_time = datetime.now() - timedelta(hours=24)
        if not end_time:
            end_time = datetime.now()

        # 中文注释：标准化 level 参数（大小写 + 同义映射），确保与 Python 标准日志级别匹配
        level_std = level.upper() if level else None
        if level_std == "WARN":
            level_std = "WARNING"

        # 中文注释：标准化 format 参数
        fmt_std = (fmt or "").lower() or None  # None 表示自动识别（默认策略）
        VALID_FORMATS = {"log", "json", "ndjson"}
        if fmt_std is not None and fmt_std not in VALID_FORMATS:
            # 不合法的 format 退回自动识别，避免报错
            fmt_std = None

        # 安全上限：限制扫描的文件数与单文件行数，避免超大日志导致阻塞
        MAX_FILES_TO_SCAN = 5
        MAX_LINES_PER_FILE = 200000

        # 读取和解析日志文件
        all_logs = []
        files_searched = 0
        lines_scanned_total = 0

        for log_file in sorted(
            log_files, key=lambda x: x.stat().st_mtime, reverse=True
        ):
            try:
                files_searched += 1
                with open(log_file, "r", encoding="utf-8") as f:
                    lines_processed = 0
                    for line_num, line in enumerate(f):
                        # 安全上限：单文件最多处理 MAX_LINES_PER_FILE 行
                        if lines_processed >= MAX_LINES_PER_FILE:
                            break

                        line = line.strip()
                        if not line:
                            continue

                        lines_processed += 1
                        lines_scanned_total += 1

                        try:
                            # 更健壮的解析策略：format 作为“偏好”，始终按行内容再做一次形态判断
                            is_json_line = line.lstrip().startswith("{")
                            if fmt_std in ("json", "ndjson"):
                                # 优先按 JSON 解析，失败则回退文本解析
                                try:
                                    log_data = json.loads(line)
                                    log_entry = parse_json_log(log_data)
                                except json.JSONDecodeError:
                                    log_entry = parse_text_log(
                                        line, line_num + 1, log_file.name
                                    )
                            elif fmt_std == "log":
                                # 若用户强制 log，但行看起来是 JSON，也尝试 JSON 解析；否则按文本
                                if is_json_line:
                                    try:
                                        log_data = json.loads(line)
                                        log_entry = parse_json_log(log_data)
                                    except json.JSONDecodeError:
                                        log_entry = parse_text_log(
                                            line, line_num + 1, log_file.name
                                        )
                                else:
                                    log_entry = parse_text_log(
                                        line, line_num + 1, log_file.name
                                    )
                            else:
                                # 自动：按行首判断
                                if is_json_line:
                                    try:
                                        log_data = json.loads(line)
                                        log_entry = parse_json_log(log_data)
                                    except json.JSONDecodeError:
                                        log_entry = parse_text_log(
                                            line, line_num + 1, log_file.name
                                        )
                                else:
                                    log_entry = parse_text_log(
                                        line, line_num + 1, log_file.name
                                    )

                            if log_entry and filter_log_entry(
                                log_entry, level_std, search, start_time, end_time
                            ):
                                all_logs.append(log_entry)

                        except (json.JSONDecodeError, ValueError):
                            # 跳过无法解析的行
                            continue

                # 限制读取的文件数量以避免性能问题
                if files_searched >= MAX_FILES_TO_SCAN:
                    break

            except Exception as e:
                logger.warning(f"读取日志文件失败: {log_file}", error=str(e))
                continue

        # 按时间戳排序（最新的在前）
        all_logs.sort(key=lambda x: x.timestamp, reverse=True)

        # 分页处理
        total_count = len(all_logs)
        logs = all_logs[offset : offset + limit]

        # 转换为响应格式
        log_entries = [LogEntry(**log.__dict__) for log in logs]

        response = LogsResponse(
            logs=log_entries,
            total_count=total_count,
            has_more=offset + len(logs) < total_count,
            query_info={
                "level": level_std,
                "search": search,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "files_searched": files_searched,
                "format": fmt_std,
                "max_lines_per_file": MAX_LINES_PER_FILE,
                "lines_scanned": lines_scanned_total,
            },
        )

        query_duration = (datetime.now() - query_start_time).total_seconds() * 1000

        logger.info(
            "日志搜索完成",
            results_count=len(logs),
            total_count=total_count,
            files_searched=files_searched,
            duration_ms=round(query_duration, 2),
        )

        return response

    except Exception as e:
        logger.error("日志搜索失败", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"日志搜索失败: {str(e)}")


class SimpleLogEntry:
    """简单日志条目类"""

    def __init__(
        self,
        timestamp,
        level,
        message,
        module=None,
        request_id=None,
        duration_ms=None,
        client_ip=None,
        method=None,
        path=None,
    ):
        self.timestamp = timestamp
        self.level = level
        self.message = message
        self.module = module
        self.request_id = request_id
        self.duration_ms = duration_ms
        self.client_ip = client_ip
        self.method = method
        self.path = path


# =================== 新增：通用解码与口语化工具（服务端端）===================
# 中文注释：
# - 解决日志中 msg 为“JSON 字符串（含 \\uXXXX）”的可读性
# - 将结构化事件（event/extra.extra）转为口语化摘要


def _looks_json_text(s: str) -> bool:
    return isinstance(s, str) and s.strip().startswith(("{", "["))


def _decode_unicode_string(s: str) -> str:
    """尽可能将包含 \\uXXXX 的字符串还原为可读中文。
    - 若 s 本身是 JSON 字符串字面量（"..."），直接 json.loads
    - 否则尝试包裹成 JSON 字符串并 json.loads（转义双引号）
    失败则原样返回
    """
    if not isinstance(s, str):
        return s  # type: ignore[return-value]
    try:
        t = s.strip()
        if len(t) >= 2 and t[0] == t[-1] and t[0] in ('"', "'"):
            return json.loads(t)
        wrapped = '"' + s.replace('"', '\\"') + '"'
        return json.loads(wrapped)
    except Exception:
        return s


def _parse_json_deep(s: str):
    """尝试最多两次将字符串解析为 JSON 对象。成功返回 dict，否则返回 None。"""
    if not isinstance(s, str):
        return None
    cur = s
    for _ in range(2):
        if _looks_json_text(cur):
            try:
                cur = json.loads(cur)
            except Exception:
                break
        else:
            break
    return cur if isinstance(cur, dict) else None


def _humanize_from_obj(obj: dict) -> str | None:
    """从结构化对象提取口语化摘要。"""
    try:
        event = obj.get("event") or (obj.get("extra") or {}).get("event")
        ext = (obj.get("extra") or {}).get("extra") or obj.get("extra") or {}

        def _round(v):
            try:
                return round(float(v), 2)
            except Exception:
                return v

        def _preview(txt, n: int = 160) -> str:
            try:
                s = str(txt or "")
            except Exception:
                s = ""
            return " ".join(s.split())[:n]

        mapping: dict[str, callable] = {
            "api.request.start": lambda: f"收到 {ext.get('method','')} {ext.get('path') or ext.get('url') or ''} 请求，来自 {ext.get('client_ip') or ext.get('remote_addr') or ''}",
            "api.request.success": lambda: f"请求完成，状态 {ext.get('status_code')}，用时 {_round(ext.get('duration_ms'))}ms，返回 {ext.get('content_type') or ''}，长度 {ext.get('content_length') or ''}",
            "pool.initialized": lambda: f"连接池初始化完成，最小连接 {obj.get('min_size')}，最大连接 {obj.get('max_size')}",
            "db.init.success": lambda: f"数据库连接池初始化成功（{obj.get('host') or ''}/{obj.get('database') or ''}）",
            "api.sql.executed": lambda: f"执行 SQL，用时 {_round(ext.get('duration_ms'))}ms{(f'，影响行数 {ext.get('affected_rows')}' if ext.get('affected_rows') is not None else '')}\nSQL 预览：{_preview(ext.get('sql'))}",
            "task.begin": lambda: f"任务开始：{_preview(obj.get('message'))}",
            # 中文事件名（startup/health 等）
            "健康检查完成": lambda: f"健康检查完成：连接池已{ '初始化' if obj.get('db_initialized') else '未初始化' }",
            "应用初始化完成": lambda: f"应用初始化完成（{_preview(obj)}）",
            "日志系统初始化完成": lambda: "日志系统初始化完成",
            "数据库连接池初始化完成": lambda: "数据库连接池初始化完成",
        }
        if event in mapping:
            return mapping[event]()
        # 没有标准事件，回退 message/msg 字段
        if "message" in obj:
            return _decode_unicode_string(str(obj.get("message")))
        if "msg" in obj:
            return _decode_unicode_string(str(obj.get("msg")))
        return None
    except Exception:
        return None


def parse_json_log(log_data: dict) -> Optional[SimpleLogEntry]:
    """解析JSON格式的日志，并口语化 message 字段（中文注释）。"""
    try:
        # 兼容不同字段命名：timestamp/time/ts
        timestamp = log_data.get(
            "timestamp", log_data.get("time", log_data.get("ts", ""))
        )
        level = (log_data.get("level") or "INFO").upper()
        # 原始消息（可能是事件名或嵌套 JSON 字符串）
        # 注意：.get('event') 可能为空字符串，不能作为有效消息；改用“或链”确保取到非空值
        raw_message = (
            log_data.get("event")
            or log_data.get("message")
            or log_data.get("msg")
            or ""
        )

        # 优先从顶层对象口语化
        human = _humanize_from_obj(log_data)
        # 若失败且 raw_message 看起来是嵌套 JSON 字符串，尝试解析后口语化
        if not human and isinstance(raw_message, str):
            nested = _parse_json_deep(_decode_unicode_string(raw_message))
            if isinstance(nested, dict):
                human = _humanize_from_obj(nested)
        # 最后回退：尽量解码字符串以显示中文
        if not human and isinstance(raw_message, str):
            human = _decode_unicode_string(raw_message)
        message = human if isinstance(human, str) else str(raw_message)

        # 进一步提取结构化字段用于分组：request_id/method/path/client_ip/duration_ms
        nested_obj = None
        if isinstance(raw_message, str):
            nested_obj = _parse_json_deep(_decode_unicode_string(raw_message))
        ext_for_fields = None
        if isinstance(nested_obj, dict):
            ext_for_fields = (
                (nested_obj.get("extra") or {}).get("extra")
                or nested_obj.get("extra")
                or {}
            )
        request_id = (
            log_data.get("request_id")
            or (ext_for_fields or {}).get("request_id")
            or (nested_obj or {}).get("request_id")
            or (nested_obj or {}).get("headers", {}).get("x-request-id")
        )
        method_f = log_data.get("method") or (ext_for_fields or {}).get("method")
        path_f = (
            log_data.get("path")
            or (ext_for_fields or {}).get("path")
            or (ext_for_fields or {}).get("url")
        )
        client_ip_f = (
            log_data.get("client_ip")
            or (ext_for_fields or {}).get("client_ip")
            or (ext_for_fields or {}).get("remote_addr")
        )
        duration_f = log_data.get("duration_ms") or (ext_for_fields or {}).get(
            "duration_ms"
        )

        return SimpleLogEntry(
            timestamp=timestamp,
            level=level,
            message=message,
            module=log_data.get("logger", log_data.get("module")),
            request_id=request_id,
            duration_ms=duration_f,
            client_ip=client_ip_f,
            method=method_f,
            path=path_f,
        )
    except Exception:
        return None


def parse_text_log(line: str, line_num: int, filename: str) -> Optional[SimpleLogEntry]:
    """解析文本格式的日志：尽量提取时间/级别，并对消息做解码（中文注释）。"""
    try:
        # 简单的文本日志解析
        parts = line.split(" ", 3)
        if len(parts) >= 3:
            timestamp = f"{parts[0]} {parts[1]}" if len(parts) > 1 else parts[0]
            level = parts[2].strip("[]").upper() if len(parts) > 2 else "INFO"
            raw_msg = parts[3] if len(parts) > 3 else line
            # 尝试将 msg 作为嵌套 JSON 解码并口语化
            msg_obj = (
                _parse_json_deep(_decode_unicode_string(raw_msg))
                if isinstance(raw_msg, str)
                else None
            )
            human_msg = (
                _humanize_from_obj(msg_obj) if isinstance(msg_obj, dict) else None
            )
            message = human_msg or _decode_unicode_string(raw_msg)

            # 进一步提取结构化字段用于分组
            request_id = None
            method_f = None
            path_f = None
            client_ip_f = None
            duration_f = None
            if isinstance(msg_obj, dict):
                ext_for_fields = (
                    (msg_obj.get("extra") or {}).get("extra")
                    or msg_obj.get("extra")
                    or {}
                )
                request_id = (
                    (ext_for_fields or {}).get("request_id")
                    or msg_obj.get("request_id")
                    or (msg_obj.get("headers", {}) or {}).get("x-request-id")
                )
                method_f = ext_for_fields.get("method")
                path_f = ext_for_fields.get("path") or ext_for_fields.get("url")
                client_ip_f = ext_for_fields.get("client_ip") or ext_for_fields.get(
                    "remote_addr"
                )
                duration_f = ext_for_fields.get("duration_ms")

            return SimpleLogEntry(
                timestamp=timestamp,
                level=level,
                message=message,
                module=f"{filename}:{line_num}",
                request_id=request_id,
                duration_ms=duration_f,
                client_ip=client_ip_f,
                method=method_f,
                path=path_f,
            )
    except Exception:
        pass

    # 如果解析失败，返回原始行作为消息（并做一次解码）
    return SimpleLogEntry(
        timestamp=datetime.now().isoformat(),
        level="INFO",
        message=_decode_unicode_string(line),
        module=f"{filename}:{line_num}",
    )


def filter_log_entry(
    log_entry: SimpleLogEntry,
    level: Optional[str],
    search: Optional[str],
    start_time: datetime,
    end_time: datetime,
) -> bool:
    """过滤日志条目"""
    try:
        # 时间过滤
        if log_entry.timestamp:
            try:
                # 尝试解析各种时间格式
                log_time = None
                timestamp_str = log_entry.timestamp

                # 常见的时间格式
                time_formats = [
                    "%Y-%m-%dT%H:%M:%S.%f%z",
                    "%Y-%m-%dT%H:%M:%S%z",
                    "%Y-%m-%d %H:%M:%S.%f",
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S.%f",
                    "%Y-%m-%dT%H:%M:%S",
                ]

                for fmt in time_formats:
                    try:
                        log_time = datetime.strptime(timestamp_str, fmt)
                        if log_time.tzinfo is None:
                            log_time = log_time.replace(tzinfo=start_time.tzinfo)
                        break
                    except ValueError:
                        continue

                if log_time:
                    if start_time.tzinfo is None:
                        start_time = start_time.replace(tzinfo=None)
                        end_time = end_time.replace(tzinfo=None)
                        if log_time.tzinfo:
                            log_time = log_time.replace(tzinfo=None)

                    if not (start_time <= log_time <= end_time):
                        return False

            except Exception:
                # 如果时间解析失败，跳过时间过滤
                pass

        # 级别过滤
        if level and log_entry.level != level:
            return False

        # 关键词搜索
        if search:
            search_lower = search.lower()
            if not any(
                search_lower in str(getattr(log_entry, attr, "")).lower()
                for attr in ["message", "module", "path"]
            ):
                return False

        return True

    except Exception:
        return True  # 如果过滤出错，默认包含该条目


@router.get("/levels")
async def get_log_levels():
    """获取可用的日志级别（中文注释：对外暴露 WARN，与内部 WARNING 对应）"""
    return {
        "levels": ["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"],
        "mapping": {"WARN": "WARNING"},
        "description": "系统支持的日志级别",
    }


@router.get("/stats")
async def get_log_stats():
    """获取日志统计信息"""
    try:
        log_dir = Path("logs")
        if not log_dir.exists():
            log_dir = Path(".")

        log_files = list(log_dir.glob("*.log"))

        total_size = sum(f.stat().st_size for f in log_files)

        return {
            "log_files_count": len(log_files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "oldest_log": (
                min([f.stat().st_mtime for f in log_files]) if log_files else None
            ),
            "newest_log": (
                max([f.stat().st_mtime for f in log_files]) if log_files else None
            ),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日志统计失败: {str(e)}")
