from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from pathlib import Path as _Path
from typing import Any, Dict, Optional

try:
    import yaml  # 配置文件解析
except Exception:  # pragma: no cover
    yaml = None  # 兜底，不中断运行

from app.services.ingest.copy_workers import copy_from_mapping
from app.services.ingest.create_staging import create_staging
from app.services.ingest.merge_service import merge_window
from app.services.ingest.prepare_dim import prepare_dim
from app.core.time_utils import format_for_display


def run_all(
    settings,
    mapping: str,
    use_staging_time_range: bool,
    window_start: Optional[str],
    window_end: Optional[str],
    summary_json: Optional[str],
    with_device_running: bool = False,
    with_presence: bool = False,
    with_device_phase: bool = False,
    device_id: int | None = None,
) -> Dict[str, Any]:
    """
    通过配置文件开关控制每个子流程：
    configs/merge.yaml:
      run_all:
        prepare_dim: true
        create_staging: true
        ingest_copy: true
        merge_fact: true
        device_running: false
        presence: false
    """
    # 总计时器和耗时统计
    import time
    import sys
    import logging

    _act = logging.getLogger("activity")
    _act.info(
        "[流程-开始] [全流程执行]",
        extra={
            "extra_data": {
                "mapping": mapping,
                "use_staging_time_range": use_staging_time_range,
                "window_start": window_start,
                "window_end": window_end,
                "with_device_running": with_device_running,
                "with_presence": with_presence,
                "device_id": device_id,
            }
        },
    )

    t0_total = time.perf_counter()
    timing_stats: Dict[str, Any] = {}

    # 读取配置开关（不存在或解析失败则默认开启前4步，device_running/presence 默认 False）
    do_prepare_dim = True
    do_create_staging = True
    do_ingest_copy = True
    do_merge_fact = True
    do_prepare_dim_stage2 = False  # 默认关闭阶段2
    cfg_device_running = with_device_running
    cfg_presence = with_presence
    cfg_calculation = False  # 默认关闭计算功能
    device_running_cfg: dict[str, Any] = {}
    calculation_cfg: dict[str, Any] = {}
    try:
        # 优先使用 settings.system.directories.configs，避免受当前工作目录影响
        try:
            _cfg_dirs = getattr(getattr(settings, "system", None), "directories", None)
            _cfg_dir_path = _Path(getattr(_cfg_dirs, "configs", "configs"))
        except Exception:
            _cfg_dir_path = _Path("configs")
        cfg_path = _cfg_dir_path / "merge.yaml"
        if yaml and cfg_path.exists():
            data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            ra = (data or {}).get("run_all", {}) or {}
            do_prepare_dim = bool(ra.get("prepare_dim", do_prepare_dim))
            do_create_staging = bool(ra.get("create_staging", do_create_staging))
            do_ingest_copy = bool(ra.get("ingest_copy", do_ingest_copy))
            do_merge_fact = bool(ra.get("merge_fact", do_merge_fact))
            do_prepare_dim_stage2 = bool(ra.get("prepare_dim_stage2", do_prepare_dim_stage2))
            cfg_device_running = bool(ra.get("device_running", cfg_device_running))
            cfg_presence = bool(ra.get("presence", cfg_presence))
            cfg_calculation = bool(ra.get("enable_calculation", cfg_calculation))
            device_running_cfg = (ra.get("device_running_cfg", {}) or {})
            calculation_cfg = (ra.get("calculation_cfg", {}) or {})

    except Exception:
        pass

    # 环境变量优先级最高：ENABLE_CALCULATION
    import os
    env_calculation = os.getenv("ENABLE_CALCULATION")
    if env_calculation is not None:
        cfg_calculation = env_calculation.strip().lower() in ("1", "true", "yes", "y", "on")

    # 进度：入口参数与开关
    try:
        import logging as _logging

        _act = _logging.getLogger("activity")
        _act.info(
            "[进度] orchestrator.run_all 进入",
            extra={
                "extra_data": {
                    "event": "orchestrator.enter",
                    "flags": {
                        "prepare_dim": do_prepare_dim,
                        "create_staging": do_create_staging,
                        "ingest_copy": do_ingest_copy,
                        "merge_fact": do_merge_fact,
                        "prepare_dim_stage2": do_prepare_dim_stage2,
                        "calculation": cfg_calculation,
                        "device_running": cfg_device_running,
                        "presence": cfg_presence,
                    },
                }
            },
        )
    except Exception:
        pass

    copy_stats: Dict[str, Any] = {
        "files_total": 0,
        "files_succeeded": 0,
        "files_failed": 0,
        "rows_read": 0,
        "rows_loaded": 0,
        "rows_rejected": 0,
    }

    # 1) prepare-dim（阶段1：重建维度表）
    if do_prepare_dim:
        t0_stage = time.perf_counter()
        try:
            import logging as _logging

            _logging.getLogger("activity").info("[进度] prepare-dim 阶段1 开始")
        except Exception:
            pass
        prepare_dim(settings, Path(mapping), stage=1)
        duration_s = time.perf_counter() - t0_stage
        timing_stats["prepare_dim_stage1"] = {"duration_s": duration_s}
        try:
            import logging as _logging

            _logging.getLogger("activity").info(f"[进度] prepare-dim 阶段1 完成 (耗时: {duration_s:.2f}秒)")
        except Exception:
            pass

    # 2) create-staging
    if do_create_staging:
        t0_stage = time.perf_counter()
        try:
            import logging as _logging

            _logging.getLogger("activity").info("[进度] create-staging 开始")
        except Exception:
            pass
        create_staging(settings)
        duration_s = time.perf_counter() - t0_stage
        timing_stats["create_staging"] = {"duration_s": duration_s}
        try:
            import logging as _logging

            _logging.getLogger("activity").info(f"[进度] create-staging 完成 (耗时: {duration_s:.2f}秒)")
        except Exception:
            pass

    # 3) ingest-copy（统计）
    if do_ingest_copy:
        t0_stage = time.perf_counter()
        try:
            import logging as _logging

            _logging.getLogger("activity").info("[进度] ingest-copy 开始")
        except Exception:
            pass
        copy_stats = copy_from_mapping(settings, Path(mapping))
        duration_s = time.perf_counter() - t0_stage
        timing_stats["ingest_copy"] = {"duration_s": duration_s}
        try:
            import logging as _logging

            _logging.getLogger("activity").info(f"[进度] ingest-copy 完成 (耗时: {duration_s:.2f}秒)")
        except Exception:
            pass

    # 4) merge-fact（确定窗口与统计）
    # 统一时间解析（输入）：若参数未带时区，则按 settings.system.timezone.default 解释
    # 统一时间输出（日志/摘要）：格式“YYYY-MM-DD HH:MM:SS+08”，以系统默认时区展示
    def _norm_iso_utc(_s: Optional[str]) -> Optional[str]:
        if not _s:
            return _s
        from datetime import datetime, timezone as _tz
        try:
            from zoneinfo import ZoneInfo as _ZI  # py>=3.9
        except Exception:
            _ZI = None  # type: ignore
        try:
            _dt = datetime.fromisoformat(_s.replace("Z", "+00:00"))
            if _dt.tzinfo is None:
                try:
                    _tz_name = str(getattr(getattr(getattr(settings, "system", None), "timezone", None), "default", "UTC"))
                except Exception:
                    _tz_name = "UTC"
                if _ZI:
                    _dt = _dt.replace(tzinfo=_ZI(_tz_name))
                else:
                    # 回退：直接视为 UTC
                    _dt = _dt.replace(tzinfo=_tz.utc)
            return _dt.astimezone(_tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            return _s

    def _fmt_local(_dt: datetime) -> str:
        """按系统默认时区格式化为 'YYYY-MM-DD HH:MM:SS+08'。"""
        return format_for_display(_dt, settings)

    if use_staging_time_range:
        from datetime import timedelta
        from datetime import timezone as _tz

        from app.adapters.db.gateway import get_conn

        try:
            import logging as _logging

            _logging.getLogger("activity").info("[进度] 窗口探测开始")
        except Exception:
            pass

        # 统一使用 gateway.get_staging_time_range（站点时区优先 + UTC 转换）
        from app.adapters.db.gateway import get_staging_time_range


        with get_conn(settings) as conn:
            ws_dt, we_dt, row_count = get_staging_time_range(conn)
            if not ws_dt or not we_dt:
                raise RuntimeError("staging_raw 无数据，无法确定合并窗口")
            we_dt = we_dt + timedelta(seconds=1)  # 前闭后开，末秒+1s
            ws = ws_dt.astimezone(_tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            we = we_dt.astimezone(_tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            ws_local = _fmt_local(ws_dt)
            we_local = _fmt_local(we_dt)

            # 进度：窗口确定
            try:
                import logging as _logging

                _logging.getLogger("activity").info(
                    "[进度] 窗口确定",
                    extra={
                        "extra_data": {
                            "event": "window.determined",
                            "start": ws_local,
                            "end": we_local,
                        }
                    },
                )
            except Exception:
                pass
    else:
        if not window_start or not window_end:
            raise ValueError("未指定窗口且未启用 --use-staging-time-range")
        ws, we = _norm_iso_utc(window_start), _norm_iso_utc(window_end)
        _ws_dt = datetime.fromisoformat(ws.replace("Z", "+00:00"))
        _we_dt = datetime.fromisoformat(we.replace("Z", "+00:00"))
        ws_local = _fmt_local(_ws_dt)
        we_local = _fmt_local(_we_dt)


    merge_stats = None
    if do_merge_fact:
        t0_stage = time.perf_counter()
        # 进度：merge-fact 开始
        try:
            import logging as _logging

            _logging.getLogger("activity").info(
                "[进度] merge-fact 开始",
                extra={
                    "extra_data": {
                        "event": "merge.start",
                        "start": ws_local,
                        "end": we_local,
                        "device_id": device_id,
                    }
                },
            )
        except Exception:
            pass
        merge_stats = merge_window(
            settings,
            datetime.fromisoformat(ws.replace("Z", "+00:00")),
            datetime.fromisoformat(we.replace("Z", "+00:00")),
            device_id=device_id,
        )
        duration_s = time.perf_counter() - t0_stage
        timing_stats["merge_fact"] = {"duration_s": duration_s}
        # 进度：merge-fact 完成
        try:
            import logging as _logging

            _logging.getLogger("activity").info(
                f"[进度] merge-fact 完成 (耗时: {duration_s:.2f}秒)",
                extra={"extra_data": {"event": "merge.done", "stats": merge_stats, "duration_s": duration_s}},
            )
        except Exception:
            pass

    # 4.1) prepare-dim 阶段2：生成规则表（在 merge-fact 之后执行）
    if do_prepare_dim_stage2:
        t0_stage = time.perf_counter()
        try:
            import logging as _logging

            _logging.getLogger("activity").info("[进度] prepare-dim 阶段2 开始")
        except Exception:
            pass
        prepare_dim_result = prepare_dim(settings, Path(mapping), stage=2)
        duration_s = time.perf_counter() - t0_stage
        # 提取规则生成的详细耗时
        rule_timing = {}
        if prepare_dim_result and "rule_generation" in prepare_dim_result:
            for key, val in prepare_dim_result["rule_generation"].items():
                if isinstance(val, dict) and "duration_ms" in val:
                    rule_timing[key] = val["duration_ms"]
        timing_stats["prepare_dim_stage2"] = {"duration_s": duration_s, "rule_timing_ms": rule_timing}
        try:
            import logging as _logging

            _logging.getLogger("activity").info(f"[进度] prepare-dim 阶段2 完成 (耗时: {duration_s:.2f}秒)")
        except Exception:
            pass

    # 注意：device_running 阶段已整合到 prepare_dim_stage2 中（阶段B）
    # 不再需要独立的 device_running 阶段，避免重复执行
    device_running_summary: Dict[str, Any] | None = None

    # 6.5) 可选后续：device_phase（放在 device_running 之后）

    # 6) 可选后续：presence（在线状态检测，在质量标注之后执行）
    presence_summary: Dict[str, Any] | None = None
    if cfg_presence:
        t0_stage = time.perf_counter()
        try:
            import logging as _logging
            _logging.getLogger("activity").info(
                "[进度] presence 开始",
                extra={
                    "extra_data": {
                        "event": "presence.start",
                        "window": {"start": ws_local, "end": we_local},
                        "device_id": device_id,
                    }
                }
            )
        except Exception:
            pass

        try:
            from datetime import datetime as _dt
            from datetime import timezone as _tz

            from app.services.reporting.presence_writer import (
                run_presence_compute as _rpc,
            )

            # 直接复用已确定的窗口
            s = _dt.fromisoformat(ws.replace("Z", "+00:00")).astimezone(_tz.utc)
            e = _dt.fromisoformat(we.replace("Z", "+00:00")).astimezone(_tz.utc)
            presence_summary = _rpc(start=s, end=e, device_id=device_id)
            duration_s = time.perf_counter() - t0_stage
            timing_stats["presence"] = {"duration_s": duration_s}

            try:
                import logging as _logging
                _logging.getLogger("activity").info(
                    f"[进度] presence 完成 (耗时: {duration_s:.2f}秒)",
                    extra={
                        "extra_data": {
                            "event": "presence.done",
                            "duration_s": duration_s,
                            "summary": presence_summary,
                        }
                    }
                )
            except Exception:
                pass
        except Exception as ex:
            duration_s = time.perf_counter() - t0_stage
            timing_stats["presence"] = {"duration_s": duration_s, "error": str(ex)}
            presence_summary = {"status": "error", "message": str(ex)}

            try:
                import logging as _logging
                _logging.getLogger("activity").error(
                    f"[进度] presence 失败 (耗时: {duration_s:.2f}秒): {ex}",
                    extra={
                        "extra_data": {
                            "event": "presence.error",
                            "duration_s": duration_s,
                            "error": str(ex),
                        }
                    }
                )
            except Exception:
                pass

    # 7) 可选后续：缺失指标计算（在 presence 之后执行）
    calculation_summary: Dict[str, Any] | None = None
    if cfg_calculation:
        t0_stage = time.perf_counter()
        try:
            import logging as _logging

            _act = _logging.getLogger("activity")
            _act.info(
                "[进度] 缺失指标计算开始",
                extra={
                    "extra_data": {
                        "event": "calculation.start",
                        "window": {"start": ws_local, "end": we_local},
                        "device_id": device_id,
                        "config": calculation_cfg,
                    }
                },
            )

            from app.services.calculation.orchestrator import CalculationOrchestrator
            from app.adapters.db import get_connection

            # 获取需要计算的设备列表
            devices = []
            with get_connection() as conn:
                cur = conn.cursor()
                if device_id:
                    # 如果指定了设备ID，只计算该设备
                    cur.execute(
                        "SELECT station_id, id FROM dim_devices WHERE id = %s",
                        (device_id,)
                    )
                else:
                    # 否则计算所有设备
                    cur.execute("SELECT station_id, id FROM dim_devices WHERE COALESCE(is_active, TRUE)=TRUE AND COALESCE(NULLIF(type,''),'') NOT IN ('clear_water_pool','other') ORDER BY station_id, id")
                devices = cur.fetchall()

            if devices:
                _act.info(
                    f"[进度] 缺失指标计算：找到 {len(devices)} 个设备",
                    extra={"extra_data": {"event": "calculation.devices_found", "device_count": len(devices)}}
                )

                # 创建计算编排器
                # 安全卫兵：若方法注册表为空，则自动初始化一次，避免"没有注册的方法"
                try:
                    with get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("SELECT COUNT(*) FROM calculation_method_registry WHERE is_enabled = TRUE")
                            _method_cnt = cur.fetchone()[0]
                    if not _method_cnt:
                        import logging as _logging
                        _logging.getLogger(__name__).warning(
                            "calculation_method_registry 为空，自动执行 init-methods 进行自愈",
                            extra={"extra_data": {"event": "calculation.methods_bootstrap"}}
                        )
                        # 直接复用 CLI 初始化逻辑
                        try:
                            from app.cli.calculation import init_methods as _init_methods
                            _init_methods()
                        except Exception:
                            # 回退到 SQL 直执行（更保守）
                            from pathlib import Path as _P
                            sql_file = _P("scripts")/"sql"/"calculation"/"init_methods.sql"
                            if sql_file.exists():
                                with get_connection() as _conn:
                                    with _conn.cursor() as _cur:
                                        _cur.execute(sql_file.read_text(encoding="utf-8"))
                                        _conn.commit()
                except Exception:
                    # 自愈失败不阻断主流程，后续依然会有日志暴露问题根因
                    pass

                # 从配置读取参数
                _calc_cfg = calculation_cfg or {}
                metrics = _calc_cfg.get("metrics", [])
                max_workers = int(_calc_cfg.get("max_workers", 4))
                auto_parallel = bool(_calc_cfg.get("auto_parallel", True))
                write_to_db = bool(_calc_cfg.get("write_to_db", True))
                enable_optimization = bool(_calc_cfg.get("enable_optimization", False))

                # 创建计算编排器（启用参数优化）
                calc_orchestrator = CalculationOrchestrator(
                    enable_adaptive=True,
                    enable_optimization=enable_optimization
                )

                # 转换时间格式（从 ISO8601 UTC 转换为本地时间字符串）
                _ws_dt = datetime.fromisoformat(ws.replace("Z", "+00:00"))
                _we_dt = datetime.fromisoformat(we.replace("Z", "+00:00"))

                # 转换为本地时区（+08）
                try:
                    from zoneinfo import ZoneInfo as _ZI

                    _tz_cfg = getattr(getattr(settings, "system", None), "timezone", None)
                    if isinstance(_tz_cfg, str):
                        _tz_name = _tz_cfg or "Asia/Shanghai"
                    else:
                        _tz_name = (
                            getattr(_tz_cfg, "default", None)
                            or getattr(_tz_cfg, "display", None)
                            or "Asia/Shanghai"
                        )
                    _ws_local = _ws_dt.astimezone(_ZI(_tz_name))
                    _we_local = _we_dt.astimezone(_ZI(_tz_name))
                except Exception:
                    _ws_local = _ws_dt
                    _we_local = _we_dt

                start_time_str = _ws_dt.isoformat()
                end_time_str = _we_dt.isoformat()

                _act.info(
                    f"[进度] 缺失指标计算：开始批量计算",
                    extra={
                        "extra_data": {
                            "event": "calculation.batch_start",
                            "device_count": len(devices),
                            "metrics": metrics if metrics else "all",
                            "max_workers": max_workers,
                            "auto_parallel": auto_parallel,
                            "write_to_db": write_to_db,
                        }
                    }
                )

                # 执行批量计算
                result = calc_orchestrator.calculate_missing_metrics_batch(
                    devices=devices,
                    start_time=start_time_str,
                    end_time=end_time_str,
                    metrics=metrics if metrics else [],  # 空列表表示计算所有可计算的指标
                    write_to_db=write_to_db,
                    max_workers=max_workers,
                    auto_parallel=auto_parallel,
                )

                calculation_summary = {
                    "status": "ok",
                    "window": {"start": ws_local, "end": we_local},
                    "devices": len(devices),
                    "successful_devices": result.get("successful_devices", 0),
                    "failed_devices": result.get("failed_devices", 0),
                    "total_points": result.get("total_points", 0),
                    "performance": result.get("performance_stats", {}),
                    "config": {
                        "metrics": metrics if metrics else "all",
                        "max_workers": max_workers,
                        "auto_parallel": auto_parallel,
                        "write_to_db": write_to_db,
                    }
                }

                duration_s = time.perf_counter() - t0_stage
                timing_stats["calculation"] = {"duration_s": duration_s}

                _act.info(
                    f"[进度] 缺失指标计算完成 (耗时: {duration_s:.2f}秒)",
                    extra={
                        "extra_data": {
                            "event": "calculation.done",
                            "duration_s": duration_s,
                            "summary": calculation_summary,
                        }
                    },
                )
            else:
                duration_s = time.perf_counter() - t0_stage
                timing_stats["calculation"] = {"duration_s": duration_s}

                calculation_summary = {
                    "status": "skipped",
                    "reason": "no_devices_found",
                    "window": {"start": ws_local, "end": we_local},
                }
                _act.info(
                    f"[进度] 缺失指标计算跳过：未找到设备 (耗时: {duration_s:.2f}秒)",
                    extra={"extra_data": {"event": "calculation.skipped", "reason": "no_devices_found", "duration_s": duration_s}}
                )

        except Exception as ex:
            import logging as _logging
            import traceback

            duration_s = time.perf_counter() - t0_stage
            timing_stats["calculation"] = {"duration_s": duration_s, "error": str(ex)}

            _logging.getLogger("error").error(
                f"[错误] 缺失指标计算失败 (耗时: {duration_s:.2f}秒): {ex}",
                extra={
                    "extra_data": {
                        "event": "calculation.error",
                        "duration_s": duration_s,
                        "error": str(ex),
                        "traceback": traceback.format_exc(),
                    }
                }
            )
            calculation_summary = {
                "status": "error",
                "message": str(ex),
                "window": {"start": ws_local, "end": we_local},
            }


    # 生成耗时统计报告
    total_duration_s = time.perf_counter() - t0_total
    timing_stats["total"] = {"duration_s": total_duration_s}

    # 生成Markdown表格格式的耗时统计报告
    try:
        import logging as _logging
        _act = _logging.getLogger("activity")

        # 构建报告
        report_lines = [
            "",
            "=" * 80,
            "⏱️  **耗时统计报告**",
            "=" * 80,
            "",
            "| 阶段名称 | 耗时（秒） | 占比（%） | 详细信息 |",
            "|---------|-----------|----------|---------|"
        ]

        # 计算每个阶段的占比
        for stage_name, stage_data in timing_stats.items():
            if stage_name == "total":
                continue
            duration_s = stage_data.get("duration_s", 0)
            percentage = (duration_s / total_duration_s * 100) if total_duration_s > 0 else 0

            # 详细信息（规则生成的6个函数耗时）
            details = ""
            if stage_name == "prepare_dim_stage2" and "rule_timing_ms" in stage_data:
                rule_timing = stage_data["rule_timing_ms"]
                if rule_timing:
                    details_parts = []
                    for rule_name, duration_ms in rule_timing.items():
                        details_parts.append(f"{rule_name}: {duration_ms}ms")
                    details = "; ".join(details_parts)

            report_lines.append(
                f"| {stage_name} | {duration_s:.2f} | {percentage:.1f} | {details} |"
            )

        # 总计行
        report_lines.append("|---------|-----------|----------|---------|")
        report_lines.append(f"| **总计** | **{total_duration_s:.2f}** | **100.0** | |")
        report_lines.append("=" * 80)
        report_lines.append("")

        report_text = "\n".join(report_lines)

        # 输出到日志
        _act.info(f"[耗时统计]\n{report_text}")

        # 输出到控制台（确保实时显示）
        print(report_text)
        sys.stdout.flush()

    except Exception as e:
        pass  # 忽略报告生成错误，不影响主流程

    _act.info(
        "[流程-完成] [全流程执行完成]",
        extra={
            "extra_data": {
                "total_duration_s": time.perf_counter() - t0_total,
                "files_succeeded": int(copy_stats.get("files_succeeded", 0)),
                "files_failed": int(copy_stats.get("files_failed", 0)),
                "rows_loaded": int(copy_stats.get("rows_loaded", 0)),
                "rows_rejected": int(copy_stats.get("rows_rejected", 0)),
            }
        },
    )

    summary = {
        "mapping_file": str(mapping),
        "window": {"start": ws_local, "end": we_local},
        "copy_stats": {
            "files_total": int(copy_stats.get("files_total", 0)),
            "files_succeeded": int(copy_stats.get("files_succeeded", 0)),
            "files_failed": int(copy_stats.get("files_failed", 0)),
            "rows_read": int(copy_stats.get("rows_read", 0)),
            "rows_loaded": int(copy_stats.get("rows_loaded", 0)),
            "rows_rejected": int(copy_stats.get("rows_rejected", 0)),
        },
        "merge_stats": (merge_stats or {}),
        "calculation": calculation_summary,
        "device_running": device_running_summary,
        "presence": presence_summary,
        "timing_stats": timing_stats,  # 添加耗时统计到摘要
    }

    if summary_json:
        out = Path(summary_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        import json as _json

        out.write_text(
            _json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    return summary
