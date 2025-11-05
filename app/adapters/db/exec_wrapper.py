from __future__ import annotations

"""
轻量级 DB 执行包装（默认关闭）。
- 目的：当启用时，自动识别“数据库函数/视图”的查询，在不改变现有业务代码的情况下，追加中文业务日志：log_db_function/log_db_view。
- 安全：仅包裹 cursor.execute / executemany，其他方法直接透传；不主动 fetch，避免额外 IO；开销极小（字符串预处理+一次正则）。
- 开关：通过环境变量 APP_DB_AUTO_LOG=true/1/yes 启用。
"""

import os
import re
import time
from typing import Any, Optional

try:
    from psycopg import Connection as _PsyConn  # type: ignore
    from psycopg import Cursor as _PsyCursor  # type: ignore
except Exception:  # pragma: no cover
    _PsyConn = object  # type: ignore
    _PsyCursor = object  # type: ignore

import logging

_act = logging.getLogger(__name__)


_ENABLE = os.getenv("APP_DB_AUTO_LOG", "false").lower() in {"1", "true", "yes"}

# 识别 FROM 子句中的“表函数”与“视图”。仅对 FROM ...(<args>) 识别为函数；对 FROM ... 不带括号且命名类似 v_* 或 *_view 识别为视图。
_RE_FROM_FN = re.compile(r"from\s+([a-z0-9_.]+)\s*\(")  # e.g., FROM public.fn_xxx( ...
_RE_FROM_OBJ = re.compile(r"from\s+([a-z0-9_.]+)\b")      # e.g., FROM public.v_xxx ...


def _normalize_sql(sql: str) -> str:
    s = sql.strip().lower()
    # 合并空白，去掉多余换行，便于 regex
    s = " ".join(s.split())
    return s


def _guess_db_object(sql: str) -> tuple[Optional[str], Optional[str]]:
    """返回 (kind, name)，kind in {"func","view"}。
    仅在能够较为确定时返回；否则 (None, None)。
    """
    s = _normalize_sql(sql)
    # 函数（表函数）：FROM schema.fn_xxx(...)
    m = _RE_FROM_FN.search(s)
    if m:
        return "func", m.group(1)

    # 视图：FROM schema.v_xxx 或 *_view（不带括号）
    m2 = _RE_FROM_OBJ.search(s)
    if m2:
        name = m2.group(1)
        base = name.split(".")[-1]
        if base.startswith("v_") or base.endswith("_view"):
            return "view", name

    return None, None


class LoggingCursor:
    def __init__(self, inner: _PsyCursor):
        self._cur = inner

    # 透传未知属性（如 copy、description 等）
    def __getattr__(self, item):  # pragma: no cover - 简单透传
        return getattr(self._cur, item)

    # 上下文协议透传
    def __enter__(self):
        self._cur.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._cur.__exit__(exc_type, exc_val, exc_tb)

    # 拦截 execute / executemany
    def execute(self, sql: str, params: Any | None = None):
        t0 = time.perf_counter()
        try:
            return self._cur.execute(sql, params)
        finally:
            cost_ms = int((time.perf_counter() - t0) * 1000)
            kind, name = _guess_db_object(sql)
            if not name:
                return
            try:
                if kind == "func":
                    args = None
                    if isinstance(params, dict):
                        # 仅采集常见关键键，避免大对象
                        keys = [
                            "station_id",
                            "station_ids",
                            "device_id",
                            "device_ids",
                            "metric_id",
                            "metric_ids",
                            "start_ts",
                            "end_ts",
                        ]
                        args = {k: params.get(k) for k in keys if k in params}
                    _act.info(
                        "[数据库-执行] 数据库函数调用",
                        extra={"extra_data": {"function": name, "args": args, "duration_ms": cost_ms}},
                    )
                elif kind == "view":
                    filters = None
                    if isinstance(params, dict):
                        # 与上同，采集轻量参数
                        keys = ["station_id", "station_ids", "device_id", "start_ts", "end_ts"]
                        filters = {k: params.get(k) for k in keys if k in params}
                    _act.info(
                        "[数据库-查询] 视图查询",
                        extra={"extra_data": {"view": name, "filters": filters, "duration_ms": cost_ms}},
                    )
            except Exception:
                # 日志失败不影响主流程
                pass

    def executemany(self, sql: str, seq_of_params):
        t0 = time.perf_counter()
        try:
            return self._cur.executemany(sql, seq_of_params)
        finally:
            cost_ms = int((time.perf_counter() - t0) * 1000)
            kind, name = _guess_db_object(sql)
            if not name:
                return
            try:
                if kind == "func":
                    log_db_function(name, args=None, duration_ms=cost_ms, rows=None)
                elif kind == "view":
                    log_db_view(name, filters=None, duration_ms=cost_ms, rows=None)
            except Exception:
                pass


class ProxyConnection:
    """连接代理：仅重写 cursor() 返回 LoggingCursor，其他方法透传。"""

    def __init__(self, inner: _PsyConn):
        self._conn = inner

    def __getattr__(self, item):  # pragma: no cover
        return getattr(self._conn, item)

    def cursor(self, *args, **kwargs) -> LoggingCursor:
        cur = self._conn.cursor(*args, **kwargs)
        return LoggingCursor(cur)


def wrap_connection_if_enabled(conn: _PsyConn):
    """如果开启了 APP_DB_AUTO_LOG，则返回代理连接，否则原样返回。"""
    if not _ENABLE:
        return conn
    try:
        _act.info("[核心-连接] [数据库连接包装启用]")
        return ProxyConnection(conn)
    except Exception:
        return conn

