from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Iterable, List, Tuple
import logging

from app.adapters.db.gateway import get_conn
from app.core.logging.setup import log_db_function, log_biz


def _snapshot_device_counts(
    conn, device_id: int, start: datetime, end_excl: datetime
) -> Dict[str, Any]:
    """采集单设备在当前窗口内的前后状态与事实覆盖（用于前后对比日志）。"""
    with conn.cursor() as cur:
        # 规则/基线总量（全量维度）
        cur.execute(
            "SELECT count(*) FROM public.metric_rule_auto_baseline WHERE device_id=%s",
            (device_id,),
        )
        baseline_rows = int(cur.fetchone()[0])
        cur.execute(
            "SELECT count(*) FROM public.metric_quality_rules WHERE device_id=%s",
            (device_id,),
        )
        rule_rows = int(cur.fetchone()[0])
        # PF 阈值
        cur.execute(
            "SELECT pf_min, pf_max FROM public.device_running_thresholds WHERE device_id=%s",
            (device_id,),
        )
        row = cur.fetchone()
        pf_min = float(row[0]) if row and row[0] is not None else None
        pf_max = float(row[1]) if row and row[1] is not None else None
        # 窗口内事实覆盖：点数与指标种类数
        cur.execute(
            """
            SELECT count(*) AS points, count(DISTINCT metric_id) AS metrics
            FROM public.fact_measurements
            WHERE device_id=%s AND ts_bucket >= %s AND ts_bucket < %s
            """,
            (device_id, start, end_excl),
        )
        frow = cur.fetchone()
        points = int(frow[0]) if frow and frow[0] is not None else 0
        metrics = int(frow[1]) if frow and frow[1] is not None else 0
    return {
        "baseline_rows": baseline_rows,
        "rule_rows": rule_rows,
        "pf_min": pf_min,
        "pf_max": pf_max,
        "fm_points": points,
        "fm_metrics": metrics,
    }


