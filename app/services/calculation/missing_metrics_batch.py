from __future__ import annotations

import concurrent.futures as cf
import json
import math
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import psycopg

from app.core.config.loader_new import load_settings
from app.adapters.db import init_database, get_connection
from app.services.calculation.orchestrator import CalculationOrchestrator

import logging

_act = logging.getLogger(__name__)

TZ_SH = timezone(timedelta(hours=8))


@dataclass
class BatchPlan:
    start: datetime
    end: datetime
    window_hours: int
    devices: List[Tuple[int, int]]  # (station_id, device_id)
    metrics: Optional[List[str]] = None  # None表示从metrics_presence_per_second_device动态查询
    filter_running: bool = True
    filter_quality: bool = True
    concurrency: int = 3
    dry_run: bool = False
    limit_windows_per_device: Optional[int] = None
    use_presence_table: bool = True  # 是否使用metrics_presence_per_second_device表


def _datetime_range(start: datetime, end: datetime, step_hours: int) -> Iterable[Tuple[datetime, datetime]]:
    cur = start
    step = timedelta(hours=step_hours)
    while cur < end:
        nxt = min(cur + step, end)
        yield cur, nxt
        cur = nxt


def _fetch_global_span_and_devices() -> Tuple[datetime, datetime, List[Tuple[int, int]]]:
    _act.info("[流程-开始] [获取全局时间范围和设备列表]")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT MIN(ts_bucket), MAX(ts_bucket) FROM public.fact_measurements")
            min_ts, max_ts = cur.fetchone()
            # 设备列表，按行数降序
            cur.execute(
                """
                SELECT station_id, device_id
                FROM public.fact_measurements
                GROUP BY station_id, device_id
                ORDER BY COUNT(*) DESC
                """
            )
            devices = [(r[0], r[1]) for r in cur.fetchall()]
    # 统一为 +08:00 时区（若已有 tz 则保持）
    if isinstance(min_ts, datetime) and min_ts.tzinfo is None:
        min_ts = min_ts.replace(tzinfo=TZ_SH)
    if isinstance(max_ts, datetime) and max_ts.tzinfo is None:
        max_ts = max_ts.replace(tzinfo=TZ_SH)
    return min_ts, max_ts, devices


def _fetch_enabled_metrics() -> List[str]:
    """获取全局启用的指标列表（已废弃，仅用于向后兼容）"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT metric_key
                FROM calculation_method_registry
                WHERE is_enabled = TRUE
                ORDER BY metric_key
                """
            )
            return [r[0] for r in cur.fetchall()]


