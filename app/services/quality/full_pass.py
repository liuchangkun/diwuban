from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List

from app.adapters.db.gateway import get_conn

_act = logging.getLogger(__name__)
# device_phase 已合并至 mv_device_running_1s，移除旧计算入口
from app.services.rules.auto_baseline import (
    run_auto_baseline,
)  # TODO: 后续迁移至 baseline:auto:compute CLI 名称，对应服务函数保留
from app.services.quality.mark_window import mark_quality_window


def run_quality_full_pass(
    settings,
    start: str,
    end: str,
    lookback_days: int,
    station_id: Optional[int],
    device_id: Optional[int],
) -> Dict[str, Any]:
    _act.info(
        "[流程-开始] [质量全流程]",
        extra={
            "extra_data": {
                "start": start,
                "end": end,
                "lookback_days": lookback_days,
                "station_id": station_id,
                "device_id": device_id,
            }
        },
    )

    steps: List[Dict[str, Any]] = []

    # Step1: device_phase（已合并为 mv_device_running_1s 的相位列；此处跳过）
    _act.info("[流程-跳过] [设备相位计算-已合并至MV]")
    steps.append({"step": "device_phase", "skipped": True, "reason": "merged_into_mv"})

    # Step2: auto-baseline
    _act.info("[流程-阶段] [自动基线生成开始]")
    _ = run_auto_baseline(settings, lookback_days, station_id, device_id)
    _act.info("[流程-阶段] [自动基线生成完成]")
    steps.append(
        {
            "step": "auto_baseline",
            "lookback_days": lookback_days,
            "station_id": station_id,
            "device_id": device_id,
        }
    )

    # Step3: quality mark
    _act.info("[流程-阶段] [质量窗口标注开始]")
    _ = mark_quality_window(settings, start, end, station_id, device_id)
    _act.info("[流程-阶段] [质量窗口标注完成]")
    steps.append(
        {
            "step": "quality_mark",
            "start": start,
            "end": end,
            "station_id": station_id,
            "device_id": device_id,
        }
    )

    _act.info(
        "[流程-完成] [质量全流程]",
        extra={"extra_data": {"steps_count": len(steps)}},
    )

    return {"ok": True, "steps": steps}