def seed_from_existing_data(
    settings,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    lookback_days: int = 7,
    station_id: Optional[int] = None,
    device_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    单次窗口内的全集合计算（不分批）：
    - 计算 metric_rule_auto_baseline（稳态且质量=0）
    - 补齐 metric_quality_rules / device_running_thresholds / quality_code_dict

    注意：大窗口时可能耗时较长。更推荐使用 batch_seed_from_existing_data。
    """
    from datetime import timezone
    import logging

    _act = logging.getLogger("activity")
    _act.info(
        "[流程-开始] [种子配置生成]",
        extra={
            "extra_data": {
                "lookback_days": lookback_days,
                "station_id": station_id,
                "device_id": device_id,
                "start": start.isoformat() if start else None,
                "end": end.isoformat() if end else None,
            }
        }
    )

    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # 提升语句超时（60分钟）
            try:
                cur.execute("SET LOCAL statement_timeout TO '3600000ms'")
            except Exception:
                pass

            # 自动探测时间窗
            if start is None or end is None:
                cur.execute(
                    "SELECT MIN(ts_bucket), MAX(ts_bucket) FROM public.fact_measurements"
                )
                row = cur.fetchone()
                if not row or row[0] is None or row[1] is None:
                    raise RuntimeError("fact_measurements 无数据，无法计算种子配置")
                start = row[0]
                end = row[1]

            # 统一为 UTC aware
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)

            end_excl = end + timedelta(seconds=1)

            # 刷新自动基线（窗口版）
            cur.execute(
                "CALL public.sp_refresh_metric_rule_auto_baseline_win(%s,%s,%s,%s)",
                (start, end_excl, station_id, device_id),
            )

            # 种子填充（补齐规则/阈值/字典）
            cur.execute(
                "CALL public.sp_seed_config_from_current_data(%s)", (lookback_days,)
            )

            # 汇总计数
            cur.execute("SELECT COUNT(*) FROM public.metric_rule_auto_baseline")
            auto_baseline_rows = int(cur.fetchone()[0])
            cur.execute("SELECT COUNT(*) FROM public.metric_quality_rules")
            manual_rules_rows = int(cur.fetchone()[0])
            cur.execute(
                "SELECT COUNT(*) FROM public.device_running_thresholds WHERE pf_min IS NOT NULL OR pf_max IS NOT NULL"
            )
            drt_pf_filled = int(cur.fetchone()[0])
            cur.execute("SELECT COUNT(*) FROM public.quality_code_dict")
            qdict_rows = int(cur.fetchone()[0])

    result = {
        "window": {
            "start": start.isoformat() if start else None,
            "end": end.isoformat() if end else None,
        },
        "lookback_days": lookback_days,
        "filters": {"station_id": station_id, "device_id": device_id},
        "counts": {
            "metric_rule_auto_baseline": auto_baseline_rows,
            "metric_quality_rules": manual_rules_rows,
            "device_running_thresholds_pf_filled": drt_pf_filled,
            "quality_code_dict": qdict_rows,
        },
    }

    _act.info(
        "[流程-完成] [种子配置生成完成]",
        extra={
            "extra_data": {
                "window_start": start.isoformat() if start else None,
                "window_end": end.isoformat() if end else None,
                "auto_baseline_rows": auto_baseline_rows,
                "manual_rules_rows": manual_rules_rows,
                "drt_pf_filled": drt_pf_filled,
                "qdict_rows": qdict_rows,
            }
        }
    )

    return result


def batch_seed_from_existing_data(
    settings,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    lookback_days: int = 7,
    station_id: Optional[int] = None,
    device_ids: Optional[Iterable[int]] = None,
    max_retries: int = 2,
    work_mem: Optional[str] = None,
    log_prefix: str = "[seed-batch]",
    fast_mode: bool = True,
) -> Dict[str, Any]:
    """
    批量计算（支持快速模式）：
    - 快速模式：一次性在库端计算全窗口(可按站过滤)的自动基线 → 统一补齐规则/阈值；极大降低过程调用与扫描开销
    - 常规模式：按设备分批执行，单设备独立事务，失败可重试
    - Python 仅编排；所有统计/补齐在数据库内完成；输出全中文日志

    返回：整体统计与失败设备列表
    """
    from datetime import timezone
    import time

    with get_conn(settings) as conn:
        # 探测窗口（获取数据 + 耗时 + 结果）
        t_win = time.perf_counter()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT MIN(ts_bucket), MAX(ts_bucket) FROM public.fact_measurements"
            )
            row = cur.fetchone()
        win_ms = int((time.perf_counter() - t_win) * 1000)
        min_ts = row[0] if row else None
        max_ts = row[1] if row else None
        if start is None or end is None:
            if not min_ts or not max_ts:
                raise RuntimeError("fact_measurements 无数据，无法计算种子配置")
            start = min_ts if start is None else start
            end = max_ts if end is None else end
        # 统一时区
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        end_excl = end + timedelta(seconds=1)
        log_biz(
            action="分批-窗口探测",
            status="info",
            detail={
                "min_ts": (min_ts.isoformat() if min_ts else None),
                "max_ts": (max_ts.isoformat() if max_ts else None),
                "duration_ms": win_ms,
                "used_start": start.isoformat(),
                "used_end": end.isoformat(),
            },
        )

        # 批处理窗口日志
        log_biz(
            action="分批-窗口",
            status="info",
            detail={
                "start": start.isoformat(),
                "end": end.isoformat(),
                "lookback_days": lookback_days,
                "station_id": station_id,
            },
        )

        # 设备列表
        if device_ids is None:
            t_dl = time.perf_counter()
            with conn.cursor() as cur:
                if station_id is not None:
                    cur.execute(
                        "SELECT DISTINCT device_id FROM public.fact_measurements WHERE station_id=%s AND ts_bucket>=%s AND ts_bucket<%s ORDER BY device_id",
                        (station_id, start, end_excl),
                    )
                else:
                    cur.execute(
                        "SELECT DISTINCT device_id FROM public.fact_measurements WHERE ts_bucket>=%s AND ts_bucket<%s ORDER BY device_id",
                        (start, end_excl),
                    )
                device_ids = [int(r[0]) for r in cur.fetchall()]
            dl_ms = int((time.perf_counter() - t_dl) * 1000)
            log_biz(
                action="分批-设备清单",
                status="info",
                detail={
                    "devices_total": len(device_ids),
                    "duration_ms": dl_ms,
                    "station_id": station_id,
                },
            )
        # 快速模式：一次性在库端计算（不按设备循环）
        total = len(list(device_ids))

        if fast_mode:
            import time as _t

            t0 = _t.perf_counter()
            with conn.cursor() as cur:
                try:
                    cur.execute("SET LOCAL statement_timeout TO '3600000ms'")
                    if work_mem:
                        cur.execute("SET LOCAL work_mem TO %s", (work_mem,))
                except Exception:
                    pass
                # A) 全库/按站 自动基线（一次）
                t_ab = _t.perf_counter()
                cur.execute(
                    "CALL public.sp_refresh_metric_rule_auto_baseline_win(%s,%s,%s,%s)",
                    (start, end_excl, station_id, None),
                )
                conn.commit()
                ab_ms = int((_t.perf_counter() - t_ab) * 1000)
                log_biz(
                    action="全库-自动基线(一次)",
                    status="info",
                    detail={
                        "sql": "CALL public.sp_refresh_metric_rule_auto_baseline_win(?,?,?,?)",
                        "args": {
                            "start": start.isoformat(),
                            "end": end.isoformat(),
                            "station_id": station_id,
                            "device_id": None,
                        },
                        "duration_ms": ab_ms,
                        "success": True,
                    },
                )
            # B) 规则/阈值补齐（一次，直接SQL，避免重复触发全局基线刷新）
            t_seed = _t.perf_counter()
            with conn.cursor() as cur:
                try:
                    cur.execute("SET LOCAL statement_timeout TO '600000ms'")
                except Exception:
                    pass
                # B1) 基于已写入的 metric_rule_auto_baseline 补齐 metric_quality_rules（仅插入缺失）
                cur.execute(
                    """
                    INSERT INTO public.metric_quality_rules(
                      station_id, device_id, metric_id,
                      value_min, value_max,
                      spike_abs, roc_abs, roc_ratio,
                      flatline_eps, flatline_delta,
                      remark
                    )
                    SELECT b.station_id, b.device_id, b.metric_id,
                           b.p05, b.p95,
                           b.spike_abs, b.roc_abs, b.roc_ratio,
                           b.flatline_eps, b.flatline_delta,
                           'seed:auto_baseline(win)'
                    FROM public.metric_rule_auto_baseline b
                    LEFT JOIN public.metric_quality_rules r
                      ON r.station_id IS NOT DISTINCT FROM b.station_id
                     AND r.device_id  IS NOT DISTINCT FROM b.device_id
                     AND r.metric_id  IS NOT DISTINCT FROM b.metric_id
                    WHERE r.metric_id IS NULL;
                    """
                )
                # B2) 以窗口内稳态段的 PF 5%~95% 填充 device_running_thresholds（仅填空值）
                cur.execute(
                    """
                    WITH ids AS (
                      SELECT
                        (SELECT id FROM public.dim_metric_config WHERE metric_key='device_phase') AS phase_id,
                        (SELECT id FROM public.dim_metric_config WHERE metric_key='device_running') AS run_id,
                        (SELECT id FROM public.dim_metric_config WHERE metric_key IN ('pump_power_factor','power_factor') LIMIT 1) AS pf_id
                    ), base AS (
                      SELECT f.device_id, f.value AS pf
                      FROM public.fact_measurements f
                      JOIN ids ON TRUE
                      LEFT JOIN public.fact_measurements ph
                        ON ph.station_id=f.station_id AND ph.device_id=f.device_id AND ph.ts_bucket=f.ts_bucket
                       AND ids.phase_id IS NOT NULL AND ph.metric_id=ids.phase_id AND ph.value=1
                      LEFT JOIN public.fact_measurements frun
                        ON frun.station_id=f.station_id AND frun.device_id=f.device_id AND frun.ts_bucket=f.ts_bucket
                       AND ids.run_id IS NOT NULL AND frun.metric_id=ids.run_id AND frun.value=1
                      WHERE f.metric_id=ids.pf_id
                        AND f.ts_bucket >= %s AND f.ts_bucket < %s
                        AND COALESCE(f.quality_status,0)=0 AND f.value IS NOT NULL
                        AND (ph.ts_bucket IS NOT NULL OR frun.ts_bucket IS NOT NULL)
                    ), agg AS (
                      SELECT device_id,
                             percentile_cont(0.05) WITHIN GROUP (ORDER BY pf)::float8 AS pf_min,
                             percentile_cont(0.95) WITHIN GROUP (ORDER BY pf)::float8 AS pf_max
                      FROM base GROUP BY device_id
                    )
                    UPDATE public.device_running_thresholds t
                    SET pf_min = COALESCE(t.pf_min, a.pf_min),
                        pf_max = COALESCE(t.pf_max, a.pf_max)
                    FROM agg a
                    WHERE a.device_id=t.device_id;
                    """,
                    (start, end_excl),
                )
                # B3) 默认窗口与不平衡阈值（仅当为空）
                cur.execute(
                    """
                    UPDATE public.device_running_thresholds t
                    SET start_pre_secs  = COALESCE(start_pre_secs, 3),
                        start_post_secs = COALESCE(start_post_secs, 5),
                        stop_pre_secs   = COALESCE(stop_pre_secs, 3),
                        stop_post_secs  = COALESCE(stop_post_secs, 3),
                        imbalance_max_pct = COALESCE(imbalance_max_pct, 20.0);
                    """
                )
                # B4) 质量字典：若缺少必要条目则补齐
                cur.execute(
                    """
                    INSERT INTO public.quality_code_dict(code,label_zh,category,severity,description)
                    VALUES
                      (101,'越界','数值特性',3,'数值超出合理区间'),
                      (111,'异常跳变','数值特性',3,'相邻秒差值超阈'),
                      (112,'变化率异常','数值特性',3,'相对或绝对变化率超阈'),
                      (121,'平台期','数值特性',2,'短窗标准差与极差均很小，可能传感器卡死'),
                      (131,'上饱和','数值特性',3,'接近量程上限持续'),
                      (132,'下饱和','数值特性',3,'接近量程下限持续'),
                      (201,'高噪声','噪声/完整性',2,'短窗标准差异常偏高'),
                      (401,'状态矛盾','跨指标/跨设备',4,'运行=0但功率/流量高或运行=1但输出近零'),
                      (501,'时间漂移','时间一致性',2,'ts_raw 与 ts_bucket 偏差过大'),
                      (502,'重复秒','时间一致性',2,'同秒重复/冲突'),
                      (701,'功率因数异常','机理/物理',3,'功率因数超出合理范围'),
                      (711,'液位流量守恒异常','机理/物理',4,'dLevel/dt 与流量不一致'),
                      (721,'相似定律异常','机理/物理',3,'与变频相似定律偏差过大'),
                      (731,'泵曲线偏差','机理/物理',3,'与泵特性曲线偏差过大'),
                      (751,'计数器非单调','机理/物理',3,'累计量出现回退')
                    ON CONFLICT (code) DO NOTHING;
                    """
                )
            conn.commit()
            seed_ms = int((_t.perf_counter() - t_seed) * 1000)
            log_biz(
                action="分批-补齐规则阈值(一次)",
                status="info",
                detail={
                    "sql": "rule_seed: inline SQL (no baseline refresh)",
                    "args": {"lookback_days": lookback_days},
                    "duration_ms": seed_ms,
                    "success": True,
                },
            )
            # C) 汇总
            t_sum = _t.perf_counter()
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM public.metric_rule_auto_baseline")
                auto_baseline_rows = int(cur.fetchone()[0])
                cur.execute("SELECT COUNT(*) FROM public.metric_quality_rules")
                manual_rules_rows = int(cur.fetchone()[0])
                cur.execute(
                    "SELECT COUNT(*) FROM public.device_running_thresholds WHERE pf_min IS NOT NULL OR pf_max IS NOT NULL"
                )
                drt_pf_filled = int(cur.fetchone()[0])
                cur.execute("SELECT COUNT(*) FROM public.quality_code_dict")
                qdict_rows = int(cur.fetchone()[0])
            sum_ms = int((_t.perf_counter() - t_sum) * 1000)
            total_ms = int((_t.perf_counter() - t0) * 1000)
            log_biz(
                action="分批-完成",
                status="info",
                detail={
                    "duration_ms": total_ms,
                    "summary_query_ms": sum_ms,
                    "devices_total": total,
                    "devices_succeeded": total,
                    "devices_failed": 0,
                    "metric_rule_auto_baseline": auto_baseline_rows,
                    "metric_quality_rules": manual_rules_rows,
                    "device_running_thresholds_pf_filled": drt_pf_filled,
                    "quality_code_dict": qdict_rows,
                    "success": True,
                    "mode": "fast",
                },
            )
            return {
                "window": {
                    "start": (
                        start.isoformat() if hasattr(start, "isoformat") else str(start)
                    ),
                    "end": end.isoformat() if hasattr(end, "isoformat") else str(end),
                },
                "lookback_days": lookback_days,
                "filters": {"station_id": station_id},
                "stats": {
                    "devices_total": total,
                    "devices_succeeded": total,
                    "devices_failed": 0,
                    "metric_rule_auto_baseline": auto_baseline_rows,
                    "metric_quality_rules": manual_rules_rows,
                    "device_running_thresholds_pf_filled": drt_pf_filled,
                    "quality_code_dict": qdict_rows,
                },
                "failed": [],
                "mode": "fast",
            }

        total = len(list(device_ids))
        log_biz(
            action="分批-设备规模",
            status="info",
            detail={"devices_total": total},
        )
        succeeded: List[int] = []
        failed: List[Tuple[int, str]] = []
        t0 = time.perf_counter()

        logger = logging.getLogger("biz")
        for idx, did in enumerate(device_ids, start=1):
            attempt = 0
            while attempt <= max_retries:
                attempt += 1
                last_step = "begin"
                try:
                    before = _snapshot_device_counts(conn, did, start, end_excl)
                    log_biz(
                        action="设备-开始",
                        status="info",
                        detail={
                            "device_id": did,
                            "index": idx,
                            "total": total,
                            "fm_points": before["fm_points"],
                            "fm_metrics": before["fm_metrics"],
                            "baseline_rows": before["baseline_rows"],
                            "rule_rows": before["rule_rows"],
                            "statement_timeout_ms": 3600000,
                            "work_mem": work_mem,
                        },
                    )
                    with conn.cursor() as cur:
                        # 每设备设置长超时与可选 work_mem
                        try:
                            cur.execute("SET LOCAL statement_timeout TO '3600000ms'")
                            if work_mem:
                                cur.execute("SET LOCAL work_mem TO %s", (work_mem,))
                        except Exception:
                            pass

                        # 步骤A：刷新自动基线
                        last_step = "refresh_auto_baseline"
                        t1 = time.perf_counter()
                        cur.execute(
                            "CALL public.sp_refresh_metric_rule_auto_baseline_win(%s,%s,%s,%s)",
                            (start, end_excl, station_id, did),
                        )
                        t1_exec = time.perf_counter()
                        conn.commit()
                        t1_end = time.perf_counter()
                        cost1_exec = int((t1_exec - t1) * 1000)
                        cost1_commit = int((t1_end - t1_exec) * 1000)
                        log_biz(
                            action="设备-计算自动基线",
                            status="info",
                            detail={
                                "device_id": did,
                                "sql": "CALL public.sp_refresh_metric_rule_auto_baseline_win(?,?,?,?)",
                                "args": {
                                    "start": start.isoformat(),
                                    "end": end.isoformat(),
                                    "station_id": station_id,
                                    "device_id": did,
                                },
                                "duration_ms": cost1_exec + cost1_commit,
                                "success": True,
                            },
                        )
                        log_db_function(
                            "public.sp_refresh_metric_rule_auto_baseline_win",
                            args={
                                "start": (
                                    start.isoformat()
                                    if hasattr(start, "isoformat")
                                    else str(start)
                                ),
                                "end": (
                                    end.isoformat()
                                    if hasattr(end, "isoformat")
                                    else str(end)
                                ),
                                "station_id": station_id,
                                "device_id": did,
                            },
                            duration_ms=cost1_exec + cost1_commit,
                        )

                        after = _snapshot_device_counts(conn, did, start, end_excl)
                        delta = {
                            "baseline_rows_before": before["baseline_rows"],
                            "baseline_rows_after": after["baseline_rows"],
                            "baseline_rows_delta": after["baseline_rows"]
                            - before["baseline_rows"],
                            "rule_rows_before": before["rule_rows"],
                            "rule_rows_after": after["rule_rows"],
                            "rule_rows_delta": after["rule_rows"] - before["rule_rows"],
                            "pf_min_before": before["pf_min"],
                            "pf_min_after": after["pf_min"],
                            "pf_max_before": before["pf_max"],
                            "pf_max_after": after["pf_max"],
                            "fm_points_before": before["fm_points"],
                            "fm_points_after": after["fm_points"],
                            "fm_metrics_before": before["fm_metrics"],
                            "fm_metrics_after": after["fm_metrics"],
                        }

                        cost_ms = cost1_exec + cost1_commit
                        log_biz(
                            action="设备-完成",
                            status="info",
                            detail={
                                "device_id": did,
                                "index": idx,
                                "total": total,
                                "duration_ms": cost_ms,
                                "success": True,
                                "executed": [
                                    "CALL public.sp_refresh_metric_rule_auto_baseline_win",
                                ],
                                **delta,
                            },
                        )
                        succeeded.append(did)
                        break
                except Exception as e:
                    conn.rollback()
                    log_biz(
                        action="设备-失败",
                        status="error",
                        detail={
                            "device_id": did,
                            "index": idx,
                            "total": total,
                            "attempt": attempt,
                            "max_retries": max_retries,
                            "last_step": last_step,
                            "error": str(e),
                        },
                    )
                    if attempt <= max_retries:
                        time.sleep(min(2**attempt, 10))
                        continue
                    failed.append((did, str(e)))
                    break

        # 汇总计数（获取数据 + 耗时 + 结果）
        t_sum = time.perf_counter()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM public.metric_rule_auto_baseline")
            row = cur.fetchone()
            auto_baseline_rows = int(row[0]) if row and row[0] is not None else 0

            cur.execute("SELECT COUNT(*) FROM public.metric_quality_rules")
            row = cur.fetchone()
            manual_rules_rows = int(row[0]) if row and row[0] is not None else 0

            cur.execute(
                "SELECT COUNT(*) FROM public.device_running_thresholds WHERE pf_min IS NOT NULL OR pf_max IS NOT NULL"
            )
            row = cur.fetchone()
            drt_pf_filled = int(row[0]) if row and row[0] is not None else 0

            cur.execute("SELECT COUNT(*) FROM public.quality_code_dict")
            row = cur.fetchone()
            qdict_rows = int(row[0]) if row and row[0] is not None else 0
        sum_ms = int((time.perf_counter() - t_sum) * 1000)

        total_ms = int((time.perf_counter() - t0) * 1000)
        log_biz(
            action="分批-完成",
            status="info",
            detail={
                "duration_ms": total_ms,
                "summary_query_ms": sum_ms,
                "devices_total": total,
                "devices_succeeded": len(succeeded),
                "devices_failed": len(failed),
                "metric_rule_auto_baseline": auto_baseline_rows,
                "metric_quality_rules": manual_rules_rows,
                "device_running_thresholds_pf_filled": drt_pf_filled,
                "quality_code_dict": qdict_rows,
                "success": len(failed) == 0,
            },
        )

        # 批量一次性：补齐规则/阈值/字典（幂等）
        import time as _t

        t3 = _t.perf_counter()
        with conn.cursor() as cur:
            try:
                cur.execute("SET LOCAL statement_timeout TO '600000ms'")  # 10分钟
            except Exception:
                pass
            cur.execute(
                "CALL public.sp_seed_config_from_current_data(%s)", (lookback_days,)
            )
        conn.commit()
        t3_end = _t.perf_counter()
        seed_once_ms = int((t3_end - t3) * 1000)
        log_biz(
            action="分批-补齐规则阈值(一次)",
            status="info",
            detail={
                "sql": "CALL public.sp_seed_config_from_current_data(?)",
                "args": {"lookback_days": lookback_days},
                "duration_ms": seed_once_ms,
                "success": True,
            },
        )

        return {
            "window": {
                "start": (
                    start.isoformat() if hasattr(start, "isoformat") else str(start)
                ),
                "end": end.isoformat() if hasattr(end, "isoformat") else str(end),
            },
            "lookback_days": lookback_days,
            "filters": {"station_id": station_id},
            "stats": {
                "devices_total": total,
                "devices_succeeded": len(succeeded),
                "devices_failed": len(failed),
                "metric_rule_auto_baseline": auto_baseline_rows,
                "metric_quality_rules": manual_rules_rows,
                "device_running_thresholds_pf_filled": drt_pf_filled,
                "quality_code_dict": qdict_rows,
            },
            "failed": [{"device_id": d, "error": msg} for d, msg in failed],
        }
