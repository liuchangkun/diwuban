from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime as _dt

from app.adapters.db.gateway import get_conn
from app.adapters.db.transaction import transaction
import logging

_act = logging.getLogger(__name__)


def run_running_thresholds(
    settings,
    start: Optional[str],
    end: Optional[str],
    station_id: Optional[int],
    device_id: Optional[int],
    ensure_rows: bool = True,
    method: str = "robust",
    enable_device_type_detection: bool = True,
    enable_running_mode_detection: bool = True,
) -> Dict[str, Any]:
    """高性能刷新 device_running_thresholds（仅库端过程），返回执行摘要。

    功能说明：
    - 窗口：若未提供，则使用 fact_measurements 的最小/最大 ts_bucket（闭区间转半开）
    - 稳态/质量与统计：由 DB 端过程负责
    - 只更新已存在设备行；可选择在执行前补齐缺失设备行

    执行步骤：
    0. 设备类型识别（如果 enable_device_type_detection=True）
       - 调用 api.sp_detect_device_type_simple 识别设备类型（变频泵 vs 软启动泵）
    0.5. 运行模式识别（如果 enable_running_mode_detection=True）
       - 调用 api.sp_detect_running_mode_simple 识别运行模式（持续运行 vs 频繁启停 vs 偶尔运行）
    1. 补齐设备行（如果 ensure_rows=True）
    2. 调用功率因数阈值学习存储过程（pf_min, pf_max）
       - robust: sp_refresh_device_running_thresholds_win（稳健分位数）
       - otsu: sp_refresh_device_running_thresholds_otsu（Otsu 双峰法）
    3. 调用电流阈值学习存储过程（enable_i, i_on, i_off）
    4. 调用功率阈值学习存储过程（enable_p, p_on, p_off）
    5. 调用频率阈值学习存储过程（enable_f, f_on, f_off）
    6. 调用时间参数学习存储过程（grace_hold_secs, min_run_secs, min_stop_secs, smoothing_secs）

    参数：
    - settings: 应用配置
    - start: 开始时间（ISO格式字符串，NULL则使用全局最小时间）
    - end: 结束时间（ISO格式字符串，NULL则使用全局最大时间）
    - station_id: 泵站ID过滤（NULL则处理所有泵站）
    - device_id: 设备ID过滤（NULL则处理所有设备）
    - ensure_rows: 是否在执行前补齐缺失设备行
    - method: 功率因数阈值学习方法（"robust" 或 "otsu"）
    - enable_device_type_detection: 是否执行设备类型识别（默认True）
    - enable_running_mode_detection: 是否执行运行模式识别（默认True）

    返回值：
    - window: 时间窗口信息
    - filters: 过滤条件
    - updated_rows_with_pf: 更新了功率因数阈值的设备数
    - samples: 样例数据（前5个设备的阈值）
    """
    _act.info(
        "[流程-开始] [运行阈值生成A]",
        extra={
            "extra_data": {
                "start": start,
                "end": end,
                "station_id": station_id,
                "device_id": device_id,
                "ensure_rows": ensure_rows,
                "method": method,
                "enable_device_type_detection": enable_device_type_detection,
                "enable_running_mode_detection": enable_running_mode_detection,
            }
        },
    )

    result: Dict[str, Any] = {
        "window": {"start": start, "end": end},
        "filters": {"station_id": station_id, "device_id": device_id},
        "updated_rows_with_pf": 0,
        "samples": [],
    }

    from pathlib import Path as _P

    with get_conn(settings) as conn:
        with transaction(conn):
            with conn.cursor() as cur:
                # 自动窗口
                if not start or not end:
                    _act.info("[数据库-查询] [时间范围查询]")
                    cur.execute(
                        "SELECT MIN(ts_bucket), MAX(ts_bucket) FROM public.fact_measurements"
                    )
                    row = cur.fetchone() or (None, None)
                    if not start and row[0] is not None:
                        start = row[0].isoformat()
                    if not end and row[1] is not None:
                        end = row[1].isoformat()
                    _act.info(
                        "[数据库-查询] [时间范围已获取]",
                        extra={"extra_data": {"start": start, "end": end}},
                    )
                if not start or not end:
                    _act.warning(
                        "[流程-跳过] [时间窗口无效]",
                        extra={"extra_data": {"start": start, "end": end}},
                    )
                    return result

                s_dt = _dt.fromisoformat(start.replace("Z", "+00:00"))
                e_dt = _dt.fromisoformat(end.replace("Z", "+00:00"))

                _act.info(
                    "[流程-阶段] [时间窗口确定]",
                    extra={
                        "extra_data": {
                            "start_ts": s_dt.isoformat(),
                            "end_ts": e_dt.isoformat(),
                            "duration_hours": (e_dt - s_dt).total_seconds() / 3600,
                        }
                    },
                )

                # 适当提升语句超时
                try:
                    cur.execute("SET LOCAL statement_timeout TO '600000ms'")
                except Exception:
                    pass

                # 执行前补齐设备行（幂等，仅 pump 类型设备 - 2025-11-11）
                if ensure_rows:
                    _act.info("[数据库-执行] [设备行补齐（仅 pump 设备）]")
                    cur.execute(
                        """
                        INSERT INTO public.device_running_thresholds(device_id)
                        SELECT DISTINCT fm.device_id
                        FROM public.fact_measurements fm
                        JOIN public.dim_devices d ON d.id = fm.device_id
                        WHERE (%s::bigint IS NULL OR fm.station_id=%s::bigint)
                          AND (%s::bigint IS NULL OR fm.device_id=%s::bigint)
                          AND d.type = 'pump'  -- 仅处理 pump 类型设备
                        ON CONFLICT (device_id) DO NOTHING
                        """,
                        (station_id, station_id, device_id, device_id),
                    )
                    _act.info(
                        "[数据库-执行] [设备行补齐完成]",
                        extra={"extra_data": {"inserted_rows": cur.rowcount or 0}},
                    )

                    # 调试：验证设备行是否真的存在
                    cur.execute("SELECT COUNT(*) FROM device_running_thresholds")
                    count_after_insert = cur.fetchone()[0]
                    _act.info(
                        "[数据库-调试] [设备行验证]",
                        extra={"extra_data": {"count_after_insert": count_after_insert}},
                    )

                # =====================================================================
                # 步骤0: 设备类型识别（新增）
                # =====================================================================
                if enable_device_type_detection:
                    try:
                        _act.info(
                            "[数据库-执行] [存储过程调用-设备类型识别]",
                            extra={"extra_data": {"proc": "api.sp_detect_device_type_simple"}},
                        )
                        cur.execute(
                            "CALL api.sp_detect_device_type_simple(%s::bigint)",
                            (device_id,),
                        )
                        _act.info("[数据库-执行] [设备类型识别完成]")
                    except Exception as e:
                        _act.warning(
                            "[数据库-错误] [设备类型识别失败]",
                            extra={"extra_data": {"error": str(e)}},
                        )

                # =====================================================================
                # 步骤0.5: 运行模式识别（新增）
                # =====================================================================
                if enable_running_mode_detection:
                    try:
                        _act.info(
                            "[数据库-执行] [存储过程调用-运行模式识别]",
                            extra={"extra_data": {"proc": "api.sp_detect_running_mode_simple"}},
                        )
                        cur.execute(
                            "CALL api.sp_detect_running_mode_simple(%s::bigint)",
                            (device_id,),
                        )
                        _act.info("[数据库-执行] [运行模式识别完成]")
                    except Exception as e:
                        _act.warning(
                            "[数据库-错误] [运行模式识别失败]",
                            extra={"extra_data": {"error": str(e)}},
                        )

                # 注意：存储过程应该在部署时创建（通过 migration 脚本），不应该在运行时创建
                # 移除了在事务内部创建存储过程的代码，因为它会导致事务回滚

                # 调用旧的功率因数阈值存储过程（如果存在）
                # 注意：这个存储过程只设置 pf_min/pf_max，不设置核心运行判断阈值
                try:
                    if (method or "robust").lower() == "otsu":
                        proc_name = "sp_refresh_device_running_thresholds_otsu"
                    else:
                        proc_name = "sp_refresh_device_running_thresholds_win"

                    # 检查存储过程是否存在
                    cur.execute(
                        """
                        SELECT COUNT(*)
                        FROM pg_proc p
                        JOIN pg_namespace n ON n.oid = p.pronamespace
                        WHERE n.nspname = 'public'
                          AND p.proname = %s
                        """,
                        (proc_name,)
                    )
                    proc_exists = cur.fetchone()[0] > 0

                    if proc_exists:
                        _act.info(
                            f"[数据库-执行] [存储过程调用-PF阈值]",
                            extra={
                                "extra_data": {"proc": proc_name}
                            },
                        )
                        cur.execute(
                            f"CALL public.{proc_name}(%s,%s,%s::bigint,%s::bigint)",
                            (s_dt, e_dt, station_id, device_id),
                        )
                        _act.info(f"[数据库-执行] [功率因数阈值学习完成]")
                    else:
                        _act.info(
                            f"[数据库-跳过] [旧存储过程不存在，将跳过PF阈值学习]",
                            extra={"extra_data": {"proc": proc_name}},
                        )
                except Exception as e:
                    _act.warning(
                        "[数据库-错误] [功率因数阈值学习失败]",
                        extra={"extra_data": {"error": str(e)}},
                    )
                    # 如果旧存储过程不存在，跳过PF阈值学习（不影响核心功能）

                # =====================================================================
                # 新增：调用电流、功率、频率、时间参数阈值学习存储过程
                # =====================================================================

                # 调用电流阈值学习存储过程
                try:
                    _act.info(
                        "[数据库-执行] [存储过程调用-电流阈值]",
                        extra={"extra_data": {"proc": "sp_refresh_device_running_thresholds_current"}},
                    )
                    cur.execute(
                        "CALL public.sp_refresh_device_running_thresholds_current(%s,%s,%s::bigint,%s::bigint)",
                        (s_dt, e_dt, station_id, device_id),
                    )
                    _act.info("[数据库-执行] [电流阈值学习完成]")
                except Exception as e:
                    _act.warning(
                        "[数据库-错误] [电流阈值学习失败]",
                        extra={"extra_data": {"error": str(e)}},
                    )

                # 调用功率阈值学习存储过程
                try:
                    _act.info(
                        "[数据库-执行] [存储过程调用-功率阈值]",
                        extra={"extra_data": {"proc": "sp_refresh_device_running_thresholds_power"}},
                    )
                    cur.execute(
                        "CALL public.sp_refresh_device_running_thresholds_power(%s,%s,%s::bigint,%s::bigint)",
                        (s_dt, e_dt, station_id, device_id),
                    )
                    _act.info("[数据库-执行] [功率阈值学习完成]")
                except Exception as e:
                    _act.warning(
                        "[数据库-错误] [功率阈值学习失败]",
                        extra={"extra_data": {"error": str(e)}},
                    )

                # 调用频率阈值学习存储过程
                try:
                    _act.info(
                        "[数据库-执行] [存储过程调用-频率阈值]",
                        extra={"extra_data": {"proc": "sp_refresh_device_running_thresholds_frequency"}},
                    )
                    cur.execute(
                        "CALL public.sp_refresh_device_running_thresholds_frequency(%s,%s,%s::bigint,%s::bigint)",
                        (s_dt, e_dt, station_id, device_id),
                    )
                    _act.info("[数据库-执行] [频率阈值学习完成]")
                except Exception as e:
                    _act.warning(
                        "[数据库-错误] [频率阈值学习失败]",
                        extra={"extra_data": {"error": str(e)}},
                    )

                # 调用时间参数学习存储过程
                try:
                    _act.info(
                        "[数据库-执行] [存储过程调用-时间参数]",
                        extra={"extra_data": {"proc": "sp_refresh_device_running_thresholds_timing"}},
                    )
                    cur.execute(
                        "CALL public.sp_refresh_device_running_thresholds_timing(%s,%s,%s::bigint,%s::bigint)",
                        (s_dt, e_dt, station_id, device_id),
                    )
                    _act.info("[数据库-执行] [时间参数学习完成]")
                except Exception as e:
                    _act.warning(
                        "[数据库-错误] [时间参数学习失败]",
                        extra={"extra_data": {"error": str(e)}},
                    )

                # 调试：在事务内部，使用同一个 cursor 验证数据
                cur.execute("SELECT COUNT(*) FROM device_running_thresholds")
                count_in_transaction = cur.fetchone()[0]
                _act.info(
                    "[数据库-调试] [事务内验证]",
                    extra={"extra_data": {"count_in_transaction": count_in_transaction}}
                )

                # 如果有数据，显示前几行
                if count_in_transaction > 0:
                    cur.execute("""
                        SELECT device_id, enable_i, i_on, i_off, updated_by
                        FROM device_running_thresholds
                        ORDER BY device_id
                        LIMIT 3
                    """)
                    sample_rows = cur.fetchall()
                    _act.info(
                        "[数据库-调试] [事务内数据样例]",
                        extra={"extra_data": {"sample_count": len(sample_rows), "samples": [
                            {"device_id": r[0], "enable_i": r[1], "i_on": float(r[2]) if r[2] else None, "i_off": float(r[3]) if r[3] else None, "updated_by": r[4]}
                            for r in sample_rows
                        ]}}
                    )

                # 事务自动提交
                _act.info("[数据库-事务] [事务将自动提交]")

            # 调试：记录事务上下文结束后的连接状态
            _act.info(
                "[数据库-调试] [事务上下文结束后]",
                extra={
                    "extra_data": {
                        "transaction_status": str(conn.info.transaction_status),
                        "autocommit": conn.autocommit,
                    }
                },
            )

            # 调试：立即验证数据是否真的提交到数据库（使用同一个连接）
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM device_running_thresholds")
                count_after_commit = cur.fetchone()[0]
                _act.info(
                    "[数据库-调试] [提交后立即验证]",
                    extra={"extra_data": {"count_after_commit": count_after_commit}}
                )

                # 如果有数据，显示前几行
                if count_after_commit > 0:
                    cur.execute("""
                        SELECT device_id, enable_i, i_on, i_off, updated_by
                        FROM device_running_thresholds
                        ORDER BY device_id
                        LIMIT 5
                    """)
                    sample_rows = cur.fetchall()
                    _act.info(
                        "[数据库-调试] [提交后数据样例]",
                        extra={"extra_data": {"sample_count": len(sample_rows), "samples": [
                            {"device_id": r[0], "enable_i": r[1], "i_on": float(r[2]) if r[2] else None, "i_off": float(r[3]) if r[3] else None, "updated_by": r[4]}
                            for r in sample_rows
                        ]}}
                    )

            # 汇总与样例（单独 cursor）
            _act.info("[数据库-查询] [执行结果查询]")
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FILTER (WHERE pf_min IS NOT NULL OR pf_max IS NOT NULL) FROM public.device_running_thresholds"
                )
                filled = int(cur.fetchone()[0])
                cur.execute(
                    """
                    SELECT device_id, pf_min, pf_max
                    FROM public.device_running_thresholds
                    WHERE pf_min IS NOT NULL OR pf_max IS NOT NULL
                    ORDER BY device_id
                    LIMIT 5
                    """
                )
                samples = [
                    {
                        "device_id": r[0],
                        "pf_min": float(r[1]) if r[1] is not None else None,
                        "pf_max": float(r[2]) if r[2] is not None else None,
                    }
                    for r in cur.fetchall() or []
                ]
            # 事务已在上面的transaction上下文中自动提交

    result.update(
        {
            "window": {"start": start, "end": end},
            "updated_rows_with_pf": filled,
            "samples": samples,
        }
    )

    _act.info(
        "[流程-完成] [运行阈值生成A]",
        extra={
            "extra_data": {
                "updated_rows": filled,
                "samples_count": len(samples),
                "method": method,
            }
        },
    )

    return result
