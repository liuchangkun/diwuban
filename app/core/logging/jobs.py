# -*- coding: utf-8 -*-
"""
轻量作业运行器：统一记录 job_id / attempt / 重试策略 / 状态流转
- 复用现有 call_with_activity，实现进入/退出/错误的一致性
- 提供重试包装与指数退避（可由上层调度器控制调用）
"""
from __future__ import annotations

import time
import logging
from typing import Any, Callable, Optional

from app.core.logging.setup import call_with_activity, log_biz, _global_cfg


def run_job(
    job_name: str,
    func: Callable[..., Any],
    *args,
    job_id: Optional[str] = None,
    attempt: int = 1,
    max_attempts: int = 1,
    backoff_ms: int = 0,
    jitter_ms: int = 0,
    next_run_ts: Optional[float] = None,
    retryable: bool = True,
    **kwargs,
) -> Any:
    """运行一次作业，并记录统一日志。

    - 进入：[进入] job_name（携带 job_id/attempt/max_attempts/计划时间等）
    - 过程：可在业务中 logger.info("[步骤] ...") 或使用 call_with_activity 内的 span 机制
    - 退出/错误：由 call_with_activity 统一输出
    - 返回：同样自动记录
    """
    logger = logging.getLogger("job")

    # 进入前透出一次“计划”状态，便于追踪排队与触发
    logger.info(
        "[业务] %s scheduled",
        job_name,
        extra={
            "extra_data": {
                "类型": "业务",
                "action": job_name,
                "status": "scheduled",
                "detail": {
                    "job_id": job_id,
                    "attempt": attempt,
                    "max_attempts": max_attempts,
                    "next_run_ts": next_run_ts,
                },
            }
        },
    )

    # running 状态
    log_biz(job_name, status="running", detail={"job_id": job_id, "attempt": attempt})

    # 运行：复用 call_with_activity，统一参数/返回值采集与异常输出
    def _invoke():
        return func(*args, **kwargs)

    try:
        res = call_with_activity(job_name, _invoke)
        log_biz(
            job_name,
            status="succeeded",
            detail={"job_id": job_id, "attempt": attempt, "max_attempts": max_attempts},
        )
        return res
    except Exception as e:
        # 失败记录
        log_biz(
            job_name,
            status="failed",
            detail={
                "job_id": job_id,
                "attempt": attempt,
                "max_attempts": max_attempts,
                "error": str(e),
            },
        )
        # 重试决策日志（配置驱动，仅示意，不实际调度）
        if _global_cfg and _global_cfg.jobs_retry_enabled and attempt < max_attempts:
            # 简单指数退避（仅用于日志展示；真正调度由上层控制）
            delay = backoff_ms * (2 ** max(0, attempt - 1)) + jitter_ms
            detail = {
                "job_id": job_id,
                "attempt": attempt,
                "next_attempt": attempt + 1,
                "max_attempts": max_attempts,
                "delay_ms": delay,
            }
            if _global_cfg.jobs_retry_include_policy:
                detail.update(
                    {
                        "policy": "exponential",
                        "base_backoff_ms": backoff_ms,
                        "jitter_ms": jitter_ms,
                    }
                )
            log_biz(job_name, status="retry", detail=detail)
        raise
