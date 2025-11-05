# -*- coding: utf-8 -*-
"""
端到端日志功能演示：
- 初始化
- call_with_activity（快/慢）
- 作业运行器：成功/失败+重试日志
- SQL：慢+EXPLAIN，快SQL
- 出站HTTP / 缓存 / 事务
运行：python scripts/dev/log_e2e.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# ensure repo root
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


import time

from app.core.logging.jobs import run_job
from app.core.logging.setup import (
    call_with_activity,
    init_logging,
    log_biz,
    log_cache,
    log_http_out,
    log_sql,
    log_tx,
)


def _demo_ok():
    time.sleep(0.05)
    return [1, 2, 3, 4, 5]


def _demo_slow():
    time.sleep(0.25)  # 触发 activity.step_slow_ms=200 的慢标记
    return {"ok": True}


def _job_ok():
    return {"ok": 1}


def _job_fail():
    """失败演示，受环境变量 LOG_E2E_JOB_FAIL 控制（默认关闭）。"""
    import os

    if os.getenv("LOG_E2E_JOB_FAIL", "false").lower() in {"1", "true", "yes"}:
        raise ValueError("boom")
    return {"skipped": True}


def main() -> None:
    init_logging("configs", "Asia/Shanghai")

    # 业务事件示范
    log_biz("order.create", status="ok", detail={"id": 1001})

    # 函数过程（快/慢）
    call_with_activity("demo.ok", _demo_ok)
    call_with_activity("demo.slow", _demo_slow)

    # 作业状态流转：失败+重试提示、成功
    try:
        run_job(
            "job.retry",
            _job_fail,
            job_id="J1",
            attempt=1,
            max_attempts=2,
            backoff_ms=100,
            jitter_ms=10,
        )
    except Exception:
        pass
    run_job("job.ok", _job_ok, job_id="J2", attempt=1, max_attempts=1)

    # SQL：慢+EXPLAIN（仅 SELECT）、快SQL
    def _explain(sql: str, params: dict, timeout_ms: int = 200):
        return "EXPLAIN PLAN ..."

    log_sql(
        "select * from t where id=%s",
        params={"id": 1, "__explain_func__": _explain},
        duration_ms=1500,
        rows=1,
    )
    log_sql(
        "update t set x=1 where id=%s",
        params={"id": 1},
        duration_ms=10,
        rows=0,
    )

    # HTTP 出站 / 缓存 / 事务（配置已启用）
    log_http_out(
        "GET",
        "https://api.example.com/items",
        status=200,
        host="api.example.com",
        duration_ms=123,
        req_headers={"authorization": "xxx", "x-req": "1"},
        resp_bytes=456,
    )
    log_cache(
        "GET",
        key_hash="k:abc",
        hit=False,
        duration_ms=25,
        bytes=128,
        ttl=60,
        reason="miss",
    )
    log_tx("BEGIN", tx_id="tx123")
    log_tx("ROLLBACK", tx_id="tx123", error="deadlock")


if __name__ == "__main__":
    main()
