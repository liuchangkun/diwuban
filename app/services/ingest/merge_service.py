from __future__ import annotations

"""
集合式合并（ingest.merge_service）
- merge_window：支持分段合并（segmented.enabled），统计 affected_rows/rows_input/... 并输出 align.merge.window 事件
- _parse_granularity/_split_window：解析粒度与切片窗口
"""


import logging
from datetime import datetime, timedelta

# 延迟导入 DB 网关，避免在无 psycopg 环境下导入失败（仅运行时需要）
from typing import Any, Dict, cast

from app.core.config.loader import Settings
from app.core.types import MergeStats
from app.utils.logging_decorators import (
    business_logger,
    log_key_metrics,
    create_internal_step_logger,
)

logger = logging.getLogger(__name__)


def _parse_granularity(spec: str) -> int:
    """将 '30m'/'1h' 等规格转换为秒数（默认 1h）。非法输入回退为 3600。"""
    s = (spec or "1h").strip().lower()
    if s.endswith("m"):
        return max(60, int(s[:-1]) * 60)
    if s.endswith("h"):
        return max(3600, int(s[:-1]) * 3600)
    # 默认 1h
    return 3600


def _split_window(
    start: datetime, end: datetime, step_seconds: int
) -> list[tuple[datetime, datetime]]:
    """按步长切分 [start,end) 为若干窗口，最后一段不超过 end。"""
    out: list[tuple[datetime, datetime]] = []
    cur = start
    while cur < end:
        nxt = cur + timedelta(seconds=step_seconds)
        if nxt > end:
            nxt = end
        out.append((cur, nxt))
        cur = nxt
    return out


@business_logger("merge_window", enable_progress=True)
def merge_window(
    settings: Settings, window_start_utc: datetime, window_end_utc: datetime
) -> MergeStats:
    """执行一个 UTC 窗口的集合式合并。
    - 支持分段合并（settings.merge.segmented.enabled）按 granularity 切片执行
    - 统一输出 align.merge.window 事件，字段：window_start/window_end/segmented/granularity/
      affected_rows/rows_input/rows_deduped/rows_merged/dedup_ratio/sql_cost_ms（如存在）
    - 返回 MergeStats：与上面字段一致（部分字段可能不存在）
    """
    # 创建内部步骤日志记录器
    step_logger = create_internal_step_logger("merge_window", logger, settings)

    # 使用普通字典累加，末尾再 cast 为 MergeStats，避免 TypedDict 的字面量键限制
    stats: Dict[str, Any] = {}

    step_logger.step("解析合并配置")
    enabled = (
        getattr(settings.merge, "segmented", None) and settings.merge.segmented.enabled
    )
    gran = (
        getattr(settings.merge, "segmented", None)
        and settings.merge.segmented.granularity
        or "1h"
    )
    step = _parse_granularity(str(gran))

    step_logger.step(
        "合并参数确定",
        result=f"分段模式: {enabled}, 粒度: {gran}",
        segmented=enabled,
        granularity=gran,
        step_seconds=step,
    )

    # 记录合并开始信息
    log_key_metrics(
        "合并窗口开始",
        {
            "window_start": window_start_utc.isoformat(),
            "window_end": window_end_utc.isoformat(),
            "segmented_enabled": enabled,
            "granularity": gran,
            "step_seconds": step,
        },
        logger,
    )

    # 运行时导入，避免测试工具函数时强依赖 psycopg
    from app.adapters.db.gateway import get_conn, run_merge_window

    with get_conn(settings) as conn:
        if enabled:
            from datetime import timezone

            # 确保时间带 tzinfo
            s = window_start_utc
            e = window_end_utc
            if s.tzinfo is None:
                s = s.replace(tzinfo=timezone.utc)
            if e.tzinfo is None:
                e = e.replace(tzinfo=timezone.utc)
            for seg_s, seg_e in _split_window(s, e, step):
                r = run_merge_window(
                    conn,
                    start_utc=seg_s,
                    end_utc=seg_e,
                    default_station_tz=settings.merge.tz.default_station_tz,
                )
                r = cast(Dict[str, Any], r)
                # 统一键名：rows_in → rows_input
                for k_src, k_dst in (
                    ("affected_rows", "affected_rows"),
                    ("rows_in", "rows_input"),
                    ("rows_deduped", "rows_deduped"),
                    ("rows_merged", "rows_merged"),
                    ("sql_cost_ms", "sql_cost_ms"),
                ):
                    stats[k_dst] = int(stats.get(k_dst, 0)) + int(r.get(k_src, 0) or 0)
                if stats.get("rows_input"):
                    stats["dedup_ratio"] = stats.get("rows_deduped", 0) / max(
                        1, int(stats.get("rows_input", 0))
                    )
        else:
            r = run_merge_window(
                conn,
                start_utc=window_start_utc,
                end_utc=window_end_utc,
                default_station_tz=settings.merge.tz.default_station_tz,
            )
            # 非分段模式直接赋值统计
            if isinstance(r, dict):
                for k_src, k_dst in (
                    ("affected_rows", "affected_rows"),
                    ("rows_in", "rows_input"),
                    ("rows_deduped", "rows_deduped"),
                    ("rows_merged", "rows_merged"),
                    ("sql_cost_ms", "sql_cost_ms"),
                ):
                    stats[k_dst] = int(r.get(k_src, 0) or 0)
                if stats.get("rows_input"):
                    stats["dedup_ratio"] = stats.get("rows_deduped", 0) / max(
                        1, int(stats.get("rows_input", 0))
                    )
    # 对齐事件输出：补充影响行数与去重比指标
    extra_payload = {
        "window_start": window_start_utc.isoformat() + "Z",
        "window_end": window_end_utc.isoformat() + "Z",
        "segmented": bool(enabled),
        "granularity": str(gran),
    }
    for k_src, k_dst in (
        ("affected_rows", "affected_rows"),
        ("rows_input", "rows_input"),
        ("rows_deduped", "rows_deduped"),
        ("rows_merged", "rows_merged"),
        ("dedup_ratio", "dedup_ratio"),
        ("sql_cost_ms", "sql_cost_ms"),
    ):
        if k_src in stats:
            extra_payload[k_dst] = stats[k_src]

    logger.info(
        "合并完成",
        extra={"event": "align.merge.window", "extra": extra_payload},
    )

    # 记录合并结果指标
    log_key_metrics(
        "合并窗口完成",
        {
            "affected_rows": stats.get("affected_rows", 0),
            "rows_input": stats.get("rows_input", 0),
            "rows_merged": stats.get("rows_merged", 0),
            "rows_deduped": stats.get("rows_deduped", 0),
            "dedup_ratio": round(stats.get("dedup_ratio", 0), 4),
            "sql_cost_ms": stats.get("sql_cost_ms", 0),
            "segmented": enabled,
            "granularity": gran,
        },
        logger,
    )

    return cast(MergeStats, stats)
