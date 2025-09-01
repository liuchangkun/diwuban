from __future__ import annotations

"""
并发 COPY 导入（ingest.copy_workers）
- 从 mapping.json 收集文件清单，生成 ValidRow/RejectRow
- 按批 COPY 到 staging_raw，记录 perf 与 backpressure 事件
- 失败与拒绝行写入 staging_rejects，过程日志均为结构化 JSON

注意：
- 不改变业务逻辑，仅补充中文注释与 Docstring；采样/背压策略详见 BackpressureController
- 事件：ingest.load.begin/progress/end、ingest.copy.batch、backpressure.enter/exit
"""


import json
import logging
import time
from pathlib import Path
from typing import Iterable, Iterator, List

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:
    pass  # type: ignore[no-redef]


from app.adapters.db.gateway import (
    copy_valid_lines,
    create_staging_if_not_exists,
    get_conn,
    insert_rejects,
)
from app.adapters.fs.reader import iter_rows
from app.core.config.loader import Settings
from app.core.types import CopyStats, RejectRow, ValidRow
from app.services.ingest.backpressure import BackpressureController
from app.services.ingest.source_hint import make_source_hint
from app.utils.logging_ext import (
    EVENT_INGEST_COPY_BATCH,
    EventLogger,
    SamplingGate,
    get_event_sampling_rate,
    log_ingest_begin,
    log_ingest_end,
    log_ingest_progress,
)
from app.utils.logging_decorators import (
    business_logger,
    file_operation_logger,
    data_processing_logger,
    create_progress_logger,
    log_key_metrics,
    create_internal_step_logger,
    log_data_quality_check,
)

# 性能日志记录器（与业务日志分离便于分析）
perf_logger = logging.getLogger("perf")
logger = logging.getLogger(__name__)


def _ensure_staging(settings: Settings) -> None:
    """确保 staging 表存在（幂等），仅在任务开始时调用一次。"""
    with get_conn(settings) as conn:
        create_staging_if_not_exists(conn)


@file_operation_logger()
def _collect_files_from_mapping(
    mapping_path: Path, base_dir: Path
) -> Iterator[tuple[str, str, str, Path]]:
    """读取 mapping.json，产出 (station_name, device_name, metric_key, csv_path)。"""
    data = json.loads(mapping_path.read_text(encoding="utf-8"))
    stations = data.get("stations") or []
    for s in stations:
        station_name = str(s.get("name") or "").strip()
        for d in s.get("devices", []) or []:
            device_name = str(d.get("name") or "").strip()

            for m in d.get("metrics", []) or []:

                metric_key = str(m.get("key") or "").strip()
                for rel in m.get("files", []) or []:
                    p = base_dir / str(rel)
                    yield station_name, device_name, metric_key, p


@data_processing_logger()
def _valid_rows_for_file(
    csv_path: Path, station: str, device: str, metric_key: str, settings: Settings
) -> Iterator[ValidRow | RejectRow]:
    """基于 csv 文件生成 ValidRow/RejectRow，填充站点/设备/指标与 source_hint。"""
    base_dir = Path(settings.ingest.base_dir)
    source_hint = make_source_hint(settings, base_dir, csv_path)
    csv_cfg = settings.ingest.csv
    perf_cfg = settings.ingest.performance
    for r in iter_rows(
        csv_path,
        source_hint,
        delimiter=csv_cfg.delimiter,
        encoding=csv_cfg.encoding,
        quote_char=csv_cfg.quote_char,
        escape_char=csv_cfg.escape_char,
        allow_bom=csv_cfg.allow_bom,
        read_buffer_size=perf_cfg.read_buffer_size,
    ):
        if isinstance(r, ValidRow):
            # 时区归一化逻辑
            dt_str = r.DataTime
            normalized_dt_str = dt_str
            # 保留原始时间字符串，避免在 COPY 阶段进行时区转换（否则在 MERGE 阶段会二次转换）
            # 仅做轻量清洗，交由 MERGE SQL 结合站点时区统一转换为 UTC 秒级对齐
            try:
                normalized_dt_str = dt_str.strip()
            except Exception:
                normalized_dt_str = dt_str

            yield ValidRow(
                station_name=station,
                device_name=device,
                metric_key=metric_key,
                TagName=r.TagName,
                DataTime=normalized_dt_str,  # 使用归一化后的时间
                DataValue=r.DataValue,
                source_hint=source_hint,
            )
        else:
            yield r


