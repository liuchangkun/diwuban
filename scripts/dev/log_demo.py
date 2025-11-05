# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import sys
from pathlib import Path

# 确保仓库根在 sys.path 中
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.logging.setup import (
    init_logging,
    log_activity,
    log_biz,
    log_sql,
    set_context,
    clear_context,
)


def main() -> None:
    # 初始化日志（使用 configs/logging.yaml）
    init_logging("configs", "Asia/Shanghai")

    # 注入上下文信息
    set_context(
        request_id="req-123", trace_id="trace-abc", user_id="u-42", tenant="t-1"
    )

    logger = logging.getLogger(__name__)

    # 1) DEBUG 与 INFO 基本日志
    logger.debug(
        "调试信息：将进行演示", extra={"extra_data": {"feature": "log_demo", "case": 1}}
    )
    logger.info("开始演示", extra={"extra_data": {"phase": "start"}})

    # 2) 方案A：自动采集参数/返回值
    from app.core.logging.setup import call_with_activity

    def add(x, y):
        return x + y

    result = call_with_activity("demo.add", add, 1, 2)
    logger.info(
        "过程：校验参数",
        extra={"extra_data": {"类型": "步骤", "step": "validate", "ok": True}},
    )

    # 3) SQL 执行日志（成功）
    log_sql(
        "SELECT * FROM public.dim_stations WHERE id=%(id)s",
        params={"id": 1},
        duration_ms=12,
        rows=1,
    )

    # 4) SQL 执行日志（失败示例）- 受环境变量 LOG_DEMO_ERROR 控制，默认关闭
    import os

    if os.getenv("LOG_DEMO_ERROR", "false").lower() in {"1", "true", "yes"}:
        log_sql(
            "SELECT * FROM public.unknown_table WHERE id=%(id)s",
            params={"id": 2},
            duration_ms=3,
            rows=None,
            error='relation "public.unknown_table" does not exist',
        )

    # 5) 业务事件日志
    log_biz("order.create", status="ok", detail={"order_id": "O123", "amount": 99.9})

    # 6) 异常与堆栈（捕获并记录）
    try:
        raise ValueError("示例异常：非法参数")
    except Exception:
        logger.exception("发生异常并记录堆栈")

    logger.info("演示结束", extra={"extra_data": {"phase": "end"}})

    clear_context()


if __name__ == "__main__":
    main()
