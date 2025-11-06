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
    with_quality_mark: bool = False,
    with_device_phase: bool = False,
    device_id: int | None = None,
    quality_codes: list[int] | None = None,
    quality_diag_level: str | None = None,
    quality_parallel: int | str = 1,
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
        quality_mark: false
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
                "with_quality_mark": with_quality_mark,
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
    cfg_quality_mark = with_quality_mark
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
            cfg_quality_mark = bool(ra.get("quality_mark", cfg_quality_mark))
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
                        "quality_mark": cfg_quality_mark,
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

    # 5) 可选后续：quality_mark（质量标注）
    quality_mark_summary: Dict[str, Any] | None = None
    if cfg_quality_mark:
        t0_stage = time.perf_counter()
        try:
            import logging as _logging
            import uuid as _uuid

            from app.services.quality.mark_window import mark_quality_window as _mqw
            from app.services.reporting.code_dist import (
                export_window_code_distribution as _export_win,
            )

            _anom_logger = _logging.getLogger("anomaly")

            # 从 merge.yaml 读取启用的质量码列表与诊断级别，用于透传给存储过程
            enabled_codes = None
            diag_level = None
            try:
                # 同上：通过 settings.system.directories.configs 定位 merge.yaml
                try:
                    _cfg_dirs = getattr(
                        getattr(settings, "system", None), "directories", None
                    )
                    _cfg_dir_path = _Path(getattr(_cfg_dirs, "configs", "configs"))
                except Exception:
                    _cfg_dir_path = _Path("configs")
                cfg_path = _cfg_dir_path / "merge.yaml"
                if yaml and cfg_path.exists():
                    _data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
                    ra = (_data or {}).get("run_all", {}) or {}
                    _codes = ra.get("quality_mark_codes_enabled")
                    if isinstance(_codes, list) and all(
                        isinstance(x, int) for x in _codes
                    ):
                        enabled_codes = _codes
                    diag = ra.get("anomaly_diagnosis", {}) or {}
                    diag_level = str(diag.get("level", "off")) if diag else None
            except Exception:
                enabled_codes = None
                diag_level = None

            # 生成本次运行ID
            _run_id = _uuid.uuid4().hex

            # 窗口级开始日志（冗余一份在 orchestrator 层，中文键）
            try:
                import threading as _th

                _anom_logger.info(
                    "[ANOMALY] window_start",
                    extra={
                        "extra_data": {
                            "事件": "anomaly.window_start",
                            "窗口": {"起": ws, "止": we},
                            "范围": {"站点ID": None, "设备ID": device_id},
                            "判定参数": {
                                "诊断级别": diag_level,
                                "启用质量码": enabled_codes,
                            },
                            "运行ID": _run_id,
                            "线程": _th.current_thread().name,
                            "threadName": _th.current_thread().name,
                        }
                    },
                )
            except Exception:
                pass
            # 在质量打标前，刷新依赖的物化视图：运行状态与60s统计（按窗口与设备）
            try:
                from app.adapters.db.gateway import get_conn as _get_conn

                with _get_conn(settings) as __conn:
                    with __conn.cursor() as __cur:
                        __cur.execute(
                            "CALL public.sp_refresh_mv_running_presence(%s,%s,%s,%s)",
                            (ws, we, None, device_id),
                        )
                        __cur.execute(
                            "CALL public.sp_refresh_mv_metric_60s_stats(%s,%s,%s,%s)",
                            (ws, we, None, device_id),
                        )
                    __conn.commit()
            except Exception:
                pass

            # 调用质量打标并计时
            # 资源采样（前）：用于计算资源变化
            try:
                import psutil as _ps

                _p0 = _ps.Process()
                _res_before = {
                    "rss": _p0.memory_info().rss,
                    "cpu": _p0.cpu_percent(None),
                }
            except Exception:
                _res_before = None
            from datetime import datetime as _dt

            _t0 = _dt.now()
            _dur_ms_orch = 0
            mark_res = None
            # 并行路径：按设备并行执行质量标注
            # 解析并行度（支持 'auto'）：若为 'auto' 则按 CPU/设备数估算有效并行度并覆盖为整数
            try:
                _qp_is_auto = isinstance(quality_parallel, str) and str(quality_parallel).lower() == "auto"
            except Exception:
                _qp_is_auto = False
            if _qp_is_auto and device_id is None:
                # 估算窗口内设备数量（用于上限约束）
                _n_devs = 0
                try:
                    from app.adapters.db.gateway import get_conn as _get_conn
                    with _get_conn(settings) as _conn:
                        with _conn.cursor() as _cur:
                            _cur.execute(
                                "SELECT COUNT(DISTINCT device_id) FROM public.mv_presence_1s_any WHERE ts_bucket >= %s AND ts_bucket < %s",
                                (
                                    _dt.fromisoformat(ws.replace('Z', '+00:00')),
                                    _dt.fromisoformat(we.replace('Z', '+00:00')),
                                ),
                            )
                            _row = _cur.fetchone()
                            _n_devs = int(_row[0]) if _row and _row[0] is not None else 0
                except Exception:
                    _n_devs = 0
                try:
                    import os as _os
                    _ncpu = int(_os.cpu_count() or 4)
                except Exception:
                    _ncpu = 4
                _eff = min(max(4, _ncpu // 2), 8)
                if _n_devs:
                    _eff = min(_eff, _n_devs)
                quality_parallel = _eff  # 生效并行度

            if (isinstance(quality_parallel, int) and quality_parallel > 1) and (device_id is None):
                try:
                    from app.adapters.db.gateway import get_conn as _get_conn
                    devs: list[int] = []
                    with _get_conn(settings) as _conn:
                        with _conn.cursor() as _cur:
                            # 优先用 presence 视图获取窗口内有数据的设备
                            _cur.execute(
                                """
                                SELECT DISTINCT device_id
                                FROM public.mv_presence_1s_any
                                WHERE ts_bucket >= %s AND ts_bucket < %s
                                ORDER BY device_id
                                """,
                                (
                                    _dt.fromisoformat(ws.replace("Z", "+00:00")),
                                    _dt.fromisoformat(we.replace("Z", "+00:00")),
                                ),
                            )
                            devs = [int(r[0]) for r in _cur.fetchall()]
                    if not devs:
                        devs = []
                except Exception:
                    devs = []
                # 若仍为空，退化为单次执行（全设备）
                if not devs:
                    mark_res = _mqw(
                        settings,
                        ws,
                        we,
                        station_id=None,
                        device_id=None,
                        codes=(quality_codes if quality_codes is not None else enabled_codes),
                        diag_level=(quality_diag_level if quality_diag_level is not None else diag_level),
                        run_id=_run_id,
                    )
                    _dur_ms_orch = int((_dt.now() - _t0).total_seconds() * 1000)
                else:
                    # 并行执行
                    try:
                        import concurrent.futures as _fut
                        def _do_one(_dev: int):
                            t0 = _dt.now()
                            res = _mqw(
                                settings,
                                ws,
                                we,
                                station_id=None,
                                device_id=_dev,
                                codes=(quality_codes if quality_codes is not None else enabled_codes),
                                diag_level=(quality_diag_level if quality_diag_level is not None else diag_level),
                                run_id=_run_id,
                            )
                            dur = int((_dt.now() - t0).total_seconds() * 1000)
                            return {"device_id": _dev, "res": res, "duration_ms": dur}
                        _items: list[dict] = []
                        with _fut.ThreadPoolExecutor(max_workers=int(quality_parallel)) as ex:
                            for item in ex.map(_do_one, devs):
                                _items.append(item)
                        _dur_ms_orch = int((_dt.now() - _t0).total_seconds() * 1000)
                        duration_s = time.perf_counter() - t0_stage
                        timing_stats["quality_mark"] = {"duration_s": duration_s}
                        # 取第一条作为代表结果
                        mark_res = _items[0]["res"] if _items else None
                        quality_mark_summary = {
                            "status": "ok",
                            "parallel": {
                                "devices": len(devs),
                                "workers": int(quality_parallel),
                                "items": _items[:5],  # 仅前5条样例，避免膨胀
                            },
                            **(mark_res or {}),
                            "duration_ms": _dur_ms_orch,
                        }
                    except Exception as _pex:
                        # 并行失败，回退单次执行
                        mark_res = _mqw(
                            settings,
                            ws,
                            we,
                            station_id=None,
                            device_id=None,
                            codes=(quality_codes if quality_codes is not None else enabled_codes),
                            diag_level=(quality_diag_level if quality_diag_level is not None else diag_level),
                            run_id=_run_id,
                        )
                        _dur_ms_orch = int((_dt.now() - _t0).total_seconds() * 1000)
            else:
                # 单次执行路径（可限定单设备）
                mark_res = _mqw(
                    settings,
                    ws,
                    we,
                    station_id=None,
                    device_id=device_id,
                    codes=(quality_codes if quality_codes is not None else enabled_codes),
                    diag_level=(quality_diag_level if quality_diag_level is not None else diag_level),
                    run_id=_run_id,
                )
                _dur_ms_orch = int((_dt.now() - _t0).total_seconds() * 1000)

            # 资源采样（可选）
            try:
                import psutil as _ps

                _p = _ps.Process()
                _res_after = {"rss": _p.memory_info().rss, "cpu": _p.cpu_percent(None)}
                try:
                    _res_before  # noqa: F401
                except NameError:
                    _res_before = None  # type: ignore
                _res_delta = (
                    {
                        "rss": _res_after["rss"] - _res_before["rss"],
                        "cpu": _res_after["cpu"],
                    }
                    if _res_before
                    else None
                )
            except Exception:
                _res_after = None
                _res_delta = None

            if not isinstance(locals().get("quality_mark_summary"), dict):
                duration_s = time.perf_counter() - t0_stage
                timing_stats["quality_mark"] = {"duration_s": duration_s}
                quality_mark_summary = {
                    "status": "ok",
                    **(mark_res or {}),
                    "duration_ms": _dur_ms_orch,
                }
            # 统一质量标注摘要中的时间展示为 +08 格式（覆盖 mark_window 返回的 ISO Z）
            try:
                if isinstance(quality_mark_summary, dict):
                    quality_mark_summary["start"] = ws_local
                    quality_mark_summary["end"] = we_local
            except Exception:
                pass


            # 质量打标完成后：按窗导出质量码分布（JSON/CSV）
            try:
                _export_win(settings, ws, we, out_dir=_Path("reports"))
            except Exception:
                pass

            # 规则级摘要（基于 quality_profile_log 的 rows_affected 聚合）
            if True:
                from app.adapters.db.gateway import get_conn as _get_conn

                def _parse_code(_stage: str) -> int | None:
                    try:
                        if _stage and _stage.startswith("update_"):
                            return int(_stage.split("_")[-1])
                    except Exception:
                        return None
                    return None

                agg: dict[int, int] = {}
                with _get_conn(settings) as _conn:
                    with _conn.cursor() as _cur:
                        from datetime import datetime as _dt
                        from datetime import timezone as _tz

                        _s_dt = _dt.fromisoformat(ws.replace("Z", "+00:00")).astimezone(
                            _tz.utc
                        )
                        _e_dt = _dt.fromisoformat(we.replace("Z", "+00:00")).astimezone(
                            _tz.utc
                        )
                        _cur.execute(
                            """
                            SELECT stage, SUM(rows_affected)::bigint AS cnt
                            FROM public.quality_profile_log
                            WHERE window_start >= %s AND window_end <= %s AND stage LIKE 'update_%%'
                            GROUP BY stage
                            """,
                            (
                                _s_dt,
                                _e_dt,
                            ),
                        )
                        for _st, _cnt in _cur.fetchall():
                            c = _parse_code(_st)
                            if c is not None:
                                agg[c] = int(_cnt or 0)
                # 输出 anomaly.rule_summary（补充 thresholds/baseline/preconditions/targets 中文键）

                from app.adapters.db.gateway import get_conn as __get_conn

                for c, n in sorted(agg.items()):
                    # 阈值/基线/前置约束（按 code 差异化；示例处理 101/111/112/121/131/132/602）
                    thr = None
                    bl = None
                    prec = None
                    targets = None
                    rule_name = None
                    if c in (101, 131, 132):
                        # 越界/饱和：读取 v_effective_metric_rules 的 value_min/value_max/saturation_min/saturation_max
                        with __get_conn(settings) as __conn:
                            with __conn.cursor() as __cur2:
                                __cur2.execute(
                                    "SELECT MIN(value_min), MAX(value_max) FROM public.v_effective_metric_rules"
                                )
                                r = __cur2.fetchone()
                                thr = (
                                    {"value_min": r[0], "value_max": r[1]}
                                    if r
                                    else None
                                )
                                rule_name = {
                                    101: "越界",
                                    131: "上饱和",
                                    132: "下饱和",
                                }.get(c)
                    elif c in (111, 112, 121):
                        with __get_conn(settings) as __conn:
                            with __conn.cursor() as __cur2:
                                __cur2.execute(
                                    "SELECT MIN(spike_abs), MAX(roc_abs), MAX(roc_ratio), MIN(flatline_eps), MIN(flatline_delta), MIN(flatline_secs) FROM public.v_effective_metric_rules"
                                )
                                r = __cur2.fetchone()
                                thr = (
                                    {
                                        "spike_abs": r[0],
                                        "roc_abs": r[1],
                                        "roc_ratio": r[2],
                                        "flatline_eps": r[3],
                                        "flatline_delta": r[4],
                                        "flatline_secs": r[5],
                                    }
                                    if r
                                    else None
                                )
                                rule_name = {
                                    111: "异常跳变",
                                    112: "变化率异常",
                                    121: "平台期",
                                }.get(c)
                    elif c == 602:
                        with __get_conn(settings) as __conn:
                            with __conn.cursor() as __cur2:
                                __cur2.execute(
                                    "SELECT MIN(median), MIN(mad) FROM public.metric_rule_auto_baseline"
                                )
                                rb = __cur2.fetchone()
                                bl = {"median": rb[0], "mad": rb[1]} if rb else None
                                __cur2.execute(
                                    "SELECT MIN(present_secs), MIN(running_secs), MIN(min_present_secs), MIN(min_running_secs) FROM (VALUES (0,0,0,0)) AS t(present_secs,running_secs,min_present_secs,min_running_secs)"
                                )
                                rp = __cur2.fetchone()
                                prec = (
                                    {
                                        "present_secs": rp[0],
                                        "running_secs": rp[1],
                                        "min_present_secs": rp[2],
                                        "min_running_secs": rp[3],
                                    }
                                    if rp
                                    else None
                                )
                                rule_name = "校准偏差"
                    # 生效范围（仅示例给出 global）
                    targets = {"scope": "global"}

                # 输出 rule_summary（在此处发出，避免插入样例段导致语法破坏）
                _anom_logger.info(
                    "[ANOMALY] rule_summary",
                    extra={
                        "extra_data": {
                            "事件": "anomaly.rule_summary",
                            "代码": c,
                            "命中": n,
                            "窗口": {"起": ws, "止": we},
                            "规则名": rule_name,
                            "目标": targets,
                            **({"阈值": thr} if thr else {}),
                            **({"基线": bl} if bl else {}),
                            **({"前置约束": prec} if prec else {}),
                            **(
                                {"运行ID": mark_res.get("run_id")}
                                if isinstance(mark_res, dict)
                                else {}
                            ),
                        }
                    },
                )

            # 样例级抽样（anomaly.case）：按命中Top-K规则，每规则最多N条
            try:
                import threading as _th
                from datetime import timezone as _tz

                from app.adapters.db.gateway import get_conn as ___get_conn

                sample_strategy = {
                    "top_rules": 3,
                    "per_rule_cases": 2,
                    "random_ratio": 0.0,
                }
                top_rules = [
                    c
                    for c, _n in sorted(agg.items(), key=lambda t: t[1], reverse=True)[
                        : sample_strategy["top_rules"]
                    ]
                ]
                for _code in top_rules:
                    if agg.get(_code, 0) <= 0:
                        continue
                    with ___get_conn(settings) as __conn3:
                        with __conn3.cursor() as __cur3:
                            _s_dt_utc = datetime.fromisoformat(
                                ws.replace("Z", "+00:00")
                            ).astimezone(_tz.utc)
                            _e_dt_utc = datetime.fromisoformat(
                                we.replace("Z", "+00:00")
                            ).astimezone(_tz.utc)
                            __cur3.execute(
                                """
                                SELECT station_id, device_id, metric_id, ts_bucket, value, quality_status, quality_meta
                                FROM public.fact_measurements
                                WHERE ts_bucket >= %s AND ts_bucket < %s AND COALESCE(quality_status,0) = %s
                                ORDER BY ts_bucket
                                LIMIT %s
                                """,
                                (
                                    _s_dt_utc,
                                    _e_dt_utc,
                                    int(_code),
                                    int(sample_strategy["per_rule_cases"]),
                                ),
                            )
                            for st, dv, mt, tsb, val, qcode, qmeta in __cur3.fetchall():
                                # 计算样例级判定参数（按具体指标与质量码）
                                _thr_case = None
                                _bl_case = None
                                _prec_case = None
                                try:
                                    if int(_code) in (101, 131, 132):
                                        __cur3.execute(
                                            "SELECT value_min, value_max FROM public.v_effective_metric_rules WHERE metric_id=%s LIMIT 1",
                                            (int(mt),),
                                        )
                                        r0 = __cur3.fetchone()
                                        _thr_case = (
                                            {"value_min": r0[0], "value_max": r0[1]}
                                            if r0
                                            else None
                                        )
                                    elif int(_code) in (111, 112, 121):
                                        __cur3.execute(
                                            "SELECT spike_abs, roc_abs, roc_ratio, flatline_eps, flatline_delta, flatline_secs FROM public.v_effective_metric_rules WHERE metric_id=%s LIMIT 1",
                                            (int(mt),),
                                        )
                                        r1 = __cur3.fetchone()
                                        _thr_case = (
                                            {
                                                "spike_abs": r1[0],
                                                "roc_abs": r1[1],
                                                "roc_ratio": r1[2],
                                                "flatline_eps": r1[3],
                                                "flatline_delta": r1[4],
                                                "flatline_secs": r1[5],
                                            }
                                            if r1
                                            else None
                                        )
                                    elif int(_code) == 602:
                                        __cur3.execute(
                                            "SELECT median, mad FROM public.metric_rule_auto_baseline WHERE metric_id=%s ORDER BY updated_at DESC NULLS LAST LIMIT 1",
                                            (int(mt),),
                                        )
                                        rb1 = __cur3.fetchone()
                                        _bl_case = (
                                            {"median": rb1[0], "mad": rb1[1]}
                                            if rb1
                                            else None
                                        )
                                        __cur3.execute(
                                            "SELECT 0 AS present_secs, 0 AS running_secs, 0 AS min_present_secs, 0 AS min_running_secs",
                                        )
                                        rp1 = __cur3.fetchone()
                                        _prec_case = (
                                            {
                                                "present_secs": rp1[0],
                                                "running_secs": rp1[1],
                                                "min_present_secs": rp1[2],
                                                "min_running_secs": rp1[3],
                                            }
                                            if rp1
                                            else None
                                        )
                                except Exception:
                                    pass
                                _anom_logger.info(
                                    "[ANOMALY] case",
                                    extra={
                                        "extra_data": {
                                            "事件": "anomaly.case",
                                            "代码": int(_code),
                                            "键": {
                                                "站点ID": int(st),
                                                "设备ID": int(dv),
                                                "指标ID": int(mt),
                                                "时间": tsb.isoformat(),
                                            },
                                            "输入": {"值": val, "质量元": qmeta},
                                            "判定参数": {
                                                **(
                                                    {"阈值": _thr_case}
                                                    if _thr_case
                                                    else {}
                                                ),
                                                **(
                                                    {"基线": _bl_case}
                                                    if _bl_case
                                                    else {}
                                                ),
                                                **(
                                                    {"前置约束": _prec_case}
                                                    if _prec_case
                                                    else {}
                                                ),
                                            },
                                            "使用指标": {
                                                "主指标ID": int(mt),
                                                "关联指标": (
                                                    qmeta.get("related_metrics")
                                                    if isinstance(qmeta, dict)
                                                    and qmeta.get("related_metrics")
                                                    else []
                                                ),
                                            },
                                            "判断结果": {
                                                "结论": "异常",
                                                "质量码": int(_code),
                                            },
                                            "窗口": {"起": ws, "止": we},
                                            "运行ID": (
                                                _run_id
                                                if "_run_id" in locals()
                                                else (
                                                    mark_res.get("run_id")
                                                    if isinstance(mark_res, dict)
                                                    else None
                                                )
                                            ),
                                            "线程": _th.current_thread().name,
                                            "抽样策略": sample_strategy,
                                        }
                                    },
                                )
            except Exception:
                pass

            # 窗口级结束日志（补充 totals/performance，中文键；含资源变化与扫描行数）
            try:
                from app.adapters.db.gateway import get_conn as __get_conn

                rows_scanned = None
                with __get_conn(settings) as __conn:
                    with __conn.cursor() as __cur:
                        __cur.execute(
                            "SELECT COUNT(*) FROM public.fact_measurements WHERE ts_bucket>=%s AND ts_bucket<%s",
                            (
                                datetime.fromisoformat(ws.replace("Z", "+00:00")),
                                datetime.fromisoformat(we.replace("Z", "+00:00")),
                            ),
                        )
                        rows_scanned = int(__cur.fetchone()[0])
                per_code = [
                    {"代码": int(c), "影响行数": int(n)} for c, n in sorted(agg.items())
                ]
                totals = {
                    "扫描行数": rows_scanned,
                    "总影响行数": int(sum(agg.values())) if agg else 0,
                    "按规则": per_code,
                }
                # 资源变化（如可用）
                try:
                    _perf_delta = _res_delta  # 由前文计算
                except Exception:
                    _perf_delta = None
                perf = {
                    "duration_ms": int(_dur_ms_orch),
                    **({"resource_delta": _perf_delta} if _perf_delta else {}),
                }
                _anom_logger.info(
                    "[ANOMALY] window_end",
                    extra={
                        "extra_data": {
                            "事件": "anomaly.window_end",
                            "窗口": {"起": ws, "止": we},
                            "范围": {"站点ID": None, "设备ID": device_id},
                            "汇总": totals,
                            "性能": perf,
                            "结果": "成功",
                            "result": "ok",
                            "线程": (
                                _th.current_thread().name
                                if " _th" in globals()
                                else __import__("threading").current_thread().name
                            ),
                            "threadName": (
                                _th.current_thread().name
                                if " _th" in globals()
                                else __import__("threading").current_thread().name
                            ),
                            **(
                                {"运行ID": mark_res.get("run_id")}
                                if isinstance(mark_res, dict)
                                else {}
                            ),
                        }
                    },
                )
            except Exception:
                pass
        except Exception as ex:
            duration_s = time.perf_counter() - t0_stage
            timing_stats["quality_mark"] = {"duration_s": duration_s, "error": str(ex)}
            quality_mark_summary = {"status": "error", "message": str(ex)}

            try:
                import logging as _logging
                _logging.getLogger("activity").error(
                    f"[进度] quality_mark 失败 (耗时: {duration_s:.2f}秒): {ex}",
                    extra={
                        "extra_data": {
                            "event": "quality_mark.error",
                            "duration_s": duration_s,
                            "error": str(ex),
                        }
                    }
                )
            except Exception:
                pass

    # 6.5) 可选后续：device_phase（放在 device_running 之后，quality_mark 之后）

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

    # 7) 可选后续：缺失指标计算（在 quality_mark 和 presence 之后执行）
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
        # 仅用于审计展示：merge.yaml 中声明启用的质量码
        "quality_mark_codes_enabled": (
            ra.get("quality_mark_codes_enabled") if "ra" in locals() else None
        ),
        "merge_stats": (merge_stats or {}),
        "calculation": calculation_summary,
        "device_running": device_running_summary,
        "presence": presence_summary,
        "quality_mark": quality_mark_summary,
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
