from __future__ import annotations

"""
集合式合并（ingest.merge_service）
- merge_window：支持分段合并（segmented.enabled），统计 affected_rows/rows_input/... 并输出 align.merge.window 事件
- _parse_granularity/_split_window：解析粒度与切片窗口
"""


import time
import logging

_act = logging.getLogger("activity")

from datetime import datetime, timedelta

# 延迟导入 DB 网关，避免在无 psycopg 环境下导入失败（仅运行时需要）
from typing import Any, Dict, cast

from app.core.config.loader_new import Settings
from app.core.types import MergeStats


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


def merge_window(
    settings: Settings,
    window_start_utc: datetime,
    window_end_utc: datetime,
    device_id: int | None = None,
) -> MergeStats:
    """执行一个 UTC 窗口的集合式合并。
    - 支持分段合并（settings.merge.segmented.enabled）按 granularity 切片执行
    - 统一输出 align.merge.window 事件，字段：window_start/window_end/segmented/granularity/
      affected_rows/rows_input/rows_deduped/rows_merged/dedup_ratio/sql_cost_ms（如存在）
    - 返回 MergeStats：与上面字段一致（部分字段可能不存在）
    """
    t0 = time.perf_counter()
    _act.info(
        "[流程-开始] [数据合并]",
        extra={
            "extra_data": {
                "window_start_utc": window_start_utc.isoformat(),
                "window_end_utc": window_end_utc.isoformat(),
                "device_id": device_id,
            }
        },
    )

    # 使用普通字典累加，末尾再 cast 为 MergeStats，避免 TypedDict 的字面量键限制
    stats: Dict[str, Any] = {}

    enabled = (
        getattr(settings.merge, "segmented", None) and settings.merge.segmented.enabled
    )
    gran = (
        getattr(settings.merge, "segmented", None)
        and settings.merge.segmented.granularity
        or "1h"
    )
    step = _parse_granularity(str(gran))

    # 运行时导入，避免测试工具函数时强依赖 psycopg
    from app.adapters.db.connection_lease import LeaseConfig, lease_connection
    from app.adapters.db.gateway import get_conn, run_merge_window

    # 配置连接租借参数，针对长时间运行的合并操作
    lease_config = LeaseConfig(
        max_lease_time=180.0,  # 3分钟租借时间，适合合并操作
        renewal_threshold=0.7,  # 70%时间后自动续租
        batch_size=1000,
        max_batch_time=60.0,  # 单个合并操作最大1分钟
    )

    if enabled:
        # 分段合并模式：使用连接租借机制避免长时间占用连接
        _act.info(
            "[流程-阶段] [分段合并模式]",
            extra={"extra_data": {"granularity": str(gran), "step_seconds": step}},
        )

        with lease_connection(settings, lease_config) as lease:
            from datetime import timezone

            # 确保时间带 tzinfo

            s = window_start_utc
            e = window_end_utc
            if s.tzinfo is None:
                s = s.replace(tzinfo=timezone.utc)
            if e.tzinfo is None:
                e = e.replace(tzinfo=timezone.utc)

            segments = list(_split_window(s, e, step))
            total_segments = len(segments)

            _act.info(
                "[流程-阶段] [窗口已切分]",
                extra={
                    "extra_data": {
                        "total_segments": total_segments,
                        "step_seconds": step,
                    }
                },
            )

            for idx, (seg_s, seg_e) in enumerate(segments):
                _act.info(
                    "[流程-阶段] [分段处理]",
                    extra={
                        "extra_data": {
                            "segment_index": idx + 1,
                            "total_segments": total_segments,
                            "segment_start": seg_s.isoformat(),
                            "segment_end": seg_e.isoformat(),
                        }
                    },
                )
                with lease.get_connection() as conn:
                    r = run_merge_window(
                        conn,
                        start_utc=seg_s,
                        end_utc=seg_e,
                        default_station_tz=settings.merge.tz.default_station_tz,
                        device_id=device_id,
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
                        stats[k_dst] = int(stats.get(k_dst, 0)) + int(
                            r.get(k_src, 0) or 0
                        )

                    if stats.get("rows_input"):
                        stats["dedup_ratio"] = stats.get("rows_deduped", 0) / max(
                            1, int(stats.get("rows_input", 0))
                        )

    else:
        # 单次合并模式：使用普通连接
        _act.info("[流程-阶段] [单次合并模式]")
        with get_conn(settings) as conn:
            r = run_merge_window(
                conn,
                start_utc=window_start_utc,
                end_utc=window_end_utc,
                default_station_tz=settings.merge.tz.default_station_tz,
                device_id=device_id,
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

    dur_ms = int((time.perf_counter() - t0) * 1000)
    _act.info(
        "[流程-完成] [数据合并]",
        extra={
            "extra_data": {
                "segmented": bool(enabled),
                "granularity": str(gran),
                "duration_ms": dur_ms,
                "affected_rows": int(stats.get("affected_rows", 0) or 0),
                "rows_input": int(stats.get("rows_input", 0) or 0),
                "rows_deduped": int(stats.get("rows_deduped", 0) or 0),
                "rows_merged": int(stats.get("rows_merged", 0) or 0),
                "dedup_ratio": stats.get("dedup_ratio", 0.0),
            }
        },
    )

    return cast(MergeStats, stats)
