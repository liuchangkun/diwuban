from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from datetime import datetime, timedelta, timezone

from app.services.rules.auto_baseline_b import run_auto_baseline_b
from app.services.rules.auto_baseline import run_auto_baseline
from app.services.rules.metric_quality_rules_b import (
    compute_metric_quality_rules_shadow,
)
from app.services.rules.metric_quality_rules import compute_metric_quality_rules
from app.services.rules.running_thresholds_b import run_running_thresholds_b
from app.services.rules.running_thresholds import run_running_thresholds
from app.services.ingest.prepare_dim import prepare_dim
from app.core.time_utils import format_for_display


@dataclass
class RefreshAllPlan:
    lookback_days: int
    station_id: Optional[int]
    device_id: Optional[int]
    window_start: Optional[str]
    window_end: Optional[str]
    method_thresholds_a: str  # robust|otsu
    mode: str  # shadow|prod|both
    capabilities_mapping: Optional[str]
    with_mark: bool = True
    with_diff_report: bool = False
    report_dir: Optional[str] = None


def _iso_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _derive_window(now_utc: datetime, days: int) -> tuple[str, str]:
    end = now_utc
    start = now_utc - timedelta(days=days)
    return _iso_utc(start), _iso_utc(end)


def run_refresh_all(settings, plan: RefreshAllPlan) -> Dict[str, Any]:
    import logging
    _act = logging.getLogger("activity")

    _act.info(
        "[流程-开始] [刷新全部数据]",
        extra={
            "extra_data": {
                "mode": plan.mode,
                "lookback_days": plan.lookback_days,
                "station_id": plan.station_id,
                "device_id": plan.device_id,
            }
        }
    )

    summary: Dict[str, Any] = {
        "args": plan.__dict__,
        "steps": [],
    }
    now_u = datetime.now(timezone.utc)

    # 1) 设备能力（可选）
    if plan.capabilities_mapping:
        _act.info(
            "[流程-阶段] [准备维度数据]",
            extra={"extra_data": {"mapping_file": plan.capabilities_mapping}}
        )
        try:
            prepare_dim(settings, plan.capabilities_mapping)
            summary["steps"].append({"step": "prepare_dim", "ok": True})
            _act.info(
                "[流程-阶段] [维度数据准备完成]",
                extra={"extra_data": {"ok": True}}
            )
        except Exception as e:
            summary["steps"].append(
                {"step": "prepare_dim", "ok": False, "error": str(e)}
            )
            _act.error(
                "[流程-错误] [维度数据准备失败]",
                extra={"extra_data": {"error": str(e)}}
            )

    # 窗口（统一按系统默认时区解析；对外输出格式：YYYY-MM-DD HH:MM:SS+08）
    def _to_local_fmt(_s: Optional[str]) -> Optional[str]:
        if not _s:
            return _s
        try:
            dt = datetime.fromisoformat(_s.replace("Z", "+00:00"))
            return format_for_display(dt, settings)
        except Exception:
            return _s

    if plan.window_start and plan.window_end:
        win_start = _to_local_fmt(plan.window_start)
        win_end = _to_local_fmt(plan.window_end)
    else:
        win_start, win_end = _derive_window(now_u, plan.lookback_days)
        win_start = _to_local_fmt(win_start)
        win_end = _to_local_fmt(win_end)

    do_shadow = plan.mode in ("shadow", "both")
    do_prod = plan.mode in ("prod", "both")

    _act.info(
        "[流程-阶段] [时间窗口确定]",
        extra={
            "extra_data": {
                "window_start": win_start,
                "window_end": win_end,
                "do_shadow": do_shadow,
                "do_prod": do_prod,
            }
        }
    )

    # 2) 基线（影子 B）
    if do_shadow:
        _act.info(
            "[流程-阶段] [开始计算影子基线]",
            extra={
                "extra_data": {
                    "lookback_days": plan.lookback_days,
                    "station_id": plan.station_id,
                    "device_id": plan.device_id,
                    "method": "stl_residual",
                    "version": "vB_shadow",
                }
            }
        )
        try:
            res_b = run_auto_baseline_b(
                settings,
                lookback_days=plan.lookback_days,
                station_id=plan.station_id,
                device_id=plan.device_id,
                method="stl_residual",
                version="vB_shadow",
            )
            summary["steps"].append(
                {
                    "step": "baseline_shadow",
                    "ok": True,
                    "inserted": res_b.get("inserted", 0),
                }
            )
            _act.info(
                "[流程-阶段] [影子基线计算完成]",
                extra={
                    "extra_data": {
                        "inserted": res_b.get("inserted", 0),
                        "ok": True,
                    }
                }
            )
        except Exception as e:
            summary["steps"].append(
                {"step": "baseline_shadow", "ok": False, "error": str(e)}
            )
            _act.error(
                "[流程-错误] [影子基线计算失败]",
                extra={"extra_data": {"error": str(e)}}
            )

    # 3) 基线（正式 A）
    if do_prod:
        _act.info(
            "[流程-阶段] [开始计算正式基线]",
            extra={
                "extra_data": {
                    "lookback_days": plan.lookback_days,
                    "station_id": plan.station_id,
                    "device_id": plan.device_id,
                }
            }
        )
        try:
            res_a = run_auto_baseline(
                settings, plan.lookback_days, plan.station_id, plan.device_id
            )
            summary["steps"].append({"step": "baseline_prod", "ok": True})
            _act.info(
                "[流程-阶段] [正式基线计算完成]",
                extra={"extra_data": {"ok": True}}
            )
        except Exception as e:
            summary["steps"].append(
                {"step": "baseline_prod", "ok": False, "error": str(e)}
            )
            _act.error(
                "[流程-错误] [正式基线计算失败]",
                extra={"extra_data": {"error": str(e)}}
            )

    # 4) 质量规则（影子 B）
    if do_shadow:
        _act.info(
            "[流程-阶段] [开始计算影子质量规则]",
            extra={
                "extra_data": {
                    "station_id": plan.station_id,
                    "device_id": plan.device_id,
                    "method": "stl_residual",
                    "version": "vB_shadow",
                }
            }
        )
        try:
            res_qb = compute_metric_quality_rules_shadow(
                settings,
                station_id=plan.station_id,
                device_id=plan.device_id,
                method="stl_residual",
                version="vB_shadow",
            )
            summary["steps"].append(
                {
                    "step": "quality_rules_shadow",
                    "ok": True,
                    "inserted": res_qb.get("inserted", 0),
                }
            )
            _act.info(
                "[流程-阶段] [影子质量规则计算完成]",
                extra={
                    "extra_data": {
                        "inserted": res_qb.get("inserted", 0),
                        "ok": True,
                    }
                }
            )
        except Exception as e:
            summary["steps"].append(
                {"step": "quality_rules_shadow", "ok": False, "error": str(e)}
            )
            _act.error(
                "[流程-错误] [影子质量规则计算失败]",
                extra={"extra_data": {"error": str(e)}}
            )

    # 5) 运行阈值（影子 B - GMM）
    if do_shadow:
        _act.info(
            "[流程-阶段] [开始计算影子运行阈值]",
            extra={
                "extra_data": {
                    "window_start": win_start,
                    "window_end": win_end,
                    "station_id": plan.station_id,
                    "device_id": plan.device_id,
                    "method": "gmm_bimodal",
                    "version": "vB_shadow",
                }
            }
        )
        try:
            res_rb = run_running_thresholds_b(
                settings=settings,
                start=win_start,
                end=win_end,
                station_id=plan.station_id,
                device_id=plan.device_id,
                method="gmm_bimodal",
                version="vB_shadow",
            )
            summary["steps"].append(
                {
                    "step": "running_thresholds_shadow",
                    "ok": True,
                    "inserted": res_rb.get("inserted", 0),
                }
            )
            _act.info(
                "[流程-阶段] [影子运行阈值计算完成]",
                extra={
                    "extra_data": {
                        "inserted": res_rb.get("inserted", 0),
                        "ok": True,
                    }
                }
            )
        except Exception as e:
            summary["steps"].append(
                {"step": "running_thresholds_shadow", "ok": False, "error": str(e)}
            )
            _act.error(
                "[流程-错误] [影子运行阈值计算失败]",
                extra={"extra_data": {"error": str(e)}}
            )

    # 6) 运行阈值（正式 A）
    if do_prod:
        _act.info(
            "[流程-阶段] [开始计算正式运行阈值]",
            extra={
                "extra_data": {
                    "window_start": win_start,
                    "window_end": win_end,
                    "station_id": plan.station_id,
                    "device_id": plan.device_id,
                    "method": plan.method_thresholds_a,
                }
            }
        )
        try:
            res_ra = run_running_thresholds(
                settings=settings,
                start=win_start,
                end=win_end,
                station_id=plan.station_id,
                device_id=plan.device_id,
                ensure_rows=True,
                method=plan.method_thresholds_a,
            )
            summary["steps"].append(
                {
                    "step": "running_thresholds_prod",
                    "ok": True,
                    "inserted": (
                        res_ra.get("inserted", 0) if isinstance(res_ra, dict) else None
                    ),
                }
            )
            _act.info(
                "[流程-阶段] [正式运行阈值计算完成]",
                extra={
                    "extra_data": {
                        "inserted": res_ra.get("inserted", 0) if isinstance(res_ra, dict) else None,
                        "ok": True,
                    }
                }
            )
        except Exception as e:
            summary["steps"].append(
                {"step": "running_thresholds_prod", "ok": False, "error": str(e)}
            )
            _act.error(
                "[流程-错误] [正式运行阈值计算失败]",
                extra={"extra_data": {"error": str(e)}}
            )

    # 7) 质量规则（正式 A）
    if do_prod:
        _act.info(
            "[流程-阶段] [开始计算正式质量规则]",
            extra={
                "extra_data": {
                    "station_id": plan.station_id,
                    "device_id": plan.device_id,
                }
            }
        )
        try:
            res_qa = compute_metric_quality_rules(
                settings, station_id=plan.station_id, device_id=plan.device_id
            )
            summary["steps"].append(
                {
                    "step": "quality_rules_prod",
                    "ok": True,
                    "inserted": res_qa.get("inserted", 0),
                    "updated": res_qa.get("updated", 0),
                }
            )
            _act.info(
                "[流程-阶段] [正式质量规则计算完成]",
                extra={
                    "extra_data": {
                        "inserted": res_qa.get("inserted", 0),
                        "updated": res_qa.get("updated", 0),
                        "ok": True,
                    }
                }
            )
        except Exception as e:
            summary["steps"].append(
                {"step": "quality_rules_prod", "ok": False, "error": str(e)}
            )
            _act.error(
                "[流程-错误] [正式质量规则计算失败]",
                extra={"extra_data": {"error": str(e)}}
            )


    # 9) 明细层（可选）：质量打标
    if plan.with_mark:
        _act.info(
            "[流程-阶段] [开始质量打标]",
            extra={
                "extra_data": {
                    "window_start": win_start,
                    "window_end": win_end,
                    "station_id": plan.station_id,
                    "device_id": plan.device_id,
                }
            }
        )
        try:
            from app.services.quality.mark_window import mark_quality_window

            mark_res = mark_quality_window(
                settings,
                start=win_start,
                end=win_end,
                station_id=plan.station_id,
                device_id=plan.device_id,
            )
            summary["steps"].append(
                {"step": "quality_mark", "ok": True, **(mark_res or {})}
            )
            _act.info(
                "[流程-阶段] [质量打标完成]",
                extra={
                    "extra_data": {
                        "ok": True,
                        "result": mark_res,
                    }
                }
            )
        except Exception as e:
            summary["steps"].append(
                {"step": "quality_mark", "ok": False, "error": str(e)}
            )
            _act.error(
                "[流程-错误] [质量打标失败]",
                extra={"extra_data": {"error": str(e)}}
            )

    # 10) 差异报告（可选）
    if plan.with_diff_report:
        try:
            from app.services.reporting.rules_diff_report import run_rules_diff_report

            rep = run_rules_diff_report(
                settings,
                method="stl_residual",
                version="vB_shadow",
                out_dir=plan.report_dir,
            )
            summary["steps"].append({"step": "diff_report", "ok": True, "report": rep})
        except Exception as e:
            summary["steps"].append(
                {"step": "diff_report", "ok": False, "error": str(e)}
            )

    summary["window"] = {"start": win_start, "end": win_end}

    # 统计成功和失败的步骤
    total_steps = len(summary["steps"])
    success_steps = sum(1 for step in summary["steps"] if step.get("ok"))
    failed_steps = total_steps - success_steps

    _act.info(
        "[流程-完成] [刷新全部数据完成]",
        extra={
            "extra_data": {
                "total_steps": total_steps,
                "success_steps": success_steps,
                "failed_steps": failed_steps,
                "window_start": win_start,
                "window_end": win_end,
                "mode": plan.mode,
            }
        }
    )

    return summary
