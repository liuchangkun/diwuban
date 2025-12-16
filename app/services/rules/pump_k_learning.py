"""
泵 k 系数学习触发入口（app.services.rules.pump_k_learning）

本模块提供泵 k 系数学习任务的统一入口，支持：
- 自动触发：定时任务调用
- 手动触发：命令行或 API 调用

使用方式：
    from app.services.rules.pump_k_learning import run_pump_k_learning

    # 学习全部泵站
    result = run_pump_k_learning(settings, start=None, end=None, station_id=None)

    # 学习指定泵站
    result = run_pump_k_learning(settings, start="2025-10-22", end="2025-10-23", station_id=1)

    # 学习指定设备
    result = run_pump_k_learning(settings, station_id=1, device_id=101)
"""

from __future__ import annotations

from datetime import datetime as _dt
from pathlib import Path
from typing import Any, Dict, Optional

from app.adapters.db.gateway import get_conn
from app.adapters.db.transaction import transaction
import logging

_act = logging.getLogger(__name__)


def run_pump_k_learning(
    settings,
    start: Optional[str] = None,
    end: Optional[str] = None,
    station_id: Optional[int] = None,
    device_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    执行泵 k 系数学习任务

    功能说明：
    - 从高频运行数据（f > 40Hz）学习每台泵的 k 系数
    - 学习结果保存到 calculation_parameters 表
    - 支持按泵站或设备过滤

    参数：
        settings: 应用配置
        start: 开始时间（ISO格式字符串，NULL则使用最早数据时间）
        end: 结束时间（ISO格式字符串，NULL则使用最新数据时间）
        station_id: 泵站ID过滤（NULL则处理所有泵站）
        device_id: 设备ID过滤（NULL则处理指定泵站的所有设备）

    返回值：
        Dict: {
            window: {start, end},
            filters: {station_id, device_id},
            learned_devices: int,
            saved_devices: int,
            results: [{device_id, k_value, sample_count, confidence, source}, ...]
        }
    """
    _act.info(
        "[流程-开始] [泵k系数学习]",
        extra={
            "extra_data": {
                "start": start,
                "end": end,
                "station_id": station_id,
                "device_id": device_id,
            }
        },
    )

    result: Dict[str, Any] = {
        "window": {"start": start, "end": end},
        "filters": {"station_id": station_id, "device_id": device_id},
        "learned_devices": 0,
        "saved_devices": 0,
        "results": [],
    }

    # 导入学习器
    from app.services.calculation.metrics.pump_flow_rate.pump_k_coefficient import (
        PumpKCoefficientLearner,
    )

    with get_conn(settings) as conn:
        with transaction(conn):
            with conn.cursor() as cur:
                # 自动确定时间窗口
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
                    _act.warning("[流程-跳过] [时间窗口无效]")
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

                # 获取要处理的泵站列表
                if station_id:
                    station_ids = [station_id]
                else:
                    cur.execute("SELECT DISTINCT id FROM dim_stations ORDER BY id")
                    station_ids = [r[0] for r in cur.fetchall()]

                _act.info(
                    "[流程-阶段] [泵站列表获取]",
                    extra={"extra_data": {"station_count": len(station_ids)}},
                )

    # 创建学习器
    learner = PumpKCoefficientLearner(trace_id="pump_k_learning_task")

    all_results = []
    saved_count = 0

    for sid in station_ids:
        if device_id:
            # 单设备学习
            learn_result = learner.learn_k_for_device(sid, device_id, s_dt, e_dt)
            device_results = {device_id: learn_result}
        else:
            # 泵站批量学习
            device_results = learner.learn_k_for_station(sid, s_dt, e_dt)

        # 保存结果
        for did, res in device_results.items():
            success = learner.save_k_to_db(
                station_id=sid,
                device_id=did,
                k_value=res['k_value'],
                sample_count=res['sample_count'],
                source=res['source'],
                confidence=res['confidence']
            )
            if success:
                saved_count += 1

            all_results.append({
                "station_id": sid,
                "device_id": did,
                "k_value": res['k_value'],
                "sample_count": res['sample_count'],
                "confidence": res['confidence'],
                "source": res['source'],
            })

    result.update({
        "window": {"start": start, "end": end},
        "learned_devices": len(all_results),
        "saved_devices": saved_count,
        "results": all_results[:20],  # 只返回前20条结果
    })

    _act.info(
        "[流程-完成] [泵k系数学习]",
        extra={
            "extra_data": {
                "learned_devices": len(all_results),
                "saved_devices": saved_count,
            }
        },
    )

    return result