def _fetch_metrics_for_device_window(
    station_id: int,
    device_id: int,
    start_time: datetime,
    end_time: datetime
) -> List[str]:
    """
    从metrics_presence_per_second_device表查询指定设备和时间窗口需要计算的指标

    Args:
        station_id: 泵站ID
        device_id: 设备ID
        start_time: 开始时间
        end_time: 结束时间

    Returns:
        需要计算的指标列表（去重后）
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 先查询总记录数用于调试
            cur.execute(
                """
                SELECT COUNT(*) as total_records,
                       COUNT(CASE WHEN array_length(need_compute_metrics, 1) > 0 THEN 1 END) as records_with_metrics
                FROM metrics_presence_per_second_device
                WHERE station_id = %s
                  AND device_id = %s
                  AND ts_second >= %s::timestamptz
                  AND ts_second < %s::timestamptz
                """,
                (station_id, device_id, start_time, end_time)
            )
            debug_info = cur.fetchone()
            _act.info(
                f"[设备 {device_id}] 时间窗口 [{start_time}, {end_time}) "
                f"查询到 {debug_info[0]} 条记录，其中 {debug_info[1]} 条有需要计算的指标"
            )

            # 查询需要计算的指标
            cur.execute(
                """
                SELECT DISTINCT unnest(need_compute_metrics) as metric_key
                FROM metrics_presence_per_second_device
                WHERE station_id = %s
                  AND device_id = %s
                  AND ts_second >= %s::timestamptz
                  AND ts_second < %s::timestamptz
                  AND array_length(need_compute_metrics, 1) > 0
                ORDER BY metric_key
                """,
                (station_id, device_id, start_time, end_time)
            )
            metrics = [r[0] for r in cur.fetchall()]

            if not metrics:
                _act.warning(
                    f"[设备 {device_id}] 时间窗口 [{start_time}, {end_time}) 没有需要计算的指标"
                )
            else:
                _act.info(
                    f"[设备 {device_id}] 时间窗口 [{start_time}, {end_time}) "
                    f"需要计算 {len(metrics)} 个指标: {metrics}"
                )

            return metrics


def build_plan(
    start: Optional[str] = None,
    end: Optional[str] = None,
    station_id: Optional[int] = None,
    device_id: Optional[int] = None,
    window_hours: int = 1,
    concurrency: int = 3,
    dry_run: bool = False,
    filter_running: bool = True,
    filter_quality: bool = True,
    limit_devices: Optional[int] = None,
    limit_windows_per_device: Optional[int] = None,
    use_presence_table: bool = True,  # 新增参数：是否使用metrics_presence_per_second_device表
) -> BatchPlan:
    # 全局范围与设备
    min_ts, max_ts, devices = _fetch_global_span_and_devices()

    # 范围覆盖
    st = datetime.fromisoformat(start) if start else min_ts
    ed = datetime.fromisoformat(end) if end else max_ts

    # 设备限定
    if station_id is not None and device_id is not None:
        devices = [(station_id, device_id)]
    elif station_id is not None:
        devices = [(sid, did) for (sid, did) in devices if sid == station_id]
    elif device_id is not None:
        devices = [(sid, did) for (sid, did) in devices if did == device_id]

    if limit_devices is not None:
        devices = devices[: max(1, int(limit_devices))]

    # 如果使用presence表，则不在这里获取指标列表，而是在worker中动态查询
    # 否则使用全局指标列表（向后兼容）
    metrics = None if use_presence_table else _fetch_enabled_metrics()

    if use_presence_table:
        _act.info("[计划模式] 使用 metrics_presence_per_second_device 表动态查询每个设备每个时间窗口的指标")
    else:
        _act.info(f"[计划模式] 使用全局指标列表: {metrics}")

    return BatchPlan(
        start=st, end=ed, window_hours=max(1, int(window_hours)),
        devices=devices, metrics=metrics,
        filter_running=bool(filter_running), filter_quality=bool(filter_quality),
        concurrency=max(1, int(concurrency)), dry_run=bool(dry_run),
        limit_windows_per_device=limit_windows_per_device,
        use_presence_table=bool(use_presence_table),
    )


def _run_one(orchestrator: CalculationOrchestrator, station_id: int, device_id: int,
             win_start: datetime, win_end: datetime, metrics: List[str],
             filter_running: bool, filter_quality: bool, write: bool) -> Dict[str, Any]:
    return orchestrator.calculate_missing_metrics(
        station_id=station_id,
        device_id=device_id,
        start_time=win_start.isoformat(),
        end_time=win_end.isoformat(),
        metrics=metrics,
        write_to_db=write,
        filter_running=filter_running,
        filter_quality=filter_quality,
    )


def run_missing_metrics_compute(
    plan: BatchPlan,
    report_dir: Path = Path("reports"),
) -> Dict[str, Any]:
    _act.info(
        "[流程-开始] [批量计算缺失指标]",
        extra={
            "extra_data": {
                "device_count": len(plan.devices),
                "metric_count": len(plan.metrics) if plan.metrics else "dynamic",
                "use_presence_table": plan.use_presence_table,
                "window_hours": plan.window_hours,
                "concurrency": plan.concurrency,
                "dry_run": plan.dry_run,
            }
        },
    )

    report_dir.mkdir(parents=True, exist_ok=True)

    total_tasks = 0
    for _sid, _did in plan.devices:
        # 计算每设备窗口总数
        total_tasks += sum(1 for _ in _datetime_range(plan.start, plan.end, plan.window_hours))

    _act.info(
        "[流程-阶段] [任务规划完成]",
        extra={"extra_data": {"total_tasks": total_tasks}},
    )

    t0 = time.time()
    results: List[Dict[str, Any]] = []

    #
    # Build maps: metric_key -> allowed device types, and (station_id,device_id) -> device type
    allowed_map = {}
    device_type_map = {}
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT metric_key, allowed_device_types
                    FROM public.calculation_method_registry
                    WHERE is_enabled
                    """
                )
                for mk, adt in cur.fetchall():
                    allowed_map[str(mk)] = set(adt or [])
                cur.execute("SELECT station_id, id AS device_id, type FROM public.dim_devices")
                for sid, did, tp in cur.fetchall():
                    device_type_map[(int(sid), int(did))] = str(tp)
    except Exception:
        # Fallback to empty maps on any error
        allowed_map = {}
        device_type_map = {}

    # 为了线程安全，每个线程内部各自构造 orchestrator
    def worker(args: Tuple[int, int, datetime, datetime]) -> Dict[str, Any]:
        sid, did, ws, we = args
        orch = CalculationOrchestrator()
        try:
            # 1. 获取指标列表
            if plan.use_presence_table:
                # 从metrics_presence_per_second_device表动态查询
                metrics_for_window = _fetch_metrics_for_device_window(sid, did, ws, we)
            else:
                # 使用全局指标列表（向后兼容）
                metrics_for_window = plan.metrics or []

            # 2. 按设备类型过滤指标（二次过滤）
            dtype = device_type_map.get((sid, did))
            if dtype:
                metrics_for_device = [m for m in metrics_for_window if dtype in (allowed_map.get(m) or set())]
            else:
                metrics_for_device = metrics_for_window

            # 3. 如果没有需要计算的指标，直接返回成功
            if not metrics_for_device:
                return {
                    "station_id": sid,
                    "device_id": did,
                    "start": ws.isoformat(),
                    "end": we.isoformat(),
                    "success": True,
                    "result": {
                        "success": True,
                        "metrics_calculated": [],
                        "metrics_failed": [],
                        "total_points": 0,
                        "valid_points": 0,
                        "written_points": 0,
                        "errors": [],
                        "performance_stats": {},
                        "message": "No metrics to calculate for this device and time window"
                    },
                }

            # 4. 执行计算
            res = _run_one(
                orch, sid, did, ws, we, metrics_for_device,
                plan.filter_running, plan.filter_quality, write=(not plan.dry_run)
            )
            return {
                "station_id": sid,
                "device_id": did,
                "start": ws.isoformat(),
                "end": we.isoformat(),
                "success": True,
                "result": res,
            }
        except Exception as e:
            return {
                "station_id": sid,
                "device_id": did,
                "start": ws.isoformat(),
                "end": we.isoformat(),
                "success": False,
                "error": str(e),
            }

    tasks: List[Tuple[int, int, datetime, datetime]] = []
    for sid, did in plan.devices:
        windows = list(_datetime_range(plan.start, plan.end, plan.window_hours))
        if plan.limit_windows_per_device is not None:
            windows = windows[: max(1, int(plan.limit_windows_per_device))]
        for ws, we in windows:
            tasks.append((sid, did, ws, we))

    # 并发执行
    with cf.ThreadPoolExecutor(max_workers=plan.concurrency) as ex:
        for out in ex.map(worker, tasks):
            results.append(out)

    t1 = time.time()

    # 汇总统计
    summary: Dict[str, Any] = {
        "devices": len(plan.devices),
        "windows": len(tasks),
        "metrics": plan.metrics if plan.metrics else "dynamic (from metrics_presence_per_second_device)",
        "use_presence_table": plan.use_presence_table,
        "concurrency": plan.concurrency,
        "filter_running": plan.filter_running,
        "filter_quality": plan.filter_quality,
        "dry_run": plan.dry_run,
        "window_hours": plan.window_hours,
        "duration_sec": round(t1 - t0, 3),
    }

    # 统计成功/失败与写入
    success_tasks = [r for r in results if r.get("success")]
    failed_tasks = [r for r in results if not r.get("success")]
    summary["success_tasks"] = len(success_tasks)
    summary["failed_tasks"] = len(failed_tasks)

    per_metric_success: Dict[str, int] = {}
    per_metric_written: Dict[str, int] = {}
    per_metric_failed: Dict[str, int] = {}
    per_metric_method_hits: Dict[str, Dict[str, int]] = {}
    failure_reason_counts: Dict[str, int] = {}
    per_metric_failure_reasons: Dict[str, Dict[str, int]] = {}

    # 性能聚合
    total_load_time = 0.0
    total_calc_time = 0.0
    total_write_time = 0.0
    per_metric_time: Dict[str, float] = {}

    def _cat_reason(text: str) -> str:
        if not text:
            return "unknown"
        if "没有可用的计算方法" in text:
            return "no_method"
        if "依赖数据无效" in text or "依赖" in text:
            return "invalid_dependencies"
        if "验证失败" in text or "NaN" in text or "范围" in text:
            return "validation_failed"
        return "other"

    for r in success_tasks:
        res = r.get("result", {})

        # 成功/失败数
        for mk in res.get("metrics_calculated", []) or []:
            per_metric_success[mk] = per_metric_success.get(mk, 0) + 1
        for mk in res.get("metrics_failed", []) or []:
            per_metric_failed[mk] = per_metric_failed.get(mk, 0) + 1

        # 写入条数（dry_run 下通常为 0，仅统计潜在写入点数）
        stats = res.get("stats_collector", {}) or {}
        for key, stat in stats.items():
            mk = key.split("|")[-3] if "|" in key else None
            if mk:
                per_metric_written[mk] = per_metric_written.get(mk, 0) + int(stat.get("written_points", 0))
                method_id = stat.get("method_id")
                if method_id:
                    per_metric_method_hits.setdefault(mk, {})[method_id] = per_metric_method_hits.get(mk, {}).get(method_id, 0) + 1

        # 失败原因
        for err in res.get("errors", []) or []:
            cat = _cat_reason(str(err))
            failure_reason_counts[cat] = failure_reason_counts.get(cat, 0) + 1
            # 尝试解析出 metric key
            mk = None
            if ":" in str(err):
                mk = str(err).split(":", 1)[0].strip()
            if mk:
                d = per_metric_failure_reasons.setdefault(mk, {})
                d[cat] = d.get(cat, 0) + 1

        # 性能
        perf = res.get("performance_stats", {}) or {}
        total_load_time += float(perf.get("load_time_sec", 0.0) or 0.0)
        total_calc_time += float(perf.get("calc_time_sec", 0.0) or 0.0)
        total_write_time += float(perf.get("write_time_sec", 0.0) or 0.0)
        mt = perf.get("metric_times", {}) or {}
        for mk, secs in mt.items():
            per_metric_time[mk] = per_metric_time.get(mk, 0.0) + float(secs or 0.0)

    performance_summary = {
        "total_load_time_sec": round(total_load_time, 3),
        "total_calc_time_sec": round(total_calc_time, 3),
        "total_write_time_sec": round(total_write_time, 3),
        "per_metric_time_sec": {k: round(v, 3) for k, v in sorted(per_metric_time.items())},
    }

    report = {
        "plan": {
            "start": plan.start.isoformat(),
            "end": plan.end.isoformat(),
            "window_hours": plan.window_hours,
            "devices": plan.devices,
            "metrics": plan.metrics,
            "concurrency": plan.concurrency,
            "filter_running": plan.filter_running,
            "filter_quality": plan.filter_quality,
            "dry_run": plan.dry_run,
        },
        "summary": summary,
        "per_metric_success_tasks": per_metric_success,
        "per_metric_failed_tasks": per_metric_failed,
        "per_metric_written_points": per_metric_written,
        "per_metric_method_hits": per_metric_method_hits,
        "failure_reason_counts": failure_reason_counts,
        "per_metric_failure_reasons": per_metric_failure_reasons,
        "performance_summary": performance_summary,
        "results": results[:2000],  # 防爆：截断明细
        "timestamp": datetime.now(tz=TZ_SH).isoformat(),
    }

    ts = datetime.now(tz=TZ_SH).strftime("%Y%m%d_%H%M%S")
    out_path = report_dir / f"missing_metrics_full_{ts}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "report": str(out_path), "summary": summary}

