from __future__ import annotations

from typing import Any, Dict, Optional
import time

from app.adapters.db.gateway import get_conn
import logging

_act = logging.getLogger(__name__)


def run_auto_baseline(
    settings,
    start: Optional[str] = None,
    end: Optional[str] = None,
    lookback_days: Optional[int] = None,
    station_id: Optional[int] = None,
    device_id: Optional[int] = None,
) -> Dict[str, Any]:
    """调用数据库过程刷新自动基线（仅库端过程）。
    - 优先使用新存储过程 sp_refresh_metric_rule_auto_baseline_win（带start/end参数）
    - 如果新存储过程不存在，回退到旧存储过程（带lookback_days参数）
    """
    _act.info(
        "[流程-开始] [自动基线生成A]",
        extra={
            "extra_data": {
                "start": start,
                "end": end,
                "lookback_days": lookback_days,
                "station_id": station_id,
                "device_id": device_id,
            }
        },
    )

    payload: Dict[str, Any] = {
        "ok": False,
        "start": start,
        "end": end,
        "lookback_days": lookback_days,
        "station_id": station_id,
        "device_id": device_id,
        "affected": None,
    }

    t0 = time.perf_counter()
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # 检查新存储过程是否存在
            _act.info("[数据库-查询] 检查新存储过程是否存在")
            cur.execute(
                "SELECT proname FROM pg_proc WHERE proname = 'sp_refresh_metric_rule_auto_baseline_win'"
            )
            has_win_proc = cur.fetchone() is not None
            _act.info(
                "[数据库-查询] 存储过程检查完成",
                extra={"has_win_proc": has_win_proc},
            )

            # 适当增加语句超时，避免长窗口超时
            try:
                cur.execute("SET LOCAL statement_timeout TO '600000ms'")
            except Exception:
                pass

            if has_win_proc and start and end:
                # 使用新存储过程（带start/end参数）
                _act.info(
                    "[数据库-执行] 调用新存储过程（带时间窗口）",
                    extra={"proc": "sp_refresh_metric_rule_auto_baseline_win"},
                )
                cur.execute(
                    "CALL public.sp_refresh_metric_rule_auto_baseline_win(%s,%s,%s,%s)",
                    (start, end, station_id, device_id),
                )
            else:
                # 回退到旧存储过程（带lookback_days参数）
                if not lookback_days:
                    lookback_days = 30  # 默认值
                _act.info(
                    "[数据库-执行] 调用旧存储过程（带lookback_days）",
                    extra={
                        "proc": "sp_refresh_metric_rule_auto_baseline",
                        "lookback_days": lookback_days,
                    },
                )
                cur.execute(
                    "CALL public.sp_refresh_metric_rule_auto_baseline(%s,%s,%s)",
                    (lookback_days, station_id, device_id),
                )

        # 提交事务，确保数据持久化
        conn.commit()

    cost_ms = int((time.perf_counter() - t0) * 1000)
    _act.info(
        "[流程-完成] [自动基线生成A]",
        extra={"extra_data": {"duration_ms": cost_ms}},
    )

    payload.update({"ok": True, "affected": None})
    return payload
