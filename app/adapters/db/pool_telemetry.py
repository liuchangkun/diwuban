from __future__ import annotations
"""
轻量连接池回退/错误遥测（进程内）
- 记录：
  - fallback_count: 因 ImportError/未初始化等原因触发的回退次数
  - error_count: 连接池已初始化但发生故障的错误次数
  - last_fallback_ts / last_error_ts: 最近一次时间戳（epoch 秒）
- 线程安全：使用简单的锁保护计数与时间字段
- 开销极小，只在事件发生时自增
"""

import threading
import time
from typing import Dict, Any
import logging

_act = logging.getLogger(__name__)

_lock = threading.Lock()
_fallback_count = 0
_error_count = 0
_last_fallback_ts: float | None = None
_last_error_ts: float | None = None


def record_fallback(reason: str | None = None) -> None:
    global _fallback_count, _last_fallback_ts
    with _lock:
        _fallback_count += 1
        _last_fallback_ts = time.time()

    _act.warning(
        "[核心-连接池] [回退触发]",
        extra={"extra_data": {"reason": reason or "unknown", "count": _fallback_count}},
    )


def record_error(reason: str | None = None) -> None:
    global _error_count, _last_error_ts
    with _lock:
        _error_count += 1
        _last_error_ts = time.time()


def snapshot() -> Dict[str, Any]:
    with _lock:
        return {
            "fallback_count": _fallback_count,
            "error_count": _error_count,
            "last_fallback_ts": _last_fallback_ts,
            "last_error_ts": _last_error_ts,
        }