def _lines_from_valid_rows(rows: Iterable[ValidRow]) -> Iterator[str]:
    """将 ValidRow 转为 COPY 所需 CSV 行（无表头）。"""
    for r in rows:
        vals = [
            r.station_name,
            r.device_name,
            r.metric_key,
            r.TagName,
            r.DataTime,
            r.DataValue,
            r.source_hint,
        ]
        out: list[str] = []
        for v in vals:
            v = v if v is not None else ""
            if ("," in v) or ('"' in v):
                out.append('"' + v.replace('"', '""') + '"')
            else:
                out.append(v)
        yield ",".join(out) + "\n"


def _p95(costs: List[int]) -> int:
    """取 P95（向下取整索引），用于背压判定。空列表返回 0。"""
    if not costs:
        return 0
    arr = sorted(costs)
    idx = max(0, int(len(arr) * 0.95) - 1)
    return arr[idx]


@business_logger("copy_from_mapping", enable_progress=True)
def copy_from_mapping(
    settings: Settings, mapping_path: Path, run_id: str | None = None
) -> CopyStats:
    """从 mapping.json 并发导入 CSV 到 staging。
    - 步骤：
      1) _ensure_staging：确保 staging 表存在
      2) 读取 mapping.json → 收集文件路径
      3) 逐文件：构造 ValidRow/RejectRow → 批量 COPY → 采样日志 → 背压判定
      4) 拒绝行写入 staging_rejects
    - 结构化事件：
      - ingest.load.begin/progress/end（root 日志）
      - ingest.copy.batch（perf 日志）
      - backpressure.enter/exit（perf 日志）
      - ingest.copy.failed（root 日志）
    - 参数：
      - settings：全局配置（含采样/批大小/工作线程数等）
      - mapping_path：映射文件路径（JSON）
      - run_id：可选；若提供将注入到 settings 作为 _runtime_run_id，参与 source_hint 生成
    - 返回：CopyStats 统计（文件总数/成功/失败、读取/加载/拒绝的行数、读取字节数等）
    """
    # 创建内部步骤日志记录器
    step_logger = create_internal_step_logger("copy_from_mapping", logger, settings)
    
    step_logger.step("初始化导入环境")
    base_dir = Path(settings.ingest.base_dir)
    _ensure_staging(settings)

    # 设置运行期 run_id 到 settings（进程内）
    if run_id:
        step_logger.step("设置运行标识符", run_id=run_id)
        # 为避免 dataclass frozen，使用 object.__setattr__ 临时挂到对象上（仅 runtime 使用）
        object.__setattr__(settings, "_runtime_run_id", run_id)
        object.__setattr__(settings.ingest, "_runtime_run_id", run_id)
        
    step_logger.step("收集文件清单")
    files = list(_collect_files_from_mapping(mapping_path, base_dir))
    step_logger.step("文件清单收集完成", result=f"共发现 {len(files)} 个文件")
    stats: CopyStats = {
        "files_total": len(files),
        "files_succeeded": 0,
        "files_failed": 0,
        "rows_read": 0,
        "rows_loaded": 0,
        "rows_rejected": 0,
        "bytes_read": 0,
    }
    # 诊断聚合（背压与批耗时，整次 run）
    run_diag = {"bp_enter": 0, "bp_exit": 0, "p95_samples": []}

    if not files:
        step_logger.branch("文件数量检查", False, "未找到任何文件")
        from app.utils.logging_ext import EVENT_INGEST_PATH_RESOLVE

        logger.warning(
            "未找到任何文件（严格路径，无自适配）",
            extra={"event": EVENT_INGEST_PATH_RESOLVE, "extra": {"not_found": True}},
        )

        # 无文件可处理，直接返回统计
        return stats
    
    step_logger.branch("文件数量检查", True, f"发现 {len(files)} 个文件")
    
    step_logger.step("初始化背压控制器")
    # 控制器与状态
    ctrl = BackpressureController(
        batch_size=settings.ingest.commit_interval,
        workers=settings.ingest.workers,
        settings=settings,
    )
    in_backpressure = False
    file_costs: List[int] = []
    
    step_logger.checkpoint("file_processing_start", {
        "total_files": len(files),
        "batch_size": ctrl.batch_size,
        "workers": settings.ingest.workers
    })

    # 创建文件处理迭代器
    file_iterator = step_logger.iteration_start("文件处理循环", len(files))

    with get_conn(settings) as conn:
        for station, device, metric_key, path in files:
            if not path.exists():
                logger.error(
                    "文件不存在",
                    extra={
                        "event": "ingest.path.resolve",
                        "extra": {"path": str(path), "not_found": True},
                    },
                )
                stats["files_failed"] = stats.get("files_failed", 0) + 1
                continue

            rows_iter = list(
                _valid_rows_for_file(path, station, device, metric_key, settings)
            )
            valids = [r for r in rows_iter if isinstance(r, ValidRow)]
            rejects = [r for r in rows_iter if isinstance(r, RejectRow)]
            stats["rows_read"] = stats.get("rows_read", 0) + len(rows_iter)

            # ingest.load.begin（按文件）
            log_ingest_begin(
                EventLogger(logging.getLogger("root")),
                file_path=str(path),
                rows_total=len(rows_iter),
            )

            # 批次级 COPY 与背压：以固定批大小（初始取 commit_interval），输出每批 perf 指标
            if valids:
                try:
                    # 以 ingest.batch.size 优先，未设置则回退 commit_interval
                    batch_size = max(
                        1,
                        int(
                            getattr(settings.ingest.batch, "size", 0)
                            or settings.ingest.commit_interval
                        ),
                    )
                    file_started_epoch = time.time()
                    bytes_read = 0
                    gate = SamplingGate(
                        every_n=max(1, settings.logging.sampling.loop_log_every_n),
                        min_interval_sec=max(
                            0.0, float(settings.logging.sampling.min_interval_sec)
                        ),
                    )
                    for i in range(0, len(valids), batch_size):
                        batch = valids[i : i + batch_size]
                        lines = list(_lines_from_valid_rows(batch))
                        t0 = time.perf_counter()
                        loaded = copy_valid_lines(conn, lines)
                        cost_ms = int((time.perf_counter() - t0) * 1000)
                        stats["rows_loaded"] = stats.get("rows_loaded", 0) + loaded

                        # ingest.load.progress（采样节流）
                        batch_bytes = sum(len(line.encode("utf-8")) for line in lines)
                        bytes_read += batch_bytes
                        rows_done = i + len(batch)
                        log_ingest_progress(
                            EventLogger(logging.getLogger("root")),
                            gate,
                            rows_read=rows_done,
                            bytes_read=bytes_read,
                            batch_cost_ms=cost_ms,
                            started_ts=file_started_epoch,
                        )

                        # 背压判定（基于批次 P95 与数据质量失败率）
                        total = len(valids) + len(rejects)
                        fail_rate = (len(rejects) / total) if total else 0.0
                        k = max(1, int(settings.ingest.p95_window))
                        file_costs.append(cost_ms)
                        p95 = _p95(file_costs[-k:])
                        adj = ctrl.decide(p95_ms=p95, fail_rate=fail_rate)
                        if adj.get("action") in ("shrink_batch", "shrink_workers"):
                            if not in_backpressure:
                                in_backpressure = True
                                from app.utils.logging_ext import (
                                    EVENT_BACKPRESSURE_ENTER,
                                )

                                perf_logger.info(
                                    EVENT_BACKPRESSURE_ENTER,
                                    extra={
                                        "event": EVENT_BACKPRESSURE_ENTER,
                                        "extra": {
                                            "p95_batch_ms": p95,
                                            "p95_window": k,
                                            "batch_cost_ms": cost_ms,
                                            "rows_per_sec": round(
                                                (len(batch) / max(1, cost_ms)) * 1000.0,
                                                2,
                                            ),
                                            "fail_rate": fail_rate,
                                            "adjustment": adj,
                                        },
                                    },
                                )
                            if adj.get("action") == "shrink_batch" and adj.get(
                                "to_batch"
                            ):
                                batch_size = int(adj["to_batch"]) or batch_size
                        elif adj.get("action") == "recover" and in_backpressure:
                            in_backpressure = False
                            from app.utils.logging_ext import (
                                EVENT_BACKPRESSURE_EXIT,
                            )

                            perf_logger.info(
                                EVENT_BACKPRESSURE_EXIT,
                                extra={
                                    "event": EVENT_BACKPRESSURE_EXIT,
                                    "extra": {
                                        "p95_batch_ms": p95,
                                        "p95_window": k,
                                        "batch_cost_ms": cost_ms,
                                        "rows_per_sec": round(
                                            (len(batch) / max(1, cost_ms)) * 1000.0, 2
                                        ),
                                        "fail_rate": fail_rate,
                                    },
                                },
                            )
                    stats["files_succeeded"] = stats.get("files_succeeded", 0) + 1

                    # ingest.load.end（按文件）
                    total_cost = int((time.perf_counter() - t0) * 1000)
                    log_ingest_end(
                        EventLogger(logging.getLogger("root")),
                        rows_loaded=stats["rows_loaded"],
                        cost_ms=total_cost,
                    )
                except Exception:
                    logger.exception(
                        "COPY 失败",
                        extra={
                            "event": "ingest.copy.failed",
                            "extra": {"path": str(path)},
                        },
                    )
                    stats["files_failed"] = stats.get("files_failed", 0) + 1

            if rejects:
                # 错误阈值控制：超过 per-file 阈值或错误百分比阈值则计失败并跳过写入
                eh = settings.ingest.error_handling
                total = len(valids) + len(rejects)
                over_count = len(rejects) > int(eh.max_errors_per_file)
                over_percent = (
                    (len(rejects) / total) * 100.0 > float(eh.error_threshold_percent)
                    if total
                    else False
                )
                if over_count or over_percent:
                    from app.utils.logging_ext import EVENT_INGEST_ERROR_THRESHOLD

                    logger.error(
                        "错误超过阈值，跳过写入拒绝行",
                        extra={
                            "event": EVENT_INGEST_ERROR_THRESHOLD,
                            "extra": {
                                "rejects": len(rejects),
                                "total": total,
                                "over_count": over_count,
                                "over_percent": over_percent,
                            },
                        },
                    )
                    stats["files_failed"] = stats.get("files_failed", 0) + 1
                    if not eh.continue_on_error:
                        # 中断整个处理流程（当前实现为按文件循环，continue_on_error=False 时结束本文件）
                        pass
                else:
                    insert_rejects(conn, rejects)
                    stats["rows_rejected"] = stats.get("rows_rejected", 0) + len(
                        rejects
                    )

    with get_conn(settings) as conn:
        for station, device, metric_key, path in files:
            if not path.exists():
                from app.utils.logging_ext import EVENT_INGEST_PATH_RESOLVE

                logger.error(
                    "文件不存在",
                    extra={
                        "event": EVENT_INGEST_PATH_RESOLVE,
                        "extra": {"path": str(path), "not_found": True},
                    },
                )
                stats["files_failed"] = stats.get("files_failed", 0) + 1
                continue

            rows_iter = list(
                _valid_rows_for_file(path, station, device, metric_key, settings)
            )
            valids = [r for r in rows_iter if isinstance(r, ValidRow)]
            rejects = [r for r in rows_iter if isinstance(r, RejectRow)]
            stats["rows_read"] = stats.get("rows_read", 0) + len(rows_iter)

            # ingest.load.begin（按文件）
            log_ingest_begin(
                EventLogger(logging.getLogger("root")),
                file_path=str(path),
                rows_total=len(rows_iter),
            )

            if valids:
                try:
                    batch_size = max(1, ctrl.batch_size)
                    for i in range(0, len(valids), batch_size):
                        batch = valids[i : i + batch_size]
                        t0 = time.perf_counter()
                        loaded = copy_valid_lines(conn, _lines_from_valid_rows(batch))
                        cost_ms = int((time.perf_counter() - t0) * 1000)
                        rows_per_sec = (len(batch) / max(1, cost_ms)) * 1000.0

                        # 采样/节流的进度日志（结构化 JSON）
                        batch_lines = list(_lines_from_valid_rows(batch))
                        batch_bytes = sum(
                            len(line.encode("utf-8")) for line in batch_lines
                        )
                        stats["bytes_read"] = stats.get("bytes_read", 0) + batch_bytes
                        log_ingest_progress(
                            EventLogger(logging.getLogger("root")),
                            SamplingGate(
                                every_n=max(
                                    1, settings.logging.sampling.loop_log_every_n
                                ),
                                min_interval_sec=max(
                                    0.0,
                                    float(settings.logging.sampling.min_interval_sec),
                                ),
                            ),
                            rows_read=stats["rows_read"],
                            bytes_read=stats["bytes_read"],
                            batch_cost_ms=cost_ms,
                            started_ts=time.time(),
                        )

                        # 事件级采样：根据 settings.logging.sampling.{default_rate,high_frequency_events}
                        rate = get_event_sampling_rate(
                            settings, EVENT_INGEST_COPY_BATCH
                        )
                        import random as _random

                        if _random.random() <= rate:
                            perf_logger.info(
                                EVENT_INGEST_COPY_BATCH,
                                extra={
                                    "event": EVENT_INGEST_COPY_BATCH,
                                    "extra": {
                                        "batch_size": len(batch),
                                        "batch_cost_ms": cost_ms,
                                        "rows_per_sec": round(rows_per_sec, 2),
                                    },
                                },
                            )

                        file_costs.append(cost_ms)
                        stats["rows_loaded"] = stats.get("rows_loaded", 0) + loaded

                        # 背压判定（基于批次 P95 与数据质量失败率）
                        total = len(valids) + len(rejects)
                        fail_rate = (len(rejects) / total) if total else 0.0
                        k = max(1, int(settings.ingest.p95_window))
                        p95 = _p95(file_costs[-k:])
                        run_diag["p95_samples"].append(p95)
                        adj = ctrl.decide(p95_ms=p95, fail_rate=fail_rate)
                        if adj.get("action") in ("shrink_batch", "shrink_workers"):
                            if not in_backpressure:
                                in_backpressure = True
                                # 事件采样：backpressure.enter（顶部已导入 get_event_sampling_rate）
                                _rate_bp_enter = get_event_sampling_rate(
                                    settings, EVENT_BACKPRESSURE_ENTER
                                )
                                import random as _random

                                if _random.random() <= _rate_bp_enter:
                                    run_diag["bp_enter"] += 1
                                    perf_logger.info(
                                        EVENT_BACKPRESSURE_ENTER,
                                        extra={
                                            "event": EVENT_BACKPRESSURE_ENTER,
                                            "extra": {
                                                "p95_batch_ms": p95,
                                                "p95_window": k,
                                                "batch_cost_ms": cost_ms,
                                                "rows_per_sec": round(rows_per_sec, 2),
                                                "fail_rate": fail_rate,
                                                "adjustment": adj,
                                            },
                                        },
                                    )
                            if adj.get("action") == "shrink_batch" and adj.get(
                                "to_batch"
                            ):
                                batch_size = int(adj["to_batch"]) or batch_size
                        elif adj.get("action") == "recover" and in_backpressure:
                            in_backpressure = False
                            # 事件采样：backpressure.exit（顶部已导入 get_event_sampling_rate）
                            _rate_bp_exit = get_event_sampling_rate(
                                settings, EVENT_BACKPRESSURE_EXIT
                            )
                            import random as _random

                            if _random.random() <= _rate_bp_exit:
                                run_diag["bp_exit"] += 1
                                perf_logger.info(
                                    EVENT_BACKPRESSURE_EXIT,
                                    extra={
                                        "event": EVENT_BACKPRESSURE_EXIT,
                                        "extra": {
                                            "p95_batch_ms": p95,
                                            "p95_window": k,
                                            "batch_cost_ms": cost_ms,
                                            "rows_per_sec": round(rows_per_sec, 2),
                                            "fail_rate": fail_rate,
                                        },
                                    },
                                )
                    stats["files_succeeded"] = stats.get("files_succeeded", 0) + 1
                except Exception:
                    logger.exception(
                        "COPY 失败",
                        extra={
                            "event": "ingest.copy.failed",
                            "extra": {"path": str(path)},
                        },
                    )
                    stats["files_failed"] = stats.get("files_failed", 0) + 1

            if rejects:
                insert_rejects(conn, rejects)
                stats["rows_rejected"] = stats.get("rows_rejected", 0) + len(rejects)

    # 整次 run 的 task.summary 输出（一次）
    from app.utils.logging_ext import (
        EventLogger as _EvtLog2,
    )
    from app.utils.logging_ext import (
        TaskSummaryCollector as _RunSummary,
    )
    from app.utils.logging_ext import (
        log_task_summary as _log_summary2,
    )

    _sum = _RunSummary(
        rows_total=stats.get("rows_read", 0),
        rows_merged=stats.get("rows_loaded", 0),
        backpressure_count=run_diag["bp_enter"],
    )
    if run_diag["p95_samples"]:
        ps2 = sorted(run_diag["p95_samples"])

        def _percentile2(vals, q: float) -> int:
            if not vals:
                return 0
            idx = int(max(0, min(len(vals) - 1, round(q * (len(vals) - 1)))))
            return int(vals[idx])

        _sum.diagnostics = {
            "p50_batch_ms": _percentile2(ps2, 0.50),
            "p90_batch_ms": _percentile2(ps2, 0.90),
            "p95_batch_ms": _percentile2(ps2, 0.95),
            "p99_batch_ms": _percentile2(ps2, 0.99),
            "max_batch_ms": max(ps2) if ps2 else 0,
            "min_batch_ms": min(ps2) if ps2 else 0,
            "avg_fail_rate": 0.0,
            "p95_fail_rate": 0.0,
            "max_fail_rate": 0.0,
            "samples_count": len(ps2),
            "backpressure_enter": run_diag["bp_enter"],
            "backpressure_exit": run_diag["bp_exit"],
        }

    _log_summary2(_EvtLog2(logging.getLogger("root")), _sum)

    return stats
